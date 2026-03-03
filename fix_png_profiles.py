import os
import sys
from PIL import Image

def fix_png_profile(file_path):
    try:
        img = Image.open(file_path)
        # Check if it has an ICC profile
        if 'icc_profile' in img.info:
            # Save it again without the profile
            img.save(file_path, format='PNG', icc_profile=None)
            print(f"Fixed: {file_path}")
        else:
            # print(f"Skipped (no profile): {file_path}")
            pass
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def scan_and_fix(directory):
    print(f"Scanning {directory} for PNGs with bad profiles...")
    count = 0
    for root, dirs, files in os.walk(directory):
        # Skip venv directories to save time and avoid permission errors
        if 'venv' in root or '.git' in root:
            continue

        for file in files:
            if file.lower().endswith('.png'):
                fix_png_profile(os.path.join(root, file))
                count += 1
    print(f"Scanned {count} PNG files.")

if __name__ == "__main__":
    # Fix current directory
    scan_and_fix(".")
    print("Done! The 'libpng warning: iCCP: known incorrect sRGB profile' warnings should be gone.")
