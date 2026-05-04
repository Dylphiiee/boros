#!/usr/bin/env python3
import json
import os
import requests
import hashlib
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).parent.parent
IMAGES_DIR = ROOT_DIR / "images"
IMG_JSON = ROOT_DIR / "img.json"
CDN_LOG = ROOT_DIR / "cdn_links.json"

def load_json(path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def sanitize_filename(filename):
    name, ext = os.path.splitext(filename)
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    clean = "".join(c if c in safe else "_" for c in name)[:50]
    return f"{clean}{ext.lower()}"

def download_image(url, save_path, timeout=30):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BorosGalleryBot/1.0)"}
        r = requests.get(url, headers=headers, timeout=timeout, stream=True)
        r.raise_for_status()
        if not r.headers.get("content-type", "").startswith("image/"):
            return False
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"❌ Gagal download: {e}")
        return False

def get_hash(filepath):
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()

def process_images():
    IMAGES_DIR.mkdir(exist_ok=True)
    cdn_links = load_json(CDN_LOG, [])
    img_data = load_json(IMG_JSON, {"images": [], "last_updated": None})

    if not cdn_links:
        print("📭 Tidak ada CDN links.")
        return False

    existing_files = {img["filename"] for img in img_data["images"]}
    existing_hashes = set()
    for f in IMAGES_DIR.iterdir():
        if f.is_file() and not f.name.startswith('.'):
            try:
                existing_hashes.add(get_hash(f))
            except:
                pass

    processed = 0
    updated = False

    for i, link in enumerate(cdn_links):
        if link.get("processed", False):
            continue

        url = link["url"]
        original = link.get("filename", "image.jpg")
        print(f"\n🔄 Proses: {original}")

        safe = sanitize_filename(original)
        save_path = IMAGES_DIR / safe
        stem, suffix = Path(safe).stem, Path(safe).suffix
        counter = 1
        while save_path.exists() or safe in existing_files:
            safe = f"{stem}_{counter}{suffix}"
            save_path = IMAGES_DIR / safe
            counter += 1

        temp = IMAGES_DIR / f"_temp_{safe}"
        if download_image(url, temp):
            h = get_hash(temp)
            if h in existing_hashes:
                print("   ⚠️ Duplikat, skip.")
                temp.unlink()
                cdn_links[i]["processed"] = True
                cdn_links[i]["skip_reason"] = "duplicate"
                continue

            temp.rename(save_path)
            existing_hashes.add(h)

            img_data["images"].append({
                "filename": safe,
                "original_filename": original,
                "uploaded_by": link.get("uploaded_by", "Unknown"),
                "timestamp": link.get("timestamp", datetime.utcnow().isoformat()),
                "url": f"images/{safe}",
                "hash": h
            })
            existing_files.add(safe)
            cdn_links[i]["processed"] = True
            cdn_links[i]["saved_as"] = safe
            processed += 1
            updated = True
            print(f"   ✅ Disimpan: {safe}")
        else:
            if temp.exists():
                temp.unlink()
            cdn_links[i]["processed"] = True
            cdn_links[i]["skip_reason"] = "download_failed"

    if updated:
        img_data["last_updated"] = datetime.utcnow().isoformat()
        img_data["total_count"] = len(img_data["images"])
        save_json(CDN_LOG, cdn_links)
        save_json(IMG_JSON, img_data)
        print(f"\n🎉 {processed} gambar baru! Total: {img_data['total_count']}")
        return True
    else:
        save_json(CDN_LOG, cdn_links)
        print("\n✨ Tidak ada gambar baru.")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Boros Gallery - Image Processor")
    print("=" * 50)
    process_images()
