import pytest
from unittest.mock import patch, MagicMock
import free_vram

@patch("free_vram.requests.post")
def test_free_comfyui_vram_success(mock_post):
    # Setup
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    # Execute
    free_vram.free_comfyui_vram()
    
    # Verify
    assert mock_post.call_count == len(free_vram.SERVERS)
    
@patch("free_vram.requests.post")
def test_free_comfyui_vram_failure(mock_post):
    # Setup
    import requests
    mock_post.side_effect = requests.exceptions.RequestException("Timeout")
    
    # Execute - should not raise exception, just print error
    free_vram.free_comfyui_vram()
    
    # Verify
    assert mock_post.call_count == len(free_vram.SERVERS)
