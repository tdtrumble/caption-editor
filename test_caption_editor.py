import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from caption_editor import CaptionServer, listening_pids_from_netstat, load_access_keys


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
        self.assertEqual(data["captionExtension"], ".txt")
        self.assertFalse((self.images / "sample.txt").exists())

        with self.request(
            "/api/caption",
            {"folder": "images", "name": "sample.png"},
            method="PUT",
            payload={"caption": "a useful caption"},
        ) as response:
            self.assertTrue(json.load(response)["saved"])

        self.assertEqual((self.images / "sample.txt").read_text(encoding="utf-8"), "a useful caption")

        with self.request("/api/caption", {"folder": "images", "name": "sample.png"}) as response:
            self.assertEqual(json.load(response), {"caption": "a useful caption", "exists": True})

    def test_uses_a_requested_caption_extension_for_listing_loading_and_saving(self):
        (self.images / "sample.sdxl_caption").write_text("SDXL caption", encoding="utf-8")

        with self.request("/api/images", {"folder": "images", "extension": ".sdxl_caption"}) as response:
            data = json.load(response)
        self.assertEqual(data["captionExtension"], ".sdxl_caption")
        self.assertTrue(data["files"][0]["hasCaption"])

        with self.request(
            "/api/caption",
            {"folder": "images", "name": "sample.png", "extension": "sdxl_caption"},
        ) as response:
            self.assertEqual(json.load(response), {"caption": "SDXL caption", "exists": True})

        with self.request(
            "/api/caption",
            {"folder": "images", "name": "sample.png", "extension": ".new_caption"},
            method="PUT",
            payload={"caption": "new extension caption"},
        ):
            pass
        self.assertEqual((self.images / "sample.new_caption").read_text(encoding="utf-8"), "new extension caption")
        self.assertEqual((self.images / "sample.sdxl_caption").read_text(encoding="utf-8"), "SDXL caption")

    def test_rejects_unsafe_or_image_caption_extensions(self):
        with self.assertRaises(HTTPError) as image_extension:
            self.request("/api/images", {"folder": "images", "extension": ".png"})
        self.assertEqual(image_extension.exception.code, 400)

        with self.assertRaises(HTTPError) as path_extension:
            self.request("/api/images", {"folder": "images", "extension": "../caption"})
        self.assertEqual(path_extension.exception.code, 400)

    def test_read_only_mode_allows_viewing_but_rejects_caption_writes(self):
        caption_path = self.images / "sample.txt"
        caption_path.write_text("original caption", encoding="utf-8")
        self.server.read_only = True

        with self.request("/api/config") as response:
            self.assertEqual(json.load(response), {"readOnly": True, "defaultCaptionExtension": ".txt"})

        with self.request("/api/caption", {"folder": "images", "name": "sample.png"}) as response:
            self.assertEqual(json.load(response), {"caption": "original caption", "exists": True})

        with self.assertRaises(HTTPError) as forbidden:
            self.request(
                "/api/caption",
                {"folder": "images", "name": "sample.png"},
                method="PUT",
                payload={"caption": "changed caption"},
            )
        self.assertEqual(forbidden.exception.code, 403)
        self.assertEqual(caption_path.read_text(encoding="utf-8"), "original caption")

        with self.assertRaises(HTTPError) as create_forbidden:
            self.request(
                "/api/caption",
                {"folder": "images", "name": "sample.png", "extension": ".new_caption"},
                method="PUT",
                payload={"caption": "new caption"},
            )
        self.assertEqual(create_forbidden.exception.code, 403)
        self.assertFalse((self.images / "sample.new_caption").exists())

    def test_rejects_missing_key_and_path_traversal(self):
        with self.assertRaises(HTTPError) as unauthorized:
            urlopen(f"{self.base}/api/images?folder=images", timeout=2)
        self.assertEqual(unauthorized.exception.code, 401)

        with self.assertRaises(HTTPError) as traversal:
            self.request("/api/images", {"folder": "../"})
        self.assertEqual(traversal.exception.code, 400)

    def test_browse_lists_all_root_subdirectories(self):
        hidden_images = self.root / ".hidden-images"
        hidden_images.mkdir()
        (hidden_images / "hidden.jpg").write_bytes(b"not-a-real-jpg")

        with self.request("/api/browse", {"folder": "."}) as response:
            data = json.load(response)

        self.assertEqual(
            data["directories"],
            [
                {"name": ".hidden-images", "path": ".hidden-images", "imageCount": 1},
                {"name": "images", "path": "images", "imageCount": 1},
            ],
        )

    def test_bare_local_url_redirects_to_authenticated_ui(self):
        with urlopen(f"{self.base}/", timeout=2) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), f"{self.base}/?key=test-key")
            self.assertIn(b"Caption Editor", response.read())

    def test_does_not_share_an_existing_listening_port(self):
        with self.assertRaises(OSError):
            CaptionServer(("127.0.0.1", self.server.server_address[1]), self.root, "other-key")

    def test_finds_process_listening_on_exact_windows_port(self):
        output = """
          TCP    0.0.0.0:8070       0.0.0.0:0       LISTENING       1234
          TCP    127.0.0.1:80701    0.0.0.0:0       LISTENING       9999
          TCP    [::]:8070          [::]:0          LISTENING       1234
          TCP    127.0.0.1:8070     127.0.0.1:50000 ESTABLISHED     5678
        """
        self.assertEqual(listening_pids_from_netstat(output, 8070), [1234])

    def test_loads_custom_access_keys(self):
        keys_file = self.root / "keys.txt"
        keys_file.write_text("# favorites\n apple \n\nriver\n", encoding="utf-8")
        self.assertEqual(load_access_keys(keys_file), ["apple", "river"])


if __name__ == "__main__":
    unittest.main()
