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
WISPY_URL     = "https://wispy-wave-3131.diwij76343.workers.dev/"
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

def write_encrypted(text):
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(text.encode('utf-8')) + padder.finalize()
    cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(IV), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    base64_encrypted = base64.b64encode(encrypted_data).decode('utf-8')
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(base64_encrypted)

def hex_to_base64url(hex_str):
    """Converts a hex string to a base64url string without padding."""
    if not hex_str or hex_str.lower() == "null":
        return None
    try:
        bytes_data = bytes.fromhex(hex_str)
        b64 = base64.urlsafe_b64encode(bytes_data).decode('utf-8')
        return b64.rstrip('=')
    except:
        return None

def fetch_url(url, retries=RETRY_COUNT):
    ctx = make_ssl_ctx()
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
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

def main():
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"🕐 Run time: {current_time}")

    content = fetch_url(WISPY_URL)

    if not content:
        print("⚠️ Fetch failed! Writing keep-alive placeholder to avoid stale repo.")
        placeholder = f"{OUTPUT_HEADER}\n# Last Attempted: {current_time}\n# ERROR: Source unavailable. Will retry next run.\n"
        write_encrypted(placeholder)
        sys.exit(0)

    # Parse JSON
    channels = []
    try:
        channels = json.loads(content)
        print(f"✅ Successfully parsed {len(channels)} channels from JSON!")
    except Exception as e:
        print(f"⚠️ JSON parsing error: {e}")
        sys.exit(1)

    final_text = f"{OUTPUT_HEADER}\n# Last Auto-Updated: {current_time}\n\n"
    
    valid_count = 0
    for ch in channels:
        name = ch.get('name', 'Unknown')
        c_id = ch.get('id', '')
        logo = ch.get('logo', '')
        group = ch.get('category', 'Uncategorized')
        mpd_url = ch.get('url', '')
        cookie = ch.get('cookie', '')
        keyId_hex = ch.get('keyId', '')
        key_hex = ch.get('key', '')
        
        if not mpd_url:
            continue
            
        m3u_entry = f'#EXTINF:-1 tvg-id="{c_id}" tvg-logo="{logo}" group-title="{group}",{name}\n'
        
        if keyId_hex and key_hex:
            clearkey_pair = f'{keyId_hex}:{key_hex}'
            m3u_entry += f'#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
            m3u_entry += f'#KODIPROP:inputstream.adaptive.license_key={clearkey_pair}\n'
            
        # Common OTT user agent and cookie header
        m3u_entry += f'{mpd_url}|User-Agent=Mozilla/5.0'
        if cookie:
            m3u_entry += f'&Cookie={cookie}'
        m3u_entry += '\n'
        
        final_text += m3u_entry
        valid_count += 1
        
    print(f"📋 Total channels processed: {valid_count}")

    # 🔥 AES ENCRYPTION 🔥
    write_encrypted(final_text)
    print(f"✅ Successfully generated and encrypted {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
