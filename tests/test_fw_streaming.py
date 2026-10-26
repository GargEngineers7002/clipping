import os
import json
import shutil
import tempfile
import threading
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler
from requests_toolbelt import MultipartEncoder

import fw_client


class ChunkTrackingFile:
    """A file-like object with a real file descriptor that tracks each read(size) call."""
    def __init__(self, raw_file):
        self._f = raw_file
        self.read_sizes = []

    def fileno(self):
        return self._f.fileno()

    def tell(self):
        return self._f.tell()

    def seek(self, offset, whence=0):
        return self._f.seek(offset, whence)

    def read(self, size=-1):
        self.read_sizes.append(size)
        return self._f.read(size)


class MockServerHandler(BaseHTTPRequestHandler):
    """Mock HTTP handler to verify multipart streaming uploads."""
    last_content_type = None
    last_body = None

    def log_message(self, format, *args):
        # Suppress server stderr logging during tests
        pass

    def do_POST(self):
        MockServerHandler.last_content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))

        # Stream body in 8KB chunks as the server would
        body_chunks = []
        bytes_left = content_length
        while bytes_left > 0:
            chunk = self.rfile.read(min(bytes_left, 8192))
            if not chunk:
                break
            body_chunks.append(chunk)
            bytes_left -= len(chunk)

        MockServerHandler.last_body = b"".join(body_chunks)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Connection", "close")
        self.end_headers()
        response_payload = {
            "language": "en",
            "language_probability": 0.99,
            "duration": 5.0,
            "segments": [{"start": 0.0, "end": 5.0, "text": "Test transcript"}]
        }
        self.wfile.write(json.dumps(response_payload).encode("utf-8"))


class TestStreamingUpload(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_server_url = fw_client.SERVER_URL
        self.orig_transcripts_dir = fw_client.TRANSCRIPTS_DIR
        fw_client.TRANSCRIPTS_DIR = os.path.join(self.test_dir, "transcripts")
        os.makedirs(fw_client.TRANSCRIPTS_DIR, exist_ok=True)

    def tearDown(self):
        fw_client.SERVER_URL = self.orig_server_url
        fw_client.TRANSCRIPTS_DIR = self.orig_transcripts_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_multipart_encoder_reads_in_chunks(self):
        """Verify MultipartEncoder reads the file in chunks and does not perform a single whole-file read."""
        sample_path = os.path.join(self.test_dir, "test_chunk.mp4")
        payload_data = b"X" * (1024 * 100)  # 100 KB
        with open(sample_path, "wb") as f:
            f.write(payload_data)

        with open(sample_path, "rb") as raw_f:
            tracker = ChunkTrackingFile(raw_f)
            encoder = MultipartEncoder(fields={"file": ("video.mp4", tracker, "application/octet-stream")})

            # Read through the encoder in 8192-byte chunks (as urllib3 / requests does)
            total_bytes = 0
            while True:
                chunk = encoder.read(8192)
                if not chunk:
                    break
                total_bytes += len(chunk)

            # The underlying file stream should be read via multiple chunked calls (not in a single full read)
            self.assertGreater(len(tracker.read_sizes), 1, "File should be read in multiple chunks")
            for s in tracker.read_sizes:
                self.assertNotEqual(s, -1, "Read should never be unbounded (-1)")

    def test_process_video_e2e_with_mock_server(self):
        """Verify process_video successfully uploads to the server via MultipartEncoder and writes transcript."""
        # Start a mock HTTP server on an ephemeral port
        server = HTTPServer(("127.0.0.1", 0), MockServerHandler)
        port = server.server_port
        server_thread = threading.Thread(target=server.handle_request, daemon=True)
        server_thread.start()

        fw_client.SERVER_URL = f"http://127.0.0.1:{port}/transcribe"

        # Create a test video file
        sample_video_path = os.path.join(self.test_dir, "sample_clip.mp4")
        test_content = b"Mock MP4 Binary Stream Data"
        with open(sample_video_path, "wb") as f:
            f.write(test_content)

        # Execute process_video
        success = fw_client.process_video(sample_video_path)
        server_thread.join(timeout=5)
        server.server_close()

        self.assertTrue(success, "process_video should succeed")

        # Verify server received correct Content-Type header with multipart boundary
        self.assertTrue(
            MockServerHandler.last_content_type.startswith("multipart/form-data; boundary="),
            f"Unexpected Content-Type: {MockServerHandler.last_content_type}"
        )

        # Verify body contains the filename and file payload
        self.assertIn(b'filename="sample_clip.mp4"', MockServerHandler.last_body)
        self.assertIn(test_content, MockServerHandler.last_body)

        # Verify transcript was written to disk
        expected_transcript_path = os.path.join(fw_client.TRANSCRIPTS_DIR, "sample_clip.json")
        self.assertTrue(os.path.exists(expected_transcript_path), "Transcript file was not created")

        with open(expected_transcript_path, "r", encoding="utf-8") as tf:
            data = json.load(tf)
            self.assertEqual(data["language"], "en")
            self.assertEqual(data["segments"][0]["text"], "Test transcript")


if __name__ == "__main__":
    unittest.main()
