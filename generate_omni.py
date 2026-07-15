import urllib.request
import urllib.error
import re
import ssl
import sys
import time
import os
from datetime import datetime
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

# ─── CONFIG ────────────────────────────────────────────────────────────
TEMPLATE_FILE = "template.m3u"
FRESH_JIO_URL = "https://thanks-to-veer.saqlainhaider8198.workers.dev/jtv90.m3u[srisk]?ua=sktechtv"
GK_URL        = "https://raw.githubusercontent.com/krish-93/gugl/refs/heads/main/lokulu.m3u"
OUTPUT_FILE   = "helloworld.m3u"
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

def is_url_line(line):
    s = line.strip()
    return bool(s) and not s.startswith("#") and (s.startswith("http") or s.startswith("rtmp"))

def get_tvg_id(extinf_line):
    m = re.search(r'tvg-id="([^"]+)"', extinf_line)
    if m and m.group(1).strip():
        return m.group(1).strip()
    parts = extinf_line.split(",")
    return parts[-1].strip() if len(parts) > 1 else None

def parse_source_into_blocks(content):
    lines = [l.rstrip() for l in content.splitlines()]
    start_idx = 1 if lines and re.match(r'#\s*EXTM3U', lines[0].strip(), re.IGNORECASE) else 0
    channels = {}    
    current_block = []
    
    for line in lines[start_idx:]:
        stripped = line.strip()
        if not stripped: continue
        current_block.append(stripped)
        
        if is_url_line(stripped):
            tvg_id = next((get_tvg_id(bl) for bl in current_block if re.match(r'#\s*EXTINF', bl, re.IGNORECASE)), None)
            if tvg_id:
                channels[tvg_id] = current_block[:]
            current_block = []
    return channels

def parse_template_ids(content):
    return [get_tvg_id(line) for line in content.splitlines() if re.match(r'#\s*EXTINF', line.strip(), re.IGNORECASE)]

def parse_gk_blocks(content):
    blocks, current = [], []
    for line in content.splitlines():
        s = line.strip()
        if not s or re.match(r'#\s*EXTM3U', s, re.IGNORECASE): continue
        current.append(s)
        if is_url_line(s):
            if len(current) >= 2: blocks.append(current[:])
            current = []
    return blocks

def main():
    if not os.path.exists(TEMPLATE_FILE):
        sys.exit(1)
    with open(TEMPLATE_FILE, "r", encoding="utf-8", errors="replace") as f:
        tmpl_ids = parse_template_ids(f.read())

    jio_content = fetch_url(FRESH_JIO_URL)
    jio_channels = parse_source_into_blocks(jio_content) if jio_content else {}

    matched = [jio_channels[cid] for cid in tmpl_ids if cid in jio_channels]
    
    gk_content = fetch_url(GK_URL)
    gk_blocks = parse_gk_blocks(gk_content) if gk_content else []

    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Prepare plaintext
    final_text = f"{OUTPUT_HEADER}\n# Last Auto-Updated: {current_time}\n\n"
    for block in matched + gk_blocks:
        for line in block:
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
