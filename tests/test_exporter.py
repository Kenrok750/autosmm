import pytest
import os
import shutil
from agent.exporter import export_post_package, EXPORTS_DIR

@pytest.fixture
def cleanup_exports():
    yield
    if os.path.exists(EXPORTS_DIR):
        shutil.rmtree(EXPORTS_DIR)

def test_export_post_package(cleanup_exports, tmp_path):
    # Create a fake video
    fake_video = tmp_path / "test_video.mp4"
    fake_video.write_text("dummy content")

    asset_data = {
        "id": 42,
        "video_path": str(fake_video)
    }
    eval_data = {"score": 9}
    bible = {"product_name": "Test"}
    prompt = "Test prompt"
    link = "http://wb.ru/item/123"

    export_path = export_post_package(asset_data, eval_data, bible, prompt, link)

    assert export_path is not None
    assert os.path.exists(export_path)

    # Check if files are created
    assert os.path.exists(os.path.join(export_path, "final_video.mp4"))
    assert os.path.exists(os.path.join(export_path, "cover_prompt.txt"))
    assert os.path.exists(os.path.join(export_path, "prompt_used.json"))
    assert os.path.exists(os.path.join(export_path, "evaluation.json"))
    assert os.path.exists(os.path.join(export_path, "product_bible.json"))

def test_export_missing_video(cleanup_exports):
    asset_data = {"id": 1, "video_path": "nonexistent.mp4"}
    res = export_post_package(asset_data, {}, {}, "", "")
    assert res is None
