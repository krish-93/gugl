import json
import urllib.request
import urllib.error
import ssl
import sys
import time
from datetime import datetime, timezone
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

# ─── CONFIG ────────────────────────────────────────────────────────────
FRESH_URL     = "https://pllive.bmera5952.workers.dev/"
OUTPUT_FILE   = "gioplus.m3u"
RETRY_COUNT   = 5
RETRY_DELAY   = 10

# AES Keys - Same as your OmniTV keys
SECRET_KEY = b"OmniTVSecureSecretKey_2026_12345"
IV         = b"OmniTV_IV_16_Bys"

OUTPUT_HEADER = '#EXTM3U x-tvg-url="https://avkb.short.gy/epg.xml.gz"'
# ────────────────────────────────────────────────────────────────────────

def make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch_url(url, retries=RETRY_COUNT):
    ctx = make_ssl_ctx()
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    })
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

def main():
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"🕐 Run time: {current_time}")

    content = fetch_url(FRESH_URL)

    if not content:
        # ✅ KEEP-ALIVE FIX: Even on fetch failure, write a timestamped placeholder
        # so the repo always has a new commit keeping workflows alive.
        print("⚠️ Fetch failed! Writing keep-alive placeholder to avoid stale repo.")
        placeholder = f"{OUTPUT_HEADER}\n# Last Attempted: {current_time}\n# ERROR: Source unavailable. Will retry next run.\n"
        padder = padding.PKCS7(128).padder()
        padded = padder.update(placeholder.encode('utf-8')) + padder.finalize()
        cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(IV), backend=default_backend())
        enc = cipher.encryptor()
        encrypted = base64.b64encode(enc.update(padded) + enc.finalize()).decode('utf-8')
        with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(encrypted)
        sys.exit(0)  # Exit 0 so the workflow commits the placeholder!

    # 🔹 NEW LOGIC: Parse the JSON from the new API
    channels = []
    if '[' in content:
        json_str = content[content.find('['):]
        channels = json.loads(json_str)
        print(f"✅ Successfully parsed {len(channels)} channels from JSON!")

    # ✅ KEEP-ALIVE FIX: Timestamp embedded in plaintext so encrypted
    # output is ALWAYS different → git always has something to commit.
    final_text = f"{OUTPUT_HEADER}\n# Last Auto-Updated: {current_time}\n\n"
    
    valid_count = 0
    for ch in channels:
        name = ch.get('name', 'Unknown')
        c_id = ch.get('id', '')
        logo = ch.get('logo', '')
        group = ch.get('group', 'Uncategorized')
        mpd_url = ch.get('mpd_url', '')
        license_url = ch.get('license_url', '')
        ua = ch.get('user_agent', 'Mozilla/5.0')
        
        headers = ch.get('headers', {})
        cookie = headers.get('cookie', '')
        
        if not mpd_url:
            continue
            
        final_url = f"{mpd_url}?{cookie}" if cookie else mpd_url
        
        m3u_entry = f'#EXTINF:-1 tvg-id="{c_id}" tvg-logo="{logo}" group-title="{group}",{name}\n'
        
        if license_url:
            m3u_entry += f'#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
            m3u_entry += f'#KODIPROP:inputstream.adaptive.license_key={license_url}\n'
            
        m3u_entry += f'{final_url}|User-Agent={ua}\n'
        
        final_text += m3u_entry
        valid_count += 1
        
    print(f"📋 Total channels processed: {valid_count}")

    # 🔥 AES ENCRYPTION 🔥
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(final_text.encode('utf-8')) + padder.finalize()
    cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(IV), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    base64_encrypted = base64.b64encode(encrypted_data).decode('utf-8')

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(base64_encrypted)
    print(f"✅ Successfully generated and encrypted {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
