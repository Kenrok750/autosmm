import pytest
from agent.product_bible import DEFAULT_DACHSHUND_BIBLE, format_bible_for_prompt

def test_default_bible_exists():
    assert "Glossy Black Articulated Dachshund Keychain" in DEFAULT_DACHSHUND_BIBLE["product_name"]
    assert "Glossy Black" in DEFAULT_DACHSHUND_BIBLE["color"]
    assert "Real animal fur" in DEFAULT_DACHSHUND_BIBLE["must_not_show"]

def test_format_bible_empty():
    res = format_bible_for_prompt({})
    assert res == "No specific product guidelines provided."

def test_format_bible_populated():
    res = format_bible_for_prompt(DEFAULT_DACHSHUND_BIBLE)
    assert "PRODUCT BIBLE (STRICT GUIDELINES):" in res
    assert "- Color: Glossy Black" in res
    assert "- MUST NOT SHOW (CRITICAL): Real animal fur" in res
