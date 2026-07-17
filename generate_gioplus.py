import urllib.request
import urllib.error
import ssl
import sys
import time
from datetime import datetime
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

# ─── CONFIG ────────────────────────────────────────────────────────────
FRESH_URL     = "https://noisy-truth-6766.streamstar18.workers.dev/"
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
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
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

    lines = [
        line.strip() for line in content.splitlines()
        if line.strip() and not line.strip().upper().startswith("#EXTM3U")
    ]
    print(f"📋 Total lines fetched: {len(lines)}")

    # ✅ KEEP-ALIVE FIX: Timestamp embedded in plaintext so encrypted
    # output is ALWAYS different → git always has something to commit.
    final_text = f"{OUTPUT_HEADER}\n# Last Auto-Updated: {current_time}\n\n"
    for line in lines:
        final_text += line + "\n"

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
