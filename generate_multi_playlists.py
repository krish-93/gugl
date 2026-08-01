import urllib.request
import urllib.error
import ssl
import sys
import time
import os
import re
from datetime import datetime, timezone
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

# ─── CONFIG ────────────────────────────────────────────────────────────
PLAYLISTS = [
    {
        "url": "https://thanks-to-veer.saqlainhaider8198.workers.dev/jstar.m3u[jtvf]?ua=sktechtv",
        "category": "JIO HOTSTAR"
    },
       {
        "url": "https://jhsevetns-fhd.rtxcric.workers.dev/playlist.m3u",
        "category": "JIO HOTSTAR - EVENTS"
    },
    {
        "url": "https://vortextv.modsdone.com/sony.txt",
        "category": "SONYLiv"
    },
   {
        "url": "https://nonyliv.saqlainhaider8198.workers.dev/nony2.m3u",
        "category": "SONYLIV - EVENTS"
    }
]

OUTPUT_FILE = "mixed_live.m3u"
RETRY_COUNT = 3
RETRY_DELAY = 5

# AES Keys
SECRET_KEY = b"OmniTVSecureSecretKey_2026_12345"
IV         = b"OmniTV_IV_16_Bys"

OUTPUT_HEADER = '#EXTM3U x-tvg-url="https://raw.githubusercontent.com/mitthu786/tvepg/main/tataplay/epg.xml" x-tvg-url="https://avkb.short.gy/epg.xml.gz"'
# ────────────────────────────────────────────────────────────────────────

def make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch_url(url, retries=RETRY_COUNT):
    print(f"Fetching: {url}")
    ctx = make_ssl_ctx()
    req = urllib.request.Request(url, headers={"User-Agent": "sktechtv", "Accept": "*/*"})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = resp.read().decode("utf-8", errors="replace")
                if data.strip():
                    print(f"✅ Fetched successfully on attempt {attempt}")
                    return data
        except Exception as e:
            print(f"⚠️ Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(RETRY_DELAY)
    return ""

def process_playlist(raw_content, category):
    lines = raw_content.splitlines()
    clean_lines = []
    for line in lines:
        s = line.strip()
        if not s: continue
        if s.upper().startswith("#EXTM3U"): continue
        if s.upper().startswith("##"): continue
        
        # If it's an EXTINF line, overwrite or inject group-title
        if s.upper().startswith("#EXTINF"):
            if 'group-title="' in s:
                s = re.sub(r'group-title="[^"]*"', f'group-title="{category}"', s)
            else:
                # Insert before the last comma
                s = re.sub(r',([^,]*)$', f' group-title="{category}",\\1', s)
        
        clean_lines.append(s)
    return clean_lines

def write_encrypted(text):
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(text.encode('utf-8')) + padder.finalize()
    cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(IV), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    base64_encrypted = base64.b64encode(encrypted_data).decode('utf-8')
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(base64_encrypted)

def main():
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"🕐 Run time: {current_time}")

    final_text = f"{OUTPUT_HEADER}\n# Last Auto-Updated: {current_time}\n\n"

    for pl in PLAYLISTS:
        raw_content = fetch_url(pl["url"])
        if raw_content:
            processed_lines = process_playlist(raw_content, pl["category"])
            for line in processed_lines:
                final_text += line + "\n"
        else:
            print(f"⚠️ Failed to fetch {pl['category']}, skipping.")

    # 🔥 AES ENCRYPTION 🔥
    write_encrypted(final_text)
    print(f"✅ Successfully extracted, modified categories, encrypted and saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
