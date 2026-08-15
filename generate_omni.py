import urllib.request
import urllib.error
import re
import ssl
import sys
import time
import os
import unicodedata
from datetime import datetime, timezone
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

# ─── CONFIG ────────────────────────────────────────────────────────────
TEMP_M3U_FILE = "template.m3u"
CLOUDPLAY_URL = "https://m3u.cloudplay.qzz.io/prm-m3u/pllive-prm.m3u"
TVTELUGU_URL  = "https://tvtelugu.vercel.app/api/m3u?token=madhu8081"
GK_URL        = "https://raw.githubusercontent.com/krish-93/gugl/refs/heads/main/lokulu.m3u"
OUTPUT_FILE   = "helloworld.m3u"
RETRY_COUNT   = 5
RETRY_DELAY   = 10

# AES Keys
SECRET_KEY = b"OmniTVSecureSecretKey_2026_12345"
IV         = b"OmniTV_IV_16_Bys"

OUTPUT_HEADER = '#EXTM3U x-tvg-url="https://egp.ayush848694.workers.dev/"'
# ────────────────────────────────────────────────────────────────────────

def make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch_url(url, retries=RETRY_COUNT):
    ctx = make_ssl_ctx()
    # tvtelugu requires specific user-agent
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

def is_any_url(line):
    s = line.strip()
    if s.startswith("http") or s.startswith("rtmp"): return True
    if s.startswith("#http") or s.startswith("#rtmp"): return True
    if s.startswith("# backup: http"): return True
    return False

def parse_source_into_blocks(content):
    lines = [l.rstrip() for l in content.splitlines()]
    blocks = []
    
    url_indices = [i for i, line in enumerate(lines) if is_any_url(line)]
    
    last_claimed_idx = -1
    for idx in url_indices:
        url_line = lines[idx].strip()
        
        if url_line.startswith("# backup: "):
            url_line = url_line.replace("# backup: ", "", 1)
        elif url_line.startswith("#http") or url_line.startswith("#rtmp"):
            url_line = url_line[1:]
            
        ua_line = None
        if "|" in url_line:
            parts = url_line.split("|")
            url_line = parts[0]
            for param in parts[1:]:
                if param.startswith("User-Agent="):
                    ua = param.split("=", 1)[1]
                    ua_line = f"#EXTVLCOPT:http-user-agent={ua}"
            
        block_lines = [url_line]
        if ua_line:
            block_lines.insert(0, ua_line)
            
        extinf_found = False
        
        for j in range(idx - 1, last_claimed_idx, -1):
            line = lines[j]
            if not line.strip(): continue
            if line.upper().startswith("#EXTM3U"): continue
            
            if line.upper().startswith("#EXTINF"):
                if extinf_found:
                    break
                extinf_found = True
            
            block_lines.insert(0, line)
            
        if extinf_found:
            blocks.append(block_lines)
        last_claimed_idx = idx
        
    return blocks

def normalize_text(text):
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').lower()

def get_channel_name(extinf_line):
    parts = extinf_line.split(",")
    return parts[-1].strip() if len(parts) > 1 else ""

def get_group_title(extinf_line):
    m = re.search(r'group-title="([^"]+)"', extinf_line, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""

def set_group_title_telugu(extinf_line):
    line = re.sub(r'group-title="[^"]*"', '', extinf_line).strip()
    line = re.sub(r'\s+', ' ', line)
    line = re.sub(r',([^,]*)$', r' group-title="Telugu",\1', line)
    return line

def parse_temp_order(file_path):
    if not os.path.exists(file_path):
        print(f"⚠️ Template file not found: {file_path}")
        return []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    names = []
    for line in content.splitlines():
        if re.match(r'#\s*EXTINF', line.strip(), re.IGNORECASE):
            name = get_channel_name(line)
            if name:
                names.append(normalize_text(name))
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

    # 1. Read Order from template
    temp_order = parse_temp_order(TEMP_M3U_FILE)
    print(f"📋 Found {len(temp_order)} channels in {TEMP_M3U_FILE} for ordering")

    telugu_dict = {}

    # 2. Extract Channels from CloudPlay (Primary Source)
    cloudplay_content = fetch_url(CLOUDPLAY_URL)
    if cloudplay_content:
        cloudplay_blocks = parse_source_into_blocks(cloudplay_content)
        for block in cloudplay_blocks:
            extinf = next((l for l in block if l.upper().startswith("#EXTINF")), "")
            name = normalize_text(get_channel_name(extinf))
            group = normalize_text(get_group_title(extinf))
            
            # Keep if it's in our template OR if it's a Telugu channel
            if name in temp_order or "telugu" in group:
                new_block = []
                for line in block:
                    if line.upper().startswith("#EXTINF"):
                        new_block.append(set_group_title_telugu(line))
                    else:
                        new_block.append(line)
                telugu_dict[name] = new_block
        print(f"📡 CloudPlay source: extracted {len(telugu_dict)} Telugu/Template channels")

    # 3. Extract ETV Permanent Channels from TVTELUGU (Overrides CloudPlay)
    tvtelugu_content = fetch_url(TVTELUGU_URL)
    permanent_etv = ["etv comedy", "etv music", "etv josh", "etv news"]
    etv_count = 0
    if tvtelugu_content:
        tvtelugu_blocks = parse_source_into_blocks(tvtelugu_content)
        for block in tvtelugu_blocks:
            extinf = next((l for l in block if l.upper().startswith("#EXTINF")), "")
            name = normalize_text(get_channel_name(extinf))
            
            if any(p in name for p in permanent_etv):
                new_block = []
                for line in block:
                    if line.upper().startswith("#EXTINF"):
                        new_block.append(set_group_title_telugu(line))
                    else:
                        new_block.append(line)
                telugu_dict[name] = new_block
                etv_count += 1
        print(f"📡 TVTelugu source: preserved {etv_count} permanent ETV channels")

    # 4. Order Channels according to template
    ordered_telugu_blocks = []
    
    for name in temp_order:
        if name in telugu_dict:
            ordered_telugu_blocks.append(telugu_dict.pop(name))
    
    # Remaining channels that were in Telugu groups but not in template
    remaining_telugu_blocks = list(telugu_dict.values())
    
    final_telugu_blocks = ordered_telugu_blocks + remaining_telugu_blocks
    print(f"✅ Final Telugu list: {len(ordered_telugu_blocks)} Ordered + {len(remaining_telugu_blocks)} Remaining = {len(final_telugu_blocks)} Total")

    # 5. Extract & Decrypt GK (లోకులు) సోర్స్
    gk_content = fetch_url(GK_URL)
    if gk_content:
        try:
            gk_content_dec = decrypt_text(gk_content)
            print("🔓 Successfully decrypted GK source.")
            gk_content = gk_content_dec
        except Exception as e:
            print(f"⚠️ Could not decrypt GK source: {e}")
    gk_blocks = parse_source_into_blocks(gk_content) if gk_content else []
    print(f"📡 GK source: {len(gk_blocks)} blocks found")

    if not final_telugu_blocks and not gk_blocks:
        print("⚠️ All sources failed! Writing keep-alive placeholder.")
        placeholder = f"{OUTPUT_HEADER}\n# Last Attempted: {current_time}\n# ERROR: Sources unavailable. Will retry next run.\n"
        write_encrypted(placeholder)
        sys.exit(0)

    # 6. Merge and Encrypt (ఫైనల్ ఫైల్ రైటింగ్)
    final_text = f"{OUTPUT_HEADER}\n# Last Auto-Updated: {current_time}\n\n"
    
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
