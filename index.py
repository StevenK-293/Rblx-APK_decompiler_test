import os
import zipfile
import shutil
import lief
import subprocess
from pathlib import Path
from datetime import datetime

APK_PATH = "roblox_2.682.538-an1.com.apk" # change this if you have another version
OUTPUT_DIR = "roblox_full_extracted"
APKTOOL_PATH = r"C:\Apktool\apktool.bat" # please download this so it ca nwork
LOG_FILE = "apk_analysis_log.txt"

KEYWORDS = ["Teleport", "Position", "Damage", "Health", "Speed", "Player"]

def write_log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def clear_output():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

def run_apktool():
    print("[+] Running apktool to extract resources and smali...")
    subprocess.run([APKTOOL_PATH, "d", APK_PATH, "-f", "-o", OUTPUT_DIR], check=True)
    print("[✓] Apktool extraction complete.")

def unzip_apk():
    zip_dir = os.path.join(OUTPUT_DIR, "raw_zip")
    with zipfile.ZipFile(APK_PATH, 'r') as zip_ref:
        zip_ref.extractall(zip_dir)
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
    for root, _, files in os.walk(lib_dir):
        for file in files:
            if file.endswith(".so"):
                found = True
                so_path = os.path.join(root, file)
                try:
                    binary = lief.parse(so_path)
                    write_log(f"\n[>] Native lib: {file}")
                    write_log(f"    - Arch: {binary.header.machine_type}")
                    write_log(f"    - Entry: 0x{binary.entrypoint:x}")
                    if binary.has_exported_functions:
                        write_log("    - Exported functions:")
                        for func in binary.exported_functions[:20]:
                            write_log(f"        • {func}")
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
    write_log("[+] Scanning assets for keywords...")
    for root, _, files in os.walk(assets_path):
        for file in files:
            try:
                path = os.path.join(root, file)
                with open(path, 'rb', errors='ignore') as f:
                    data = f.read()
                    for word in KEYWORDS:
                        if word.encode() in data:
                            write_log(f"[✓] '{word}' found in asset: {file}")
            except Exception as e:
                write_log(f"[!] Failed to read asset {file}: {e}")

def list_smali_classes():
    smali_path = os.path.join(OUTPUT_DIR, "smali")
    if not os.path.exists(smali_path):
        write_log("[-] No smali folder found.")
        return
    write_log("[+] Scanning smali classes...")
    for root, _, files in os.walk(smali_path):
        for file in files:
            if file.endswith(".smali"):
                class_path = os.path.join(root, file)
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

if __name__ == "__main__":
    main()
