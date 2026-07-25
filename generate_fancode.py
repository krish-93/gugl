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
SOURCE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphx8/refs/heads/main/data/fancode.m3u"
OUTPUT_FILE = "fcliv.m3u"
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

    raw_content = fetch_url(SOURCE_URL)
    
    if not raw_content:
        print("⚠️ Source failed! Writing keep-alive placeholder.")
        placeholder = f"{OUTPUT_HEADER}\n# Last Attempted: {current_time}\n# ERROR: Source unavailable. Will retry next run.\n"
        write_encrypted(placeholder)
        sys.exit(0)

    # Clean the content (remove existing EXTM3U and empty lines)
    lines = raw_content.splitlines()
    clean_lines = []
    for line in lines:
        s = line.strip()
        if not s: continue
        if s.upper().startswith("#EXTM3U"): continue
        clean_lines.append(s)
        
    final_text = f"{OUTPUT_HEADER}\n# Last Auto-Updated: {current_time}\n\n"
    for line in clean_lines:
        final_text += line + "\n"

    # 🔥 AES ENCRYPTION 🔥
    write_encrypted(final_text)
    print(f"✅ Successfully extracted, encrypted and saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
