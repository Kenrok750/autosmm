SEVERE_REJECT_REASONS = [
    "wrong_product",
    "morphed_product",
    "wrong_color",
    "real_dog_instead_of_keychain",
    "missing_chain_or_ring",
    "product_not_visible",
    "unsafe_or_misleading_claim"
]

def determine_asset_status(eval_data: dict) -> str:
    """
    Determines if the asset should be auto-rejected or marked for human review
    based on backend decision rules.
    """
    if not isinstance(eval_data, dict):
        return "ai_rejected"

    try:
        product_identity_accuracy = float(eval_data.get("product_identity_accuracy", 0))
        product_visibility = float(eval_data.get("product_visibility", 0))
        use_case_clarity = float(eval_data.get("use_case_clarity", 0))
        visual_quality = float(eval_data.get("visual_quality", 0))
        score = float(eval_data.get("score", 0))
        approved_for_human_review = bool(eval_data.get("approved_for_human_review", False))
        reject_reasons = eval_data.get("reject_reasons", [])
        if not isinstance(reject_reasons, list):
            reject_reasons = []
    except (ValueError, TypeError):
        return "ai_rejected"

    if product_identity_accuracy < 7:
        return "ai_rejected"

    if product_visibility < 6:
        return "ai_rejected"

    if use_case_clarity < 6:
        return "ai_rejected"

    if visual_quality < 5:
        return "ai_rejected"

    for reason in reject_reasons:
        if reason in SEVERE_REJECT_REASONS:
            return "ai_rejected"

    if score >= 7 and approved_for_human_review:
        return "human_review"

    return "ai_rejected"
