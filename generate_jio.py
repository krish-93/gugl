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
FRESH_JIO_URL = "https://m3u.cloudplay.qzz.io/prm-m3u/pllive-prm.m3u"
OUTPUT_FILE   = "gio.m3u"
RETRY_COUNT   = 5
RETRY_DELAY   = 10

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

    jio_content = fetch_url(FRESH_JIO_URL)

    if not jio_content:
        # ✅ KEEP-ALIVE FIX
        print("⚠️ Fetch failed! Writing keep-alive placeholder to avoid stale repo.")
        placeholder = f"{OUTPUT_HEADER}\n# Last Attempted: {current_time}\n# ERROR: Source unavailable. Will retry next run.\n"
        padder = padding.PKCS7(128).padder()
        padded = padder.update(placeholder.encode('utf-8')) + padder.finalize()
        cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(IV), backend=default_backend())
        enc = cipher.encryptor()
        encrypted = base64.b64encode(enc.update(padded) + enc.finalize()).decode('utf-8')
        with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(encrypted)
        sys.exit(0)

    jio_lines = []
    skip_current_channel = False
    
    # లైన్ బై లైన్ చెక్ చేస్తున్నాం
    for line in jio_content.splitlines():
        line_s = line.strip()
        if not line_s or line_s.upper().startswith("#EXTM3U"):
            continue
            
        # ఒకవేళ ఇది కొత్త ఛానల్ అయితే, అది మనం స్కిప్ చేయాల్సిన ఛానల్ కాదా అని చెక్ చేస్తాం
        if line_s.upper().startswith("#EXTINF"):
            if "CloudPlay" in line_s and "Jtv|General" in line_s:
                skip_current_channel = True
                print("🚫 Skipped channel: CloudPlay (Jtv|General)")
            else:
                skip_current_channel = False
                
        # స్కిప్ చేయాల్సిన ఛానల్ బ్లాక్ లో ఉంటే ఈ లైన్ ని వదిలేస్తాం (URL తో సహా)
        if skip_current_channel:
            continue
            
        jio_lines.append(line_s)

    print(f"📋 Total lines after filtering: {len(jio_lines)}")

    # ఫైనల్ టెక్స్ట్ కి మన హెడర్ యాడ్ చేసి కలుపుతున్నాం
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

    print(f"✅ Successfully generated and encrypted {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
