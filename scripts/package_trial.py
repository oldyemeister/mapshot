"""Build a portable runtime ZIP; never include raw data, venvs or generated images."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import runtime_files


def main():
    output = ROOT / "dist/mapshot-trial.zip"
    output.parent.mkdir(exist_ok=True)
    files = list(runtime_files(ROOT).values())
    files += [ROOT / p for p in ("server.py", "start.sh", "start.command", "README.md", "docs/DEPLOYMENT.md", "docs/PROJECT.md", "docs/VERIFICATION.md", "docs/VERSION_CONTROL.md", "AGENTS.md", "PRODUCT.md", "DESIGN.md")]
    inventory = []
    temporary = output.with_suffix(".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            content = path.read_bytes()
            relative = path.relative_to(ROOT).as_posix()
            archive.write(path, "mapshot/" + relative)
            inventory.append({"path": relative, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        archive.writestr("mapshot/package-manifest.json", json.dumps(inventory, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Package integrity check failed")
    temporary.replace(output)
    print(json.dumps({"files": len(files), "runtimeBytes": sum(x["bytes"] for x in inventory), "zipBytes": output.stat().st_size, "path": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
