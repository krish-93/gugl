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
WISPY_URL     = "https://m3u.cloudplay.qzz.io/prm-m3u/mbjtv-pro.m3u"
OUTPUT_FILE   = "gioplus.m3u"
RETRY_COUNT   = 5
RETRY_DELAY   = 10

# AES Keys - Same as your OmniTV keys
SECRET_KEY = b"OmniTVSecureSecretKey_2026_12345"
IV         = b"OmniTV_IV_16_Bys"

OUTPUT_HEADER = '#EXTM3U x-tvg-url="https://raw.githubusercontent.com/mitthu786/tvepg/main/tataplay/epg.xml" x-tvg-url="https://avkb.short.gy/epg.xml.gz"'
# ────────────────────────────────────────────────────────────────────────

def make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def write_encrypted(text):
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(text.encode('utf-8')) + padder.finalize()
    cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(IV), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    base64_encrypted = base64.b64encode(encrypted_data).decode('utf-8')
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(base64_encrypted)

def fetch_url(url, retries=RETRY_COUNT):
    ctx = make_ssl_ctx()
    req = urllib.request.Request(url, headers={
        "User-Agent": "OTT Navigator",
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

    content = fetch_url(WISPY_URL)

    if not content:
        print("⚠️ Fetch failed! Writing keep-alive placeholder to avoid stale repo.")
        placeholder = f"{OUTPUT_HEADER}\n# Last Attempted: {current_time}\n# ERROR: Source unavailable. Will retry next run.\n"
        write_encrypted(placeholder)
        sys.exit(0)

    # 1. వస్తున్నది డైరెక్ట్ M3U ఫైల్ కాబట్టి దాన్ని JSON లోడ్ చేయకూడదు
    # 2. ఫైల్ లో ఉన్న ఒరిజినల్ #EXTM3U ని తీసేసి మన కస్టమ్ OUTPUT_HEADER ని పెడుతున్నాం
    
    if content.startswith("#EXTM3U"):
        content = content.replace("#EXTM3U", "", 1)
        
    final_text = f"{OUTPUT_HEADER}\n# Last Auto-Updated: {current_time}\n{content}"
    
    # 🔥 AES ENCRYPTION 🔥
    write_encrypted(final_text)
    print(f"✅ Successfully generated and encrypted {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
