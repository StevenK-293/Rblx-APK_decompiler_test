import os
import zipfile
import shutil
import lief
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

APK_PATH = "roblox_2.682.538-an1.com.apk" # change this if you have another version
OUTPUT_DIR = "roblox_full_extracted"
APKTOOL_PATH = r"C:\Apktool\apktool.bat" # please download this so it ca nwork
LOG_FILE = "apk_analysis_log.txt"
OFFSET_FILE = "native_offsets.txt" # w.i.p

KEYWORDS = ["Teleport", "Position", "Damage", "Health", "Speed", "Player"]

spinner_running = False

def spinner(msg):
    global spinner_running
    spinner_running = True
    chars = "|/-\\"
    i = 0
    while spinner_running:
        print(f"\r{msg} {chars[i % len(chars)]}", end="", flush=True)
        i += 1
        time.sleep(0.1)
    print("\r" + " " * (len(msg) + 2) + "\r", end="")

def start_spinner(msg):
    t = threading.Thread(target=spinner, args=(msg,))
    t.start()
    return t

def stop_spinner(thread):
    global spinner_running
    spinner_running = False
    thread.join()

def write_log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def write_offset(text):
    with open(OFFSET_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def clear_output():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for f in [LOG_FILE, OFFSET_FILE]:
        if os.path.exists(f):
            os.remove(f)

def run_apktool():
    t = start_spinner("Running apktool to extract resources and smali")
    subprocess.run([APKTOOL_PATH, "d", APK_PATH, "-f", "-o", OUTPUT_DIR], check=True)
    stop_spinner(t)
    print("[✓] Apktool extraction complete.")

def unzip_apk():
    zip_dir = os.path.join(OUTPUT_DIR, "raw_zip")
    zip_path = APK_PATH
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        members = zip_ref.namelist()
        for file in tqdm(members, desc="Unzipping APK", ncols=75):
            zip_ref.extract(file, zip_dir)
    print("[✓] APK unzipped into raw_zip.")

def extract_manifest():
    manifest_path = os.path.join(OUTPUT_DIR, "AndroidManifest.xml")
    if os.path.exists(manifest_path):
        write_log(f"[✓] Manifest found: {manifest_path}")
    else:
        write_log("[x] AndroidManifest.xml not found!")

def extract_native_libs():
    lib_dir = os.path.join(OUTPUT_DIR, "raw_zip", "lib")
    found = False
    lib_files = []
    for root, _, files in os.walk(lib_dir):
        for file in files:
            if file.endswith(".so"):
                lib_files.append(os.path.join(root, file))

    for so_path in tqdm(lib_files, desc="Parsing native libs", ncols=75):
        file = os.path.basename(so_path)
        found = True
        try:
            binary = lief.parse(so_path)
            write_log(f"\n[>] Native lib: {file}")
            write_log(f"    - Arch: {binary.header.machine_type}")
            write_log(f"    - Entry: 0x{binary.entrypoint:x}")
            write_offset(f"{file}: entrypoint = 0x{binary.entrypoint:x}")
            if binary.has_exported_functions:
                write_log("    - Exported functions:")
                for func in binary.exported_functions[:20]:
                    write_log(f"        • {func}")
                    write_offset(f"{file}: {func}")
            else:
                write_log("    - No exports.")
        except Exception as e:
            write_log(f"[!] Failed to parse {file}: {e}")
    if not found:
        write_log("[-] No .so libs found in /lib/.")

def extract_keywords_from_assets():
    assets_path = os.path.join(OUTPUT_DIR, "raw_zip", "assets")
    if not os.path.exists(assets_path):
        write_log("[-] No assets directory found.")
        return
    all_assets = []
    for root, _, files in os.walk(assets_path):
        for file in files:
            all_assets.append(os.path.join(root, file))

    for path in tqdm(all_assets, desc="Scanning assets", ncols=75):
        file = os.path.basename(path)
        try:
            with open(path, 'rb') as f:
                data = f.read()
            try:
                decoded = data.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    decoded = data.decode("utf-16")
                except:
                    decoded = None
            if decoded:
                with open(path + ".txt", "w", encoding="utf-8") as out:
                    out.write(decoded)
                for word in KEYWORDS:
                    if word in decoded:
                        write_log(f"[✓] '{word}' found in asset: {file}")
        except Exception as e:
            write_log(f"[!] Failed to read asset {file}: {e}")

def list_smali_classes():
    smali_path = os.path.join(OUTPUT_DIR, "smali")
    if not os.path.exists(smali_path):
        write_log("[-] No smali folder found.")
        return
    smali_files = []
    for root, _, files in os.walk(smali_path):
        for file in files:
            if file.endswith(".smali"):
                smali_files.append(os.path.join(root, file))

    for class_path in tqdm(smali_files, desc="Scanning smali", ncols=75):
        try:
            with open(class_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.read()
                for word in KEYWORDS:
                    if word in lines:
                        write_log(f"[✓] '{word}' in smali: {class_path}")
                        break
        except:
            pass

def main():
    print("=== Roblox APK Deep Extractor ===")
    clear_output()
    write_log(f"=== Analysis started: {datetime.now()} ===")
    run_apktool()
    unzip_apk()
    extract_manifest()
    extract_native_libs()
    extract_keywords_from_assets()
    list_smali_classes()
    write_log(f"=== Analysis complete: {datetime.now()} ===")
    print(f"\n[✓] Log saved to {LOG_FILE}")
    print(f"[✓] Offset info saved to {OFFSET_FILE}")

if __name__ == "__main__":
    main()
