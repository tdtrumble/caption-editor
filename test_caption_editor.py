import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from caption_editor import CaptionServer, load_access_keys


class CaptionServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.images = self.root / "images"
        self.images.mkdir()
        (self.images / "sample.png").write_bytes(b"not-a-real-png")
        self.server = CaptionServer(("127.0.0.1", 0), self.root, "test-key")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(self, path, params=None, method="GET", payload=None):
        query = {"key": "test-key", **(params or {})}
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(f"{self.base}{path}?{urlencode(query)}", data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        return urlopen(request, timeout=2)

    def test_lists_images_and_round_trips_caption(self):
        with self.request("/api/images", {"folder": "images"}) as response:
            data = json.load(response)
        self.assertEqual(data["files"], [{"name": "sample.png", "hasCaption": False}])

        with self.request(
            "/api/caption",
            {"folder": "images", "name": "sample.png"},
            method="PUT",
            payload={"caption": "a useful caption"},
        ) as response:
            self.assertTrue(json.load(response)["saved"])

        self.assertEqual((self.images / "sample.txt").read_text(encoding="utf-8"), "a useful caption")

    def test_rejects_missing_key_and_path_traversal(self):
        with self.assertRaises(HTTPError) as unauthorized:
            urlopen(f"{self.base}/api/images?folder=images", timeout=2)
        self.assertEqual(unauthorized.exception.code, 401)

        with self.assertRaises(HTTPError) as traversal:
            self.request("/api/images", {"folder": "../"})
        self.assertEqual(traversal.exception.code, 400)

    def test_loads_custom_access_keys(self):
        keys_file = self.root / "keys.txt"
        keys_file.write_text("# favorites\n apple \n\nriver\n", encoding="utf-8")
        self.assertEqual(load_access_keys(keys_file), ["apple", "river"])


if __name__ == "__main__":
    unittest.main()
