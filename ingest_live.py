"""
Batch ingest PDFs to the live Render backend.
Excludes any OCR-related files. Tracks progress to avoid re-uploads.
"""

import os
import sys
import re
import requests
import time

RENDER_URL = "https://syllabus-ai-rwlh.onrender.com"
UPLOAD_ENDPOINT = f"{RENDER_URL}/api/documents/upload"
DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "documents")

SUBJECT_MAP = {"COA": "COA", "APJ": "APJ", "DAA": "DAA", "OB": "OB", "DM": "DM"}

def extract_unit_number(filename):
    patterns = [r'UNIT[\s_-]*(\d+)', r'[Uu]nit[\s_-]*(\d+)', r'UT(\d+)']
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 5:
                return num
    return 1

def is_ocr_file(filename):
    lower = filename.lower()
    return 'ocr' in lower or 'handwritten' in lower or 'scan' in lower

def collect_files():
    """Collect all PDF files to ingest."""
    files_to_ingest = []
    for subject_folder, subject_code in SUBJECT_MAP.items():
        subject_path = os.path.join(DOCS_DIR, subject_folder)
        if not os.path.exists(subject_path):
            continue
        for root, dirs, files in os.walk(subject_path):
            for filename in files:
                if not filename.lower().endswith('.pdf'):
                    continue
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(root, subject_path)
                section = rel_path if rel_path in ("A", "B", "C") else None
                unit_number = extract_unit_number(filename)
                files_to_ingest.append({
                    "filepath": filepath,
                    "filename": filename,
                    "subject_code": subject_code,
                    "section": section,
                    "unit_number": unit_number,
                    "is_ocr": is_ocr_file(filename),
                })
    return files_to_ingest

def main():
    print(f"\n{'='*60}")
    print(f"  Batch PDF Ingestion to Live Backend")
    print(f"  Server: {RENDER_URL}")
    print(f"  Docs: {DOCS_DIR}")
    print(f"{'='*60}\n")

    if not os.path.exists(DOCS_DIR):
        print(f"ERROR: Docs dir not found: {DOCS_DIR}")
        sys.exit(1)

    # Collect all files
    all_files = collect_files()
    pdf_files = [f for f in all_files if not f["is_ocr"]]
    ocr_files = [f for f in all_files if f["is_ocr"]]

    print(f"Found {len(all_files)} total PDFs")
    print(f"  - {len(pdf_files)} to ingest")
    print(f"  - {len(ocr_files)} OCR files to skip")
    print()

    if ocr_files:
        for f in ocr_files:
            print(f"  SKIP (OCR): {f['subject_code']}/{f['filename']}")
        print()

    # Wake up server
    print("Waking up Render server...")
    try:
        resp = requests.get(f"{RENDER_URL}/", timeout=120)
        print(f"Server awake! Status: {resp.status_code}\n")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)

    success_count = 0
    fail_count = 0

    for i, f in enumerate(pdf_files, 1):
        label = f"{f['subject_code']}/Sec-{f['section'] or 'Gen'}/Unit-{f['unit_number']}"
        print(f"[{i}/{len(pdf_files)}] {label} | {f['filename']}", end=" ... ", flush=True)

        try:
            with open(f["filepath"], "rb") as fh:
                files_data = {"file": (f["filename"], fh, "application/pdf")}
                form_data = {
                    "subject_code": f["subject_code"],
                    "unit_number": str(f["unit_number"]),
                }
                if f["section"]:
                    form_data["section"] = f["section"]

                resp = requests.post(UPLOAD_ENDPOINT, files=files_data, data=form_data, timeout=180)

            if resp.status_code == 200:
                data = resp.json()
                chunks = data.get("chunks_created", 0)
                print(f"OK ({chunks} chunks)")
                success_count += 1
            else:
                print(f"FAIL ({resp.status_code})")
                fail_count += 1
        except Exception as e:
            print(f"ERROR: {e}")
            fail_count += 1

        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"  DONE: {success_count} OK, {fail_count} failed, {len(ocr_files)} skipped")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
