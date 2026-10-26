import os
import json
from unittest.mock import patch, mock_open, MagicMock
import pytest
import fw_client

@patch("fw_client.requests.post")
@patch("fw_client.os.path.exists")
@patch("builtins.open", new_callable=mock_open, read_data=b"mock video data")
def test_process_video_success(mock_file, mock_exists, mock_post):
    mock_file.return_value.getvalue.return_value = b"mock video data"
    # Setup
    video_path = "/fake/dir/video.mp4"
    mock_exists.return_value = False  # Transcript does not exist
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "Transcribed text"}
    mock_post.return_value = mock_response

    # Execute
    result = fw_client.process_video(video_path)

    # Verify
    assert result is True
    mock_post.assert_called_once()
    mock_response.raise_for_status.assert_called_once()
    
    # Ensure it writes the transcript
    handle = mock_file()
    handle.write.assert_called()

@patch("fw_client.os.path.exists")
def test_process_video_already_exists(mock_exists):
    # Setup
    video_path = "/fake/dir/video.mp4"
    mock_exists.return_value = True  # Transcript already exists
    
    # Execute
    result = fw_client.process_video(video_path)

    # Verify
    assert result is True
