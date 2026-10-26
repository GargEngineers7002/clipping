import os
from unittest.mock import patch, mock_open, MagicMock
import pytest
import client_ag

@patch("client_ag.requests.post")
@patch("client_ag.os.makedirs")
@patch("builtins.open", new_callable=mock_open)
def test_stylize_video_success(mock_file, mock_makedirs, mock_post):
    # Setup
    video_path = "/fake/dir/video.mp4"
    server_url = "http://fake-server/process-video"
    model_type = "shinkai"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake video content"
    mock_post.return_value = mock_response

    # Execute
    client_ag.stylize_video(video_path, server_url, model_type)

    # Verify
    mock_post.assert_called_once()
    mock_makedirs.assert_called_once()
    
    # Ensure it writes the output video
    handle = mock_file()
    handle.write.assert_called_with(b"fake video content")

@patch("client_ag.requests.post")
@patch("builtins.open", new_callable=mock_open)
def test_stylize_video_failure(mock_file, mock_post):
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
    assert handle.write.call_count == 0

@patch("client_ag.input", return_value="1")
@patch("client_ag.os.chdir")
@patch("client_ag.glob.glob", return_value=["test1.mp4", "anonymized_test2.mp4"])
@patch("client_ag.ThreadPoolExecutor")
def test_process_directory(mock_executor, mock_glob, mock_chdir, mock_input):
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
