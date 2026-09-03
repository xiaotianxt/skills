#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).parents[1] / "scripts" / "canvas_api.py"
SPEC = importlib.util.spec_from_file_location("canvas_api", SCRIPT)
assert SPEC and SPEC.loader
canvas_api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(canvas_api)


class FakeClient:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.downloads = 0

    def download_public_url(self, _url: str, destination: pathlib.Path) -> None:
        self.downloads += 1
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.payload)


class CanvasApiTests(unittest.TestCase):
    def test_redacts_secret_fields_and_url_parameters(self):
        value = {
            "token": "secret",
            "description": '<a href="https://canvas.test/file?verifier=secret&amp;wrap=1">x</a>',
            "url": "https://canvas.test/file?download_frd=1&access_token=secret",
        }

        redacted = canvas_api.redact_secrets(value)

        self.assertEqual(redacted["token"], "[REDACTED]")
        self.assertNotIn("secret", json.dumps(redacted))
        self.assertIn("download_frd=1", redacted["url"])
        self.assertIn("verifier=[REDACTED]", redacted["description"])

    def test_extracts_next_pagination_link(self):
        header = (
            '<https://canvas.test/api?page=1>; rel="current", '
            '<https://canvas.test/api?page=2>; rel="next"'
        )
        self.assertEqual(
            canvas_api.extract_next_link(header), "https://canvas.test/api?page=2"
        )

    def test_download_preserves_canvas_folder_and_is_incremental(self):
        payload = b"course material"
        files = [
            {
                "id": "42",
                "folder_id": "7",
                "filename": "Lecture 1.pdf",
                "size": len(payload),
                "updated_at": "2026-09-03T12:00:00Z",
                "url": "https://canvas.test/files/42?verifier=secret",
            }
        ]
        folders = [{"id": "7", "full_name": "course files/Post-Lecture Notes"}]

        with tempfile.TemporaryDirectory() as temporary:
            out = pathlib.Path(temporary)
            client = FakeClient(payload)
            first = canvas_api.download_course_files(client, files, folders, out)
            second = canvas_api.download_course_files(client, files, folders, out)

            destination = out / "course-files/Post-Lecture Notes/Lecture 1.pdf"
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(first[0]["status"], "downloaded")
            self.assertEqual(second[0]["status"], "existing")
            self.assertEqual(client.downloads, 1)

    def test_existing_file_without_remote_timestamp_is_reverified(self):
        payload = b"current content"
        files = [
            {
                "id": "42",
                "folder_id": "7",
                "filename": "Lecture.pdf",
                "size": len(payload),
                "updated_at": "2026-09-03T12:00:00Z",
                "url": "https://canvas.test/files/42?verifier=secret",
            }
        ]
        folders = [{"id": "7", "full_name": "course files/Notes"}]

        with tempfile.TemporaryDirectory() as temporary:
            out = pathlib.Path(temporary)
            destination = out / "course-files/Notes/Lecture.pdf"
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b"x" * len(payload))
            canvas_api.write_json(
                out / "course-files-manifest.json",
                [
                    {
                        "id": "42",
                        "path": "course-files/Notes/Lecture.pdf",
                        "size": len(payload),
                        "sha256": canvas_api.sha256_file(destination),
                    }
                ],
            )
            client = FakeClient(payload)

            manifest = canvas_api.download_course_files(client, files, folders, out)

            self.assertEqual(manifest[0]["status"], "updated")
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(client.downloads, 1)

    def test_rejects_previous_manifest_path_outside_course_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = pathlib.Path(temporary)
            destination = canvas_api.manifest_destination(
                out,
                {"id": "42", "filename": "safe.pdf"},
                {"full_name": "course files/Notes"},
                {"path": "../outside.pdf"},
            )

            self.assertEqual(destination, out / "course-files/Notes/safe.pdf")


if __name__ == "__main__":
    unittest.main()
