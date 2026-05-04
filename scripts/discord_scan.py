#!/usr/bin/env python3
import discord
import json
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path

TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 0))
CDN_LOG = Path("cdn_links.json")
SCAN_LIMIT = 100
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}

def is_image(filename):
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS

def load_cdn_links():
    if CDN_LOG.exists():
        with open(CDN_LOG) as f:
            return json.load(f)
    return []

def save_cdn_links(links):
    with open(CDN_LOG, "w") as f:
        json.dump(links, f, indent=2, ensure_ascii=False)

async def scan_discord():
    if not TOKEN:
        print("❌ DISCORD_TOKEN tidak ditemukan!")
        return
    if not CHANNEL_ID:
        print("❌ CHANNEL_ID tidak ditemukan!")
        return

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"✅ Login sebagai: {client.user}")
        try:
            channel = client.get_channel(CHANNEL_ID)
            if not channel:
                channel = await client.fetch_channel(CHANNEL_ID)
            print(f"📡 Scanning channel: #{channel.name}")

            cdn_links = load_cdn_links()
            existing_urls = {link["url"] for link in cdn_links}
            new_count = 0

            async for message in channel.history(limit=SCAN_LIMIT, oldest_first=False):
                for attachment in message.attachments:
                    if not is_image(attachment.filename):
                        continue
                    if attachment.url in existing_urls:
                        continue
                    link_data = {
                        "url": attachment.url,
                        "filename": attachment.filename,
                        "uploaded_by": str(message.author),
                        "author_id": str(message.author.id),
                        "timestamp": message.created_at.replace(tzinfo=timezone.utc).isoformat(),
                        "message_id": str(message.id),
                        "channel_id": str(CHANNEL_ID),
                        "processed": False,
                        "scanned_at": datetime.now(timezone.utc).isoformat()
                    }
                    cdn_links.append(link_data)
                    existing_urls.add(attachment.url)
                    new_count += 1
                    print(f"   📸 Ditemukan: {attachment.filename} oleh {message.author}")

            save_cdn_links(cdn_links)
            print(f"\n✅ Scan selesai! Gambar baru: {new_count} | Total: {len(cdn_links)}")

        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await client.close()

    await client.start(TOKEN)

if __name__ == "__main__":
    print("=" * 50)
    print("🔍 Discord Gallery - Channel Scanner")
    print("=" * 50)
    asyncio.run(scan_discord())
