import os
import json
import shutil
from datetime import datetime
from typing import Optional

EXPORTS_DIR = "exports"

def export_post_package(asset_data: dict, evaluation_data: dict, product_bible: dict, prompt_used: str, product_link: str) -> Optional[str]:
    """
    Exports a successful asset into a post package.
    """
    if not asset_data or 'video_path' not in asset_data or not os.path.exists(asset_data['video_path']):
        return None

    os.makedirs(EXPORTS_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    product_slug = product_link.split("/")[-1] if product_link else "unknown"
    if not product_slug or len(product_slug) < 2:
        product_slug = "product"

    asset_id = asset_data.get('id', 'unknown')
    export_folder_name = f"{timestamp}_{product_slug}_asset_{asset_id}"
    export_path = os.path.join(EXPORTS_DIR, export_folder_name)

    os.makedirs(export_path, exist_ok=True)

    # 1. Copy final video
    dest_video_path = os.path.join(export_path, "final_video.mp4")
    shutil.copy2(asset_data['video_path'], dest_video_path)

    # 2. cover_prompt.txt
    with open(os.path.join(export_path, "cover_prompt.txt"), "w", encoding="utf-8") as f:
        f.write("A hyper-realistic close-up of a glossy black articulated dachshund keychain...")

    # 3. tiktok_caption.txt
    with open(os.path.join(export_path, "tiktok_caption.txt"), "w", encoding="utf-8") as f:
        f.write("Check out this cute articulated dachshund! 🐕‍🦺✨ #3dprinting #keychain")

    # 4. reels_caption.txt
    with open(os.path.join(export_path, "reels_caption.txt"), "w", encoding="utf-8") as f:
        f.write("Wait until you see how this keychain moves... 😍 #dachshund #giftideas")

    # 5. shorts_title.txt
    with open(os.path.join(export_path, "shorts_title.txt"), "w", encoding="utf-8") as f:
        f.write("The PERFECT gift for dachshund lovers 🎁")

    # 6. vk_caption.txt
    with open(os.path.join(export_path, "vk_caption.txt"), "w", encoding="utf-8") as f:
        f.write("Идеальный брелок для ключей! Заказать можно по ссылке ниже 👇")

    # 7. hashtags.txt
    with open(os.path.join(export_path, "hashtags.txt"), "w", encoding="utf-8") as f:
        f.write("#dachshund #keychain #gift #3dprinted #cute")

    # 8. product_link.txt
    with open(os.path.join(export_path, "product_link.txt"), "w", encoding="utf-8") as f:
        f.write(product_link if product_link else "N/A")

    # 9. prompt_used.json
    with open(os.path.join(export_path, "prompt_used.json"), "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt_used}, f, ensure_ascii=False, indent=2)

    # 10. evaluation.json
    with open(os.path.join(export_path, "evaluation.json"), "w", encoding="utf-8") as f:
        json.dump(evaluation_data, f, ensure_ascii=False, indent=2)

    # 11. product_bible.json
    with open(os.path.join(export_path, "product_bible.json"), "w", encoding="utf-8") as f:
        json.dump(product_bible, f, ensure_ascii=False, indent=2)

    return export_path
