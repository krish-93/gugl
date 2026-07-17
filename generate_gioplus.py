import urllib.request
import urllib.error
import ssl
import sys
import time
import json
from datetime import datetime
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
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

def encrypt_and_save(text):
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(text.encode('utf-8')) + padder.finalize()
    cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(IV), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    base64_encrypted = base64.b64encode(encrypted_data).decode('utf-8')

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(base64_encrypted)
    print(f"✅ Successfully generated and encrypted {OUTPUT_FILE}")

def main():
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"🕐 Run time: {current_time}")

    content = fetch_url(FRESH_URL)

    if not content:
        print("⚠️ Fetch failed! Writing keep-alive placeholder to avoid stale repo.")
        placeholder = f"{OUTPUT_HEADER}\n# Last Attempted: {current_time}\n# ERROR: Source unavailable. Will retry next run.\n"
        encrypt_and_save(placeholder)
        sys.exit(0)

    # JSON డేటాని చదవడం
    try:
        channels = json.loads(content)
    except json.JSONDecodeError:
        print("⚠️ Error: Source returned invalid JSON data!")
        sys.exit(1)

    print(f"📋 Total channels fetched: {len(channels)}")

    # M3U ఫార్మాట్‌ని క్రియేట్ చేయడం
    m3u_lines = [OUTPUT_HEADER, f"# Last Auto-Updated: {current_time}\n"]
    
    for ch in channels:
        name = ch.get("name", "Unknown Channel")
        group = ch.get("group", "")
        logo = ch.get("logo", "")
        mpd_url = ch.get("mpd_url", "")
        license_url = ch.get("license_url", "")
        headers = ch.get("headers", {})
        user_agent = ch.get("user_agent", "")

        # చానెల్ ఇన్ఫో
        extinf = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group}",{name}'
        m3u_lines.append(extinf)

        # DRM & License కీ ఉంటే యాడ్ చేయడం
        if license_url:
            m3u_lines.append('#KODIPROP:inputstream=inputstream.adaptive')
            m3u_lines.append('#KODIPROP:inputstream.adaptive.manifest_type=mpd')
            m3u_lines.append(f'#KODIPROP:inputstream.adaptive.license_key={license_url}')
        
        # User Agent ఉంటే యాడ్ చేయడం
        if user_agent:
            m3u_lines.append(f'#EXTVLCOPT:http-user-agent={user_agent}')

        # కుకీస్ లేదా హెడర్స్ ఉంటే వీడియో లింక్‌కి జత చేయడం
        header_str = ""
        if headers:
            parts = []
            for k, v in headers.items():
                parts.append(f'{k}={v}')
            if user_agent:
                parts.append(f'User-Agent={user_agent}')
            header_str = "|" + "&".join(parts)

        # ఫైనల్ వీడియో లింక్
        m3u_lines.append(f"{mpd_url}{header_str}\n")

    final_text = "\n".join(m3u_lines)
    
    # ఎన్‌క్రిప్ట్ చేసి సేవ్ చేయడం
    encrypt_and_save(final_text)

if __name__ == "__main__":
    main()
