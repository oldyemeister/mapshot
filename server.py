#!/usr/bin/env python3
"""Mapshot's dependency-free trial server (Python 3.9+).

Serve only runtime assets; source datasets and developer files stay private.
Use a TLS reverse proxy for Internet deployment. No uploads or server rendering.
"""
import argparse
import functools
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent


def runtime_files(root=ROOT):
    root = Path(root).resolve()
    files = [root / name for name in ("index.html", "app.js", "style.css")]
    files += sorted((root / "vendor").rglob("*"))
    files += sorted((root / "data").glob("*.json"))
    files += [root / "data" / f"{name}.geojson.gz" for name in
              ("roads", "buildings", "landuse", "water", "aviation")]
    files += sorted((root / "data/tiles").rglob("*.pbf"))
    return {
        "/" + p.relative_to(root).as_posix(): p
        for p in files
        if p.is_file() and p.resolve().is_relative_to(root)
        and not any(part.startswith(".") for part in p.relative_to(root).parts)
    }


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".gz": "application/gzip",  # Client explicitly decompresses these files.
        ".pbf": "application/x-protobuf",
        ".js": "text/javascript; charset=utf-8",
    }

    def __init__(self, *args, root=ROOT, **kwargs):
        self.root = Path(root).resolve()
        super().__init__(*args, directory=str(self.root), **kwargs)

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            # Reloading or cancelling a failed map load legitimately closes downloads.
            pass

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_head(self):
        path = unquote(urlsplit(self.path).path)
        if path in ("/api/health", "/api/dataset"):
            if path == "/api/health":
                payload = {"status": "ok", "app": "mapshot", "mode": "static-trial"}
            else:
                try:
                    payload = json.loads((self.root / "data/manifest.json").read_text())
                except (OSError, ValueError):
                    self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Dataset unavailable")
                    return None
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return None
        path = "/index.html" if path == "/" else path
        # Exact path matching denies traversal, directories, raw data and source files.
        allowed = self.server.public_files.get(path)
        if allowed is None or not allowed.resolve().is_relative_to(self.root):
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return None
        self.path = path
        return super().send_head()


def create_server(host="127.0.0.1", port=8097, root=ROOT):
    root = Path(root).resolve()
    if not (root / "index.html").is_file() or not (root / "data/manifest.json").is_file():
        raise ValueError("Missing index.html or data/manifest.json; copy the complete runtime package.")
    server = ThreadingHTTPServer((host, port), functools.partial(Handler, root=root))
    server.public_files = runtime_files(root)
    return server


def main():
    parser = argparse.ArgumentParser(description="Run the Mapshot trial website")
    parser.add_argument("--host", default="127.0.0.1", help="Use 0.0.0.0 for LAN access")
    parser.add_argument("--port", default=8097, type=int)
    args = parser.parse_args()
    with create_server(args.host, args.port) as server:
        print(f"Mapshot: http://{args.host}:{server.server_port}  (Ctrl+C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
