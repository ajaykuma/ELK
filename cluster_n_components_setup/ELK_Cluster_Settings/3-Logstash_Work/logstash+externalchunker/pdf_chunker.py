#!/usr/bin/env python3
"""
pdf_chunker.py
─────────────────────────────────────────────────────────────────────────────
Called by Logstash's ruby filter (Open3.capture3) with a single PDF path arg.
Writes one JSON object per line to stdout — one line per chunk.
Logstash reads these lines, splits them into individual events, and indexes
each chunk as a separate ES document.

Two chunking modes (set MODE below):
  "structured"  — split by named section headers (lab-report PDFs)
  "fixed"       — split by character count (generic PDFs, e.g. BI_approaches.pdf)

Embeddings are optional — set EMBED = True to include a dense_vector field.
Requires: pdfplumber, sentence-transformers (optional)

Usage (by Logstash, not directly):
  python3 pdf_chunker.py /path/to/report.pdf
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import os
import re
import json

import pdfplumber

# ── Config ────────────────────────────────────────────────────────────────────
MODE        = "structured"   # "structured" | "fixed"
CHUNK_SIZE  = 1000           # chars per chunk (fixed mode only)
EMBED       = True          # True = include 384-dim sentence-transformer vector
                             # Adds ~2s per PDF; set False if not needed
EMBED_MODEL = "all-MiniLM-L6-v2"

# ── Optional: load embedding model ───────────────────────────────────────────
if EMBED:
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer(EMBED_MODEL)

def embed(text):
    if not EMBED:
        return None
    return _model.encode(text, show_progress_bar=False).tolist()

# ── PDF text extraction ───────────────────────────────────────────────────────
def extract_text(pdf_path):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    return "\n".join(pages)

# ── Patient metadata parser (lab reports) ────────────────────────────────────
def parse_patient_info(text):
    def grab(pattern, default=""):
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            return default
        return next((g.strip() for g in m.groups() if g), default)

    return {
        "patient_name": grab(r"Patient Name:\s*(.+?)\s{2,}|Patient Name:\s*(.+?)\n"),
        "patient_id":   grab(r"Patient ID:\s*(P\d+)"),
        "dob":          grab(r"Date of Birth:\s*(.+?)\s{2,}"),
        "gender":       grab(r"Gender:\s*(\w+)"),
        "doctor":       grab(r"Ordering Doctor:\s*(.+?)\s{2,}"),
        "specialty":    grab(r"Specialty:\s*(.+?)\n"),
        "sample_date":  grab(r"Sample Collected:\s*(.+?)\s{2,}"),
        "report_date":  grab(r"Report Date:\s*(.+?)\n"),
        "diagnosis":    grab(r"Clinical Notes:\s*(.+?)\n"),
    }

# ── Abnormal test detector ────────────────────────────────────────────────────
def find_abnormal(section_text):
    abnormal = []
    for line in section_text.splitlines():
        if "HIGH" in line or "LOW" in line:
            m = re.match(r"^([A-Za-z /%().-]+?)\s+[\d.]", line)
            if m:
                abnormal.append(m.group(1).strip())
    return abnormal

# ── Structured chunking (lab reports) ────────────────────────────────────────
SECTION_HEADERS = [
    "Complete Blood Count",
    "Thyroid Function",
    "Basic Metabolic",
    "Allergy & Pulmonary",
    "Diabetes & Renal",
    "Iron Studies",
    "Cardiac Markers",
    "Infection & Inflammation",
    "Hormonal Panel",
    "Autoimmune Markers",
    "Interpreting Physician",
]

def clean_header_chunk(text):
    lines = [l for l in text.splitlines() if not re.fullmatch(r'\s*\d+\.\s*', l)]
    return "\n".join(lines).strip()

def split_into_sections(text):
    pattern = "(" + "|".join(re.escape(h) for h in SECTION_HEADERS) + ")"
    parts   = re.split(pattern, text, flags=re.IGNORECASE)
    sections = {}
    i = 1
    while i < len(parts) - 1:
        header = parts[i].strip()
        body   = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections[header[:30]] = body
        i += 2
    if parts:
        sections["Header"] = clean_header_chunk(parts[0])
    return sections

def chunk_structured(pdf_path, text, filename):
    info     = parse_patient_info(text)
    sections = split_into_sections(text)
    chunks   = []
    for idx, (section_name, body) in enumerate(sections.items()):
        chunk_text = f"{section_name}\n{body}"
        abnormal   = find_abnormal(body)
        doc = {
            **info,
            "section":         section_name,
            "chunk_text":      chunk_text,
            "abnormal_tests":  abnormal,
            "abnormal_count":  len(abnormal),
            "source_file":     filename,
            "chunk_index":     idx,
        }
        if EMBED:
            doc["embedding"] = embed(chunk_text)
        chunks.append(doc)
    return chunks

# ── Fixed-size chunking (generic PDFs) ───────────────────────────────────────
def chunk_fixed(pdf_path, text, filename):
    """
    Splits text into overlapping fixed-size character windows.
    CHUNK_SIZE chars with 200-char overlap to avoid cutting sentences mid-thought.
    """
    overlap  = 200
    step     = CHUNK_SIZE - overlap
    chunks   = []
    idx      = 0
    for start in range(0, len(text), step):
        chunk_text = text[start : start + CHUNK_SIZE]
        if not chunk_text.strip():
            continue
        doc = {
            "source_file": filename,
            "chunk_index": idx,
            "chunk_text":  chunk_text,
            "char_start":  start,
            "char_end":    start + len(chunk_text),
        }
        if EMBED:
            doc["embedding"] = embed(chunk_text)
        chunks.append(doc)
        idx += 1
    return chunks

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No PDF path provided"}), file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1].strip()

    if not os.path.isfile(pdf_path):
        print(json.dumps({"error": f"File not found: {pdf_path}"}), file=sys.stderr)
        sys.exit(1)

    filename = os.path.basename(pdf_path)

    try:
        text = extract_text(pdf_path)
    except Exception as e:
        print(json.dumps({"error": f"pdfplumber failed: {e}"}), file=sys.stderr)
        sys.exit(1)

    if not text.strip():
        print(json.dumps({"error": "No text extracted from PDF"}), file=sys.stderr)
        sys.exit(1)

    if MODE == "structured":
        chunks = chunk_structured(pdf_path, text, filename)
    else:
        chunks = chunk_fixed(pdf_path, text, filename)

    # Write one JSON object per line to stdout — Logstash reads these
    for chunk in chunks:
        print(json.dumps(chunk))   # newline-delimited JSON

if __name__ == "__main__":
    main()
