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
WISPY_URL     = "https://gojojtv.gojosare123.workers.dev/"
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
    # ఇక్కడ OTT Navigator User-Agent యాడ్ చేశాం
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

    # కొత్త URL డైరెక్ట్ గా M3U ఇస్తుంది, JSON కాదు. కాబట్టి JSON పార్సింగ్ తీసేశాను.
    lines = content.splitlines()
    final_text = f"{OUTPUT_HEADER}\n# Last Auto-Updated: {current_time}\n\n"
    
    valid_count = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # పాత #EXTM3U ని స్కిప్ చేస్తున్నాం ఎందుకంటే మనం ఆల్రెడీ పైన EPG తో మన ఓన్ హెడర్ పెట్టుకున్నాం
        if line.startswith("#EXTM3U"):
            continue
            
        # ఇది ఛానెల్ ప్లేబ్యాక్ URL లైన్ అయితే...
        if line.startswith("http"):
            # మన ప్లేయర్ కూడా అదే User-Agent తో ప్లే చేయడానికి యాడ్ చేస్తున్నాం
            if "|User-Agent=" not in line:
                line = f"{line}|User-Agent=OTT Navigator"
            valid_count += 1
            
        final_text += line + "\n"

    print(f"📋 Total channels processed: {valid_count}")

    # 🔥 AES ENCRYPTION 🔥
    write_encrypted(final_text)
    print(f"✅ Successfully generated and encrypted {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
