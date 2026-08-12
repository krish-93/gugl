import urllib.request
import urllib.error
import re
import ssl
import sys
import time
import os
from datetime import datetime, timezone
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

# ─── CONFIG ────────────────────────────────────────────────────────────
TEMP_M3U_FILE = "template.m3u"
TVTELUGU_URL  = "https://tvtelugu.vercel.app/api/m3u?token=madhu8081"
ZEE5_URL      = "https://cloudplay-app-json.pages.dev/pro-raw-files/zee5.m3u"
GK_URL        = "https://raw.githubusercontent.com/krish-93/gugl/refs/heads/main/lokulu.m3u"
OUTPUT_FILE   = "helloworld.m3u"
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
    # tvtelugu కోసం OTT Navigator User-Agent వాడుతున్నాము
    if "tvtelugu" in url:
        ua = "OTT Navigator IPTV/1.6.7.4 (Linux; Android 11)"
    else:
        ua = "sktechtv"
        
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = resp.read().decode("utf-8", errors="replace")
                if data.strip():
                    print(f"✅ Fetched successfully on attempt {attempt}: {url}")
                    return data
        except Exception as e:
            print(f"⚠️ Attempt {attempt}/{retries} failed for {url}: {e}")
            if attempt < retries:
                time.sleep(RETRY_DELAY)
    return ""

def is_url_line(line):
    s = line.strip()
    return bool(s) and not s.startswith("#") and (s.startswith("http") or s.startswith("rtmp"))

def get_channel_name(extinf_line):
    parts = extinf_line.split(",")
    return parts[-1].strip().lower() if len(parts) > 1 else ""

def get_group_title(extinf_line):
    m = re.search(r'group-title="([^"]+)"', extinf_line, re.IGNORECASE)
    if m:
        return m.group(1).strip().lower()
    return ""

def set_group_title_telugu(extinf_line):
    line = re.sub(r'group-title="[^"]*"', '', extinf_line).strip()
    line = re.sub(r'\s+', ' ', line)
    line = re.sub(r',([^,]*)$', r' group-title="Telugu",\1', line)
    return line

def parse_source_into_blocks(content):
    lines = [l.rstrip() for l in content.splitlines()]
    start_idx = 1 if lines and re.match(r'#\s*EXTM3U', lines[0].strip(), re.IGNORECASE) else 0
    blocks = []
    current_block = []
    for line in lines[start_idx:]:
        stripped = line.strip()
        if not stripped: continue
        current_block.append(stripped)
        if is_url_line(stripped):
            blocks.append(current_block[:])
            current_block = []
    return blocks

def parse_temp_order(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    names = []
    for line in content.splitlines():
        if re.match(r'#\s*EXTINF', line.strip(), re.IGNORECASE):
            name = get_channel_name(line)
            if name:
                names.append(name)
    return names

def decrypt_text(base64_text):
    encrypted_data = base64.b64decode(base64_text.strip())
    cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(IV), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()
    return data.decode('utf-8')

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

    temp_order = parse_temp_order(TEMP_M3U_FILE)
    print(f"📋 Found {len(temp_order)} channels in template.m3u for ordering")

    zee5_content = fetch_url(ZEE5_URL)
    zee_blocks = []
    if zee5_content:
        all_zee_blocks = parse_source_into_blocks(zee5_content)
        for block in all_zee_blocks:
            extinf = next((l for l in block if l.upper().startswith("#EXTINF")), "")
            name = get_channel_name(extinf)
            if "zee telugu hd" in name or "zee cinemalu hd" in name:
                new_block = []
                for line in block:
                    if line.upper().startswith("#EXTINF"):
                        new_block.append(set_group_title_telugu(line))
                    else:
                        new_block.append(line)
                zee_blocks.append(new_block)
        print(f"📡 ZEE5 source: extracted {len(zee_blocks)} specific Zee channels")

    tvtelugu_content = fetch_url(TVTELUGU_URL)
    telugu_blocks = []
    if tvtelugu_content:
        all_tvtelugu_blocks = parse_source_into_blocks(tvtelugu_content)
        for block in all_tvtelugu_blocks:
            extinf = next((l for l in block if l.upper().startswith("#EXTINF")), "")
            group = get_group_title(extinf)
            if "telugu" in group:
                new_block = []
                for line in block:
                    if line.upper().startswith("#EXTINF"):
                        new_block.append(set_group_title_telugu(line))
                    else:
                        new_block.append(line)
                telugu_blocks.append(new_block)
        print(f"📡 tvtelugu source: extracted {len(telugu_blocks)} Telugu channels")

    ordered_telugu_blocks = []
    telugu_dict = {}
    for block in telugu_blocks:
        extinf = next((l for l in block if l.upper().startswith("#EXTINF")), "")
        name = get_channel_name(extinf)
        telugu_dict[name] = block

    for name in temp_order:
        if name in telugu_dict:
            ordered_telugu_blocks.append(telugu_dict.pop(name))
    
    remaining_telugu_blocks = list(telugu_dict.values())
    final_telugu_blocks = ordered_telugu_blocks + remaining_telugu_blocks
    print(f"✅ Ordered {len(ordered_telugu_blocks)} tvtelugu channels matching temp.m3u (appended {len(remaining_telugu_blocks)} extras)")

    gk_content = fetch_url(GK_URL)
    if gk_content:
        try:
            gk_content_dec = decrypt_text(gk_content)
            print("🔓 Successfully decrypted GK source.")
            gk_content = gk_content_dec
        except Exception as e:
            print(f"⚠️ Could not decrypt GK source (might be plaintext): {e}")
    gk_blocks = parse_source_into_blocks(gk_content) if gk_content else []
    print(f"📡 GK source: {len(gk_blocks)} blocks found")

    if not zee_blocks and not final_telugu_blocks and not gk_blocks:
        print("⚠️ All sources failed! Writing keep-alive placeholder.")
        placeholder = f"{OUTPUT_HEADER}\n# Last Attempted: {current_time}\n# ERROR: Sources unavailable. Will retry next run.\n"
        write_encrypted(placeholder)
        sys.exit(0)

    final_text = f"{OUTPUT_HEADER}\n# Last Auto-Updated: {current_time}\n\n"
    
    for block in zee_blocks:
        for line in block:
            final_text += line + "\n"
            
    for block in final_telugu_blocks:
        for line in block:
            final_text += line + "\n"
            
    for block in gk_blocks:
        for line in block:
            final_text += line + "\n"

    write_encrypted(final_text)
    print(f"✅ Successfully generated and encrypted {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
