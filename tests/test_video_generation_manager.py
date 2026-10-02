import pytest
from unittest.mock import patch, MagicMock
import json
import video_generation_manager

def test_patch_workflow():
    wf = {
        "1": {
            "class_type": "some_node",
            "_meta": {"title": "Prompt (Positive)"},
            "inputs": {"text": "Original text"}
        },
        "2": {
            "class_type": "some_node",
            "_meta": {"title": "Sampler"},
            "inputs": {"seed": 12345}
        }
    }
    inputs = {"prompt": "New prompt text", "seed": 999}
    
    video_generation_manager.patch_workflow(wf, inputs)
    
    assert wf["1"]["inputs"]["text"] == "New prompt text"
    assert wf["2"]["inputs"]["seed"] == 999

@patch("video_generation_manager.requests.post")
def test_free_comfyui_vram(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    video_generation_manager.free_comfyui_vram()
    
    assert mock_post.call_count == len(video_generation_manager.COMFYUI_SERVERS)

@patch("video_generation_manager.requests.post")
@patch("video_generation_manager.requests.get")
@patch("video_generation_manager.os.path.exists", return_value=True)
@patch("builtins.open", new_callable=MagicMock)
def test_generate_video(mock_open, mock_exists, mock_get, mock_post):
    task = {
        "workflow": "test_workflow.json",
        "inputs": {"prompt": "Test video"}
    }
    
    # Mock json.load
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    with patch("json.load", return_value={"1": {"inputs": {}, "class_type": "test"}}):
        
        # Mock Queue Workflow Post
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"prompt_id": "123"}
        mock_post.return_value = mock_post_response
        
        # Mock History Get
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"123": {"outputs": {}}}
        mock_get.return_value = mock_get_response
        
        result = video_generation_manager.generate_video(task, "http://fake-server")
        
        assert result is True
        mock_post.assert_called()
        mock_get.assert_called()

@patch("video_generation_manager.requests.get")
@patch("video_generation_manager.os.makedirs")
@patch("builtins.open", new_callable=MagicMock)
def test_download_comfyui_outputs_with_video(mock_open, mock_makedirs, mock_get):
    history_result = {
        "outputs": {
            "99": {
                "gifs": [{"filename": "my_output.mp4"}]
            }
        }
    }
    
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.content = b"fakevideo"
    mock_get.return_value = mock_get_response
    
    files = video_generation_manager.download_comfyui_outputs("http://fake-server", history_result, "task_01", "LTX-2.5.json")
    
    assert len(files) == 1
    assert "task_01_99.mp4" in files[0]
    mock_open.assert_called()
