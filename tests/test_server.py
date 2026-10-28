import gzip
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from server import create_server


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / "data/raw").mkdir(parents=True)
        (root / "index.html").write_text("<h1>Mapshot</h1>")
        (root / "server.py").write_text("private source")
        (root / "data/manifest.json").write_text('{"roadCount": 1}')
        (root / "data/raw/private.json").write_text("private raw data")
        self.geometry = gzip.compress(b'{"type":"FeatureCollection","features":[]}')
        (root / "data/roads.geojson.gz").write_bytes(self.geometry)
        self.server = create_server(port=0, root=root)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, method="GET", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_health_dataset_and_home(self):
        self.assertEqual(json.loads(self.request("/api/health")[2])["status"], "ok")
        self.assertEqual(json.loads(self.request("/api/dataset")[2])["roadCount"], 1)
        self.assertEqual(self.request("/")[0], 200)
        self.assertEqual(self.request("/api/health", "HEAD")[2], b"")

    def test_raw_and_source_files_are_not_published(self):
        for path in ("/server.py", "/data/raw/private.json", "/data/", "/../server.py", "/%2e%2e/server.py", "/data/%2e%2e/server.py"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_gzip_is_not_decompressed_twice_and_cache_revalidates(self):
        status, headers, body = self.request("/data/roads.geojson.gz")
        self.assertEqual(status, 200)
        self.assertNotIn("Content-Encoding", headers)
        self.assertEqual(body, self.geometry)
        self.assertEqual(headers["Cache-Control"], "no-cache")
        status, _, body = self.request("/data/roads.geojson.gz", headers={"If-Modified-Since": headers["Last-Modified"]})
        self.assertEqual(status, 304)
        self.assertEqual(body, b"")


if __name__ == "__main__":
    unittest.main()
