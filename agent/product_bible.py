DEFAULT_DACHSHUND_BIBLE = {
    "product_name": "Glossy Black Articulated Dachshund Keychain",
    "target_audience": "girls/women 14-35, students, bag/pencil-case accessory buyers",
    "material": "SLA resin / rigid plastic",
    "color": "Glossy Black",
    "must_show": "glossy black articulated dachshund keychain, segmented flexible body, short legs, metal chain/ring, attached to pencil case/bag/keys",
    "must_not_show": "real dog, plush toy, fur, extra legs, wrong color, missing ring/chain, material change, gold/silver recolor unless explicitly requested",
    "selling_points": "Cute, articulated (moves satisfyingly), durable, perfect gift.",
    "usage_scenarios": "Hanging on a backpack, twirling on car keys, holding in hand to show movement.",
    "forbidden_claims": "Indestructible, real metal, suitable for small children (choking hazard)."
}

def format_bible_for_prompt(bible_data: dict) -> str:
    """
    Formats the product bible dictionary into a string suitable for inclusion in a Gemini prompt.
    """
    if not bible_data:
        return "No specific product guidelines provided."

    lines = [
        "PRODUCT BIBLE (STRICT GUIDELINES):",
        f"- Product Name: {bible_data.get('product_name', 'N/A')}",
        f"- Target Audience: {bible_data.get('target_audience', 'N/A')}",
        f"- Material: {bible_data.get('material', 'N/A')}",
        f"- Color: {bible_data.get('color', 'N/A')}",
        f"- MUST SHOW: {bible_data.get('must_show', 'N/A')}",
        f"- MUST NOT SHOW (CRITICAL): {bible_data.get('must_not_show', 'N/A')}",
        f"- Selling Points: {bible_data.get('selling_points', 'N/A')}",
        f"- Usage Scenarios: {bible_data.get('usage_scenarios', 'N/A')}",
        f"- Forbidden Claims: {bible_data.get('forbidden_claims', 'N/A')}"
    ]

    return "\n".join(lines)
