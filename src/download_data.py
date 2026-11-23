import ssl
import sys
import urllib.request
from pathlib import Path

import certifi

SHEET_ID = "1mD4Hn4NZdJlXMC4EJcSp27vg-_jbxUYJ95vQvMbSpVM"
EXPORT_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
)
ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "raw" / "northwind.xlsx"


def download(url, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Use certifi's CA bundle; python.org builds on macOS ship without one.
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(url, timeout=60, context=context) as resp:
        content = resp.read()
    # A private or moved sheet returns an HTML sign-in page, not a workbook.
    if not content.startswith(b"PK"):
        raise RuntimeError(
            "Download did not return an .xlsx file. Check that the sheet "
            "is shared as 'Anyone with the link can view'."
        )
    out_path.write_bytes(content)
    return out_path


def main():
    force = "--force" in sys.argv
    if OUT_PATH.exists() and not force:
        print(f"Using existing {OUT_PATH.relative_to(ROOT)} "
              "(pass --force to re-download).")
        return
    path = download(EXPORT_URL, OUT_PATH)
    print(f"Saved {path.relative_to(ROOT)} "
          f"({path.stat().st_size / 1024:.0f} KB).")


if __name__ == "__main__":
    main()
