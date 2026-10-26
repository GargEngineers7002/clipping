import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
import tts_generation_manager

@patch("tts_generation_manager.requests.get")
def test_get_alive_server(mock_get):
    # Setup
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    # Execute
    server = tts_generation_manager.get_alive_server()
    
    # Verify
    assert server == tts_generation_manager.TTS_SERVERS[0]
    
@patch("tts_generation_manager.requests.get")
def test_get_alive_server_failure(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.RequestException("Offline")
    
    # Execute
    server = tts_generation_manager.get_alive_server()
    
    # Verify
    assert server is None

def test_chunk_text():
    text = "Hello world. " * 100
    chunks = tts_generation_manager.chunk_text(text)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 1020

@patch("tts_generation_manager.requests.post")
@patch("builtins.open", new_callable=mock_open, read_data=b"fake image data")
def test_upload_to_comfyui(mock_file, mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"name": "uploaded_file.mp3"}
    mock_post.return_value = mock_response
    
    result = tts_generation_manager.upload_to_comfyui("http://fake-server", "/fake/path.mp3")
    assert result == "uploaded_file.mp3"

@patch("tts_generation_manager.requests.post")
def test_patch_and_queue_tts(mock_post):
    wf = {
        "1": {
            "class_type": "some_node",
            "_meta": {"title": "Text Node"},
            "inputs": {"text": "Original text", "instruction": "Original instruction"}
        }
    }
    inputs = {"text": "Patched text", "instruction": "Patched instruction"}
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"prompt_id": "12345"}
    mock_post.return_value = mock_response
    
    prompt_id, client_id = tts_generation_manager.patch_and_queue_tts(wf, inputs, "http://fake-server")
    
    assert prompt_id == "12345"
    assert client_id is not None
