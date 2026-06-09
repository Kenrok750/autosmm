import pytest
from agent.evaluation import determine_asset_status

def test_missing_data():
    assert determine_asset_status({}) == "ai_rejected"
    assert determine_asset_status(None) == "ai_rejected"

def test_low_identity_accuracy():
    eval_data = {
        "product_identity_accuracy": 6,
        "product_visibility": 8,
        "use_case_clarity": 8,
        "visual_quality": 8,
        "score": 8,
        "approved_for_human_review": True
    }
    assert determine_asset_status(eval_data) == "ai_rejected"

def test_severe_reject_reason():
    eval_data = {
        "product_identity_accuracy": 9,
        "product_visibility": 9,
        "use_case_clarity": 9,
        "visual_quality": 9,
        "score": 9,
        "approved_for_human_review": True,
        "reject_reasons": ["wrong_color"]
    }
    assert determine_asset_status(eval_data) == "ai_rejected"

def test_human_review_success():
    eval_data = {
        "product_identity_accuracy": 9,
        "product_visibility": 9,
        "use_case_clarity": 9,
        "visual_quality": 9,
        "score": 8,
        "approved_for_human_review": True,
        "reject_reasons": []
    }
    assert determine_asset_status(eval_data) == "human_review"

def test_human_review_not_approved():
    eval_data = {
        "product_identity_accuracy": 9,
        "product_visibility": 9,
        "use_case_clarity": 9,
        "visual_quality": 9,
        "score": 8,
        "approved_for_human_review": False,
        "reject_reasons": []
    }
    assert determine_asset_status(eval_data) == "ai_rejected"
