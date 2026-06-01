import pytest
from agent.gemini import extract_initial_prompt_from_response, extract_prompt_from_response

def test_extract_pure_json():
    response = '{"improved_prompt": "A sunny day on the beach, 4k, realistic"}'
    data = extract_prompt_from_response(response)
    assert data["improved_prompt"] == "A sunny day on the beach, 4k, realistic"

def test_extract_markdown_fenced_json():
    response = '''
Here is the evaluation:
```json
{
  "score": 8,
  "improved_prompt": "Better prompt"
}
```
Good luck!
'''
    data = extract_prompt_from_response(response)
    assert data["score"] == 8
    assert data["improved_prompt"] == "Better prompt"

def test_extract_text_before_after_json():
    response = '''Sure, here it is:
{
  "improved_prompt": "Cinematic shot",
  "score": 9
}
I hope this helps.'''
    data = extract_prompt_from_response(response)
    assert data["improved_prompt"] == "Cinematic shot"
    assert data["score"] == 9

def test_invalid_json():
    response = '{"improved_prompt": "Cinematic shot", "score": 9' # Missing closing brace
    with pytest.raises(ValueError, match="Failed to parse JSON"):
        extract_prompt_from_response(response)

def test_missing_improved_prompt():
    response = '{"score": 9, "reason": "Good"}'
    with pytest.raises(ValueError, match="Missing 'improved_prompt'"):
        extract_prompt_from_response(response)

def test_extract_initial_prompt_pure_json():
    response = '{"initial_prompt": "First prompt", "hook": "Look here!"}'
    data = extract_initial_prompt_from_response(response)
    assert data["initial_prompt"] == "First prompt"

def test_extract_initial_prompt_missing_key():
    response = '{"creative_angle": "Angle"}'
    with pytest.raises(ValueError, match="Missing 'initial_prompt'"):
         extract_initial_prompt_from_response(response)
