DEFAULT_DACHSHUND_BIBLE = {
    "product_name": "Glossy Black Articulated Dachshund Keychain",
    "target_audience": "Dog lovers, dachshund owners, keychain collectors, people who like 3D printed gadgets.",
    "material": "SLA resin / rigid plastic",
    "color": "Glossy Black",
    "must_show": "The metallic keychain ring/chain attached to the dog. The articulation (the body bending or moving). The glossy plastic texture reflecting light.",
    "must_not_show": "Real animal fur. Real dogs. Photorealistic biological dogs. Morphing into a real animal. Matte or rough textures.",
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
