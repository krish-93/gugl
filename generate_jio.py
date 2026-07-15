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
FRESH_JIO_URL = "https://thanks-to-veer.saqlainhaider8198.workers.dev/jtv90.m3u[srisk]?ua=sktechtv"
OUTPUT_FILE   = "gio.m3u"
RETRY_COUNT   = 3
RETRY_DELAY   = 5

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
    ctx = make_ssl_ctx()
    req = urllib.request.Request(url, headers={"User-Agent": "sktechtv", "Accept": "*/*"})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except:
            time.sleep(RETRY_DELAY)
    return ""

def main():
    jio_content = fetch_url(FRESH_JIO_URL)
    if not jio_content:
        sys.exit(1)
        
    jio_lines = [line.strip() for line in jio_content.splitlines() if line.strip() and not line.strip().upper().startswith("#EXTM3U")]
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    # Prepare plaintext
    final_text = f"{OUTPUT_HEADER}\n# Last Auto-Updated: {current_time}\n\n"
    for line in jio_lines:
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

if __name__ == "__main__":
    main()
