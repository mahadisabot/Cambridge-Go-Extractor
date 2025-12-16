import zipfile
import sys

try:
    with zipfile.ZipFile(sys.argv[1], 'r') as z:
        print("Valid ZIP file.")
        print("Contents start:")
        for name in z.namelist()[:5]:
            print(f" - {name}")
except Exception as e:
    print(f"Invalid ZIP: {e}")
