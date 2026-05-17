#!/usr/bin/env python3
"""
academic_pdf_chunker.py
─────────────────────────────────────────────────────────────────────────────
Called by Logstash (academic_pdf_pipeline.conf) with a single PDF path arg.
Designed for academic / research papers — handles:
  • Single-column and two-column layouts  (BI_approaches, Walmart paper)
  • Numbered sections  (1. Introduction, 3.1 Dataset)
  • Roman-numeral sections  (I. INTRODUCTION, IV. TECHNOLOGY)
  • Standard unnumbered headers  (Abstract, References, Conclusion)
  • Duplicate page deduplication  (IoT paper prints abstract twice)
  • Junk page filtering  (ResearchGate cover, reference-only pages)
  • Paper-level metadata extraction  (title, year, doc_type)
  • Optional sentence-transformer embeddings

Writes one JSON object per line to stdout — Logstash reads these and
creates one ES document per chunk.

Requirements:
  pip install pdfplumber sentence-transformers --break-system-packages

Usage (by Logstash, not directly):
  python3 academic_pdf_chunker.py /path/to/paper.pdf
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import os
import re
import json
import hashlib

import pdfplumber

# ── Config ────────────────────────────────────────────────────────────────────
CHUNK_SIZE     = 1000    # chars per chunk (fallback fixed mode)
OVERLAP        = 200     # overlap between fixed chunks
EMBED          = False   # True = include 384-dim sentence-transformer vector
EMBED_MODEL    = "all-MiniLM-L6-v2"

# Minimum chars for a chunk to be indexed — filters out empty/tiny sections
MIN_CHUNK_CHARS = 80

# ── Optional: load embedding model ───────────────────────────────────────────
if EMBED:
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer(EMBED_MODEL)

def embed(text):
    if not EMBED:
        return None
    return _model.encode(text, show_progress_bar=False).tolist()

# ── Two-column detection and extraction ──────────────────────────────────────
def extract_page_text(page):
    """
    Smart page extractor:
    - Detects two-column layout by checking word x-coordinate distribution
    - If two-column: extracts left and right halves separately via bounding box
    - If single-column: standard extract_text()

    Handles: IEEE conference papers (Walmart), journal papers (BI, IoT)
    """
    w = page.width
    h = page.height

    words = page.extract_words()
    if not words:
        return ""

    # Split words into left/right halves
    left_words  = [wd for wd in words if wd["x0"] < w / 2]
    right_words = [wd for wd in words if wd["x0"] >= w / 2]

    # Two-column heuristic: both halves have substantial word count
    # and are roughly balanced (ratio > 0.35)
    total = len(words)
    if total == 0:
        return ""

    left_ratio  = len(left_words) / total
    right_ratio = len(right_words) / total
    is_two_col  = (left_ratio > 0.25 and right_ratio > 0.25
                   and min(left_ratio, right_ratio) / max(left_ratio, right_ratio) > 0.35)

    if is_two_col:
        # Extract each column separately using bounding box
        # Add small margin (5pt) to avoid clipping column boundary characters
        left_text  = page.within_bbox((0,       0, w / 2 + 5, h)).extract_text() or ""
        right_text = page.within_bbox((w / 2 - 5, 0, w,       h)).extract_text() or ""
        return left_text.strip() + "\n" + right_text.strip()
    else:
        return page.extract_text() or ""

# ── Junk page detection ───────────────────────────────────────────────────────
def is_junk_page(text):
    """
    Returns True for pages that add no semantic value:
    - ResearchGate / publisher cover pages (short, lots of metadata)
    - Pure reference pages (>60% lines are "[N] Author..." citations)
    - Effectively empty pages
    """
    if not text or len(text.strip()) < 50:
        return True

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return True

    # ResearchGate cover: short page with "researchgate" keyword
    if "researchgate" in text.lower() and len(text) < 800:
        return True

    # ScienceDirect / Elsevier cover boilerplate
    if "sciencedirect" in text.lower() and len(text) < 600:
        return True

    # Pure reference page: >55% lines start with [N] citation format
    citation_lines = sum(1 for l in lines if re.match(r'^\[\d+\]', l))
    if citation_lines / len(lines) > 0.55:
        return True

    return False

# ── Full text extraction ──────────────────────────────────────────────────────
def extract_full_text(pdf_path):
    """
    Extract all text from PDF, applying smart column detection per page
    and filtering junk pages. Returns (full_text, list_of_page_texts).
    """
    page_texts = []
    seen_page_hashes = set()   # dedup identical pages (e.g. IoT duplicate abstract)

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = extract_page_text(page)

            if is_junk_page(text):
                continue

            # Deduplicate pages with identical content (ScienceDirect duplicate abstract)
            page_hash = hashlib.md5(text.strip().encode()).hexdigest()
            if page_hash in seen_page_hashes:
                continue
            seen_page_hashes.add(page_hash)

            page_texts.append((page_num + 1, text))

    full_text = "\n\n".join(t for _, t in page_texts)
    return full_text, page_texts

# ── Paper metadata extraction ─────────────────────────────────────────────────
def parse_paper_metadata(full_text, filename):
    """
    Extract title, year, authors, journal/venue from the first ~500 chars.
    These fields are indexed alongside every chunk for filtering in ES.
    """
    head = full_text[:800]

    # Year: first 4-digit year in 1990-2030 range
    year_match = re.search(r'\b(199\d|200\d|201\d|202\d)\b', head)
    year = year_match.group(0) if year_match else ""

    # Title heuristic: longest line in first 300 chars that looks like a title
    lines = [l.strip() for l in head[:300].splitlines() if len(l.strip()) > 20]
    title = lines[0] if lines else filename.replace("_", " ").replace(".pdf", "")

    # Journal/venue keywords
    venue = ""
    venue_patterns = [
        r'Procedia Computer Science',
        r'American Journal of Scientific Research',
        r'Information Systems Management',
        r'Expert Systems with Applications',
        r'Conference Paper',
        r'ICCIDS \d{4}',
        r'APWConCSE',
    ]
    for pat in venue_patterns:
        m = re.search(pat, head, re.IGNORECASE)
        if m:
            venue = m.group(0)
            break

    return {
        "doc_title":   title[:200],
        "doc_year":    year,
        "doc_venue":   venue,
        "doc_type":    "academic_paper",
        "source_file": filename,
    }

# ── Academic section detection ────────────────────────────────────────────────
# Matches:
#   "1. Introduction"        (numbered)
#   "3.1 Dataset Collection" (sub-numbered)
#   "I. INTRODUCTION"        (roman numeral, IEEE style)
#   "IV. TECHNOLOGY"
#   "Abstract", "References", "Conclusion", "Related Work" etc.
SECTION_RE = re.compile(
    r'^('
    r'\d+(?:\.\d+)*\.?\s+[A-Z][A-Za-z\s&]{3,60}'   # 1. Intro / 3.1 Dataset
    r'|[IVX]{1,5}\.\s+[A-Z][A-Z\s]{2,50}'          # I. INTRODUCTION
    r'|Abstract'
    r'|Introduction'
    r'|Related\s+Work'
    r'|Background'
    r'|Methodology'
    r'|Method(?:s)?'
    r'|Dataset\s+Collection'
    r'|Results?\s+(?:and\s+)?(?:Discussion)?'
    r'|Discussion'
    r'|Conclusion(?:s)?(?:\s+and\s+Future\s+Work)?'
    r'|References'
    r'|Acknowledgements?'
    r')',
    re.MULTILINE
)

def split_into_sections(text):
    """
    Split full paper text into named sections using SECTION_RE.
    Returns list of (section_name, section_body) tuples.
    Sections with <MIN_CHUNK_CHARS body are merged into the previous section.
    """
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return [("Full Text", text)]

    sections = []
    for i, match in enumerate(matches):
        name  = match.group(0).strip()
        start = match.end()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body  = text[start:end].strip()
        sections.append((name, body))

    # Prepend any text before first section header as "Header"
    if matches[0].start() > 0:
        header_text = text[:matches[0].start()].strip()
        if len(header_text) > MIN_CHUNK_CHARS:
            sections.insert(0, ("Header", header_text))

    # Merge tiny sections into previous (avoids orphan chunks)
    merged = []
    for name, body in sections:
        if merged and len(body) < MIN_CHUNK_CHARS:
            prev_name, prev_body = merged[-1]
            merged[-1] = (prev_name, prev_body + "\n" + name + "\n" + body)
        else:
            merged.append((name, body))

    return merged

# ── Fixed-size fallback chunker ───────────────────────────────────────────────
def chunk_fixed(text, source_file, metadata):
    """
    Fallback: overlapping fixed-size character windows.
    Used when section detection finds <2 sections (e.g. badly parsed PDF).
    """
    step   = CHUNK_SIZE - OVERLAP
    chunks = []
    idx    = 0
    seen   = set()
    for start in range(0, len(text), step):
        chunk_text = text[start: start + CHUNK_SIZE].strip()
        if not chunk_text or len(chunk_text) < MIN_CHUNK_CHARS:
            continue
        h = hashlib.md5(chunk_text.encode()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        doc = {
            **metadata,
            "section":     "fixed_chunk",
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

# ── Main chunker ──────────────────────────────────────────────────────────────
def build_chunks(pdf_path, full_text, metadata):
    """
    Try section-aware chunking first.
    If fewer than 2 sections detected, fall back to fixed-size chunking.
    Deduplicates chunks by content hash.
    """
    sections = split_into_sections(full_text)

    if len(sections) < 2:
        # Section detection failed — use fixed chunking
        return chunk_fixed(full_text, metadata["source_file"], metadata)

    chunks     = []
    seen_hashes = set()

    for idx, (section_name, body) in enumerate(sections):
        # Skip reference-heavy sections (they hurt semantic search quality)
        if section_name.lower().startswith("ref"):
            continue

        chunk_text = f"{section_name}\n{body}"

        # Deduplicate by content hash
        h = hashlib.md5(chunk_text.strip().encode()).hexdigest()
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        # If section body is very long, sub-chunk it with overlap
        if len(chunk_text) > CHUNK_SIZE * 2:
            step = CHUNK_SIZE - OVERLAP
            for sub_idx, start in enumerate(range(0, len(chunk_text), step)):
                sub_text = chunk_text[start: start + CHUNK_SIZE].strip()
                if len(sub_text) < MIN_CHUNK_CHARS:
                    continue
                sub_h = hashlib.md5(sub_text.encode()).hexdigest()
                if sub_h in seen_hashes:
                    continue
                seen_hashes.add(sub_h)
                doc = {
                    **metadata,
                    "section":     section_name,
                    "chunk_index": f"{idx}_{sub_idx}",
                    "chunk_text":  sub_text,
                    "is_sub_chunk": True,
                }
                if EMBED:
                    doc["embedding"] = embed(sub_text)
                chunks.append(doc)
        else:
            doc = {
                **metadata,
                "section":      section_name,
                "chunk_index":  idx,
                "chunk_text":   chunk_text,
                "is_sub_chunk": False,
            }
            if EMBED:
                doc["embedding"] = embed(chunk_text)
            chunks.append(doc)

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
        full_text, page_texts = extract_full_text(pdf_path)
    except Exception as e:
        print(json.dumps({"error": f"Extraction failed: {e}"}), file=sys.stderr)
        sys.exit(1)

    if not full_text.strip():
        print(json.dumps({"error": "No text extracted"}), file=sys.stderr)
        sys.exit(1)

    metadata = parse_paper_metadata(full_text, filename)
    chunks   = build_chunks(pdf_path, full_text, metadata)

    for chunk in chunks:
        print(json.dumps(chunk))

if __name__ == "__main__":
    main()
