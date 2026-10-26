import os
import unittest
from unittest.mock import patch, mock_open, MagicMock
from requests_toolbelt import MultipartEncoder
import client_ag

class TestClientAG(unittest.TestCase):
    @patch("client_ag.requests.post")
    @patch("client_ag.os.makedirs")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake video data")
    def test_stylize_video_success(self, mock_file, mock_makedirs, mock_post):
        mock_file.return_value.getvalue.return_value = b"fake video data"
        # Setup
        video_path = "/fake/dir/video.mp4"
        server_url = "http://fake-server/process-video"
        model_type = "shinkai"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"fake video content"]
        mock_post.return_value = mock_response

        # Execute
        client_ag.stylize_video(video_path, server_url, model_type)

        # Verify
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], server_url)
        self.assertIsInstance(kwargs["data"], MultipartEncoder)
        self.assertTrue(kwargs["stream"])
        mock_makedirs.assert_called_once()
        
        # Ensure it writes the output video chunks
        handle = mock_file()
        handle.write.assert_called_with(b"fake video content")

    @patch("client_ag.requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake video data")
    def test_stylize_video_failure(self, mock_file, mock_post):
        mock_file.return_value.getvalue.return_value = b"fake video data"
        # Setup
        video_path = "/fake/dir/video.mp4"
        server_url = "http://fake-server/process-video"
        model_type = "hayao"
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        # Execute
        client_ag.stylize_video(video_path, server_url, model_type)

        # Verify
        mock_post.assert_called_once()
        # Shouldn't write output if failed
        handle = mock_file()
        self.assertEqual(handle.write.call_count, 0)

    @patch("client_ag.input", return_value="1")
    @patch("client_ag.os.chdir")
    @patch("client_ag.glob.glob", return_value=["test1.mp4", "anonymized_test2.mp4"])
    @patch("client_ag.ThreadPoolExecutor")
    def test_process_directory(self, mock_executor, mock_glob, mock_chdir, mock_input):
        # Setup
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance

        # Execute
        client_ag.process_directory()

        # Verify
        mock_chdir.assert_called_once_with(client_ag.INPUT_DIR)
        mock_glob.assert_called_once_with("*.mp4")
        # Only test1.mp4 should be processed (anonymized_ should be filtered out)
        mock_executor_instance.submit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
