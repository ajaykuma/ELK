"""
es_ingest.py
─────────────────────────────────────────────────────────────────────────────
Parses each lab-report PDF, chunks it into structured sections, and indexes
every chunk into Elasticsearch.  Also provides helper search functions.

Requirements:
  pip install pdfplumber elasticsearch=8.18 --break-system-packages

Usage:
  # 1. Start Elasticsearch (Docker example):
  #    docker run -d --name es -p 9200:9200 -e "discovery.type=single-node" \
  #               -e "xpack.security.enabled=false" \
  #               docker.elastic.co/elasticsearch/elasticsearch:8.13.0

  # 2. Run ingestion:
  #    python es_ingest.py --ingest

  # 3. Run a search:
  #    python es_ingest.py --search "diabetes high glucose"

  # 4. Show stats (for visualisations):
  #    python es_ingest.py --stats
─────────────────────────────────────────────────────────────────────────────
"""

import os, re, json, argparse
import pdfplumber
from elasticsearch import Elasticsearch, helpers
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
ES_HOST  = "http://localhost:9200"
INDEX    = "lab_reports"
PDF_DIR = "E:\\ES_Wrk_Gen+Ing+Search\\lab_reports"

es = Elasticsearch(ES_HOST)

# ── Index mapping ─────────────────────────────────────────────────────────────
MAPPING = {
    "mappings": {
        "properties": {
            "patient_id":   {"type": "keyword"},
            "patient_name": {"type": "text",    "fields": {"keyword": {"type": "keyword"}}},
            "gender":       {"type": "keyword"},
            "dob":          {"type": "keyword"},
            "doctor":       {"type": "text",    "fields": {"keyword": {"type": "keyword"}}},
            "specialty":    {"type": "keyword"},
            "report_date":  {"type": "keyword"},
            "sample_date":  {"type": "keyword"},
            "diagnosis":    {"type": "text",    "fields": {"keyword": {"type": "keyword"}}},
            "section":      {"type": "keyword"},   # e.g. "CBC", "Thyroid", "Metabolic"
            "chunk_text":   {"type": "text"},       # full section text for full-text search
            "abnormal_tests":{"type": "keyword"},   # list of abnormal test names
            "abnormal_count":{"type": "integer"},
            "source_file":  {"type": "keyword"},
            "chunk_index":  {"type": "integer"},
        }
    }
}

# ── PDF Parser ────────────────────────────────────────────────────────────────
def extract_text(pdf_path):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    return "\n".join(pages)

def parse_patient_info(text):
    def grab(pattern, default=""):
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            return default
        # Return first non-None group
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
    """
    Remove stray section-number lines like '1.' or '2.' that leak into
    the Header chunk because the PDF text extractor picks up the numbering
    from the next section heading before the split regex fires.
    """
    # Drop lines that are just a number + period (e.g. "1.", "2.")
    lines = [l for l in text.splitlines() if not re.fullmatch(r'\s*\d+\.\s*', l)]
    return "\n".join(lines).strip()

def split_into_sections(text):
    """Split full text into named sections."""
    pattern = "(" + "|".join(re.escape(h) for h in SECTION_HEADERS) + ")"
    parts = re.split(pattern, text, flags=re.IGNORECASE)
    sections = {}
    i = 1
    while i < len(parts) - 1:
        header = parts[i].strip()
        body   = parts[i+1].strip() if i+1 < len(parts) else ""
        key    = header[:30]
        sections[key] = body
        i += 2
    # Always include a catch-all for the header block, cleaned of stray "N." lines
    if parts:
        sections["Header"] = clean_header_chunk(parts[0])
    return sections

def find_abnormal(section_text):
    """Return list of test names flagged HIGH or LOW in a section."""
    abnormal = []
    for line in section_text.splitlines():
        if "HIGH" in line or "LOW" in line:
            # First token(s) before a digit are usually the test name
            m = re.match(r"^([A-Za-z /%().-]+?)\s+[\d.]", line)
            if m:
                abnormal.append(m.group(1).strip())
    return abnormal

# ── Build chunks ──────────────────────────────────────────────────────────────
def build_chunks(pdf_path):
    text = extract_text(pdf_path)
    info = parse_patient_info(text)
    sections = split_into_sections(text)
    filename = os.path.basename(pdf_path)

    chunks = []
    for idx, (section_name, body) in enumerate(sections.items()):
        abnormal = find_abnormal(body)
        chunk = {
            **info,
            "section":       section_name,
            "chunk_text":    f"{section_name}\n{body}",
            "abnormal_tests": abnormal,
            "abnormal_count": len(abnormal),
            "source_file":   filename,
            "chunk_index":   idx,
        }
        chunks.append(chunk)
    return chunks

# ── Ingest ────────────────────────────────────────────────────────────────────
def ingest_all():
    # Create or recreate index
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)
        print(f"Deleted existing index '{INDEX}'")
    es.indices.create(index=INDEX, body=MAPPING)
    print(f"Created index '{INDEX}'")

    all_chunks = []
    pdfs = sorted(f for f in os.listdir(PDF_DIR) if f.endswith(".pdf"))
    for pdf_file in pdfs:
        path = os.path.join(PDF_DIR, pdf_file)
        chunks = build_chunks(path)
        for c in chunks:
            all_chunks.append({"_index": INDEX, "_source": c})
        print(f"  Parsed {pdf_file}  → {len(chunks)} chunks")

    success, errors = helpers.bulk(es, all_chunks, raise_on_error=False)
    print(f"\n Indexed {success} chunks from {len(pdfs)} PDFs")
    if errors:
        print(f" Errors: {len(errors)}")

# ── Search ────────────────────────────────────────────────────────────────────
def search(query, size=10, dedup=True):
    """
    Search the index.
    - size: how many raw ES hits to fetch (each hit = one chunk of one patient)
    - dedup: if True, collapse multiple chunks from the same patient and show
             the single best-scoring chunk per patient (recommended default).
             Set --all to disable deduplication and see every matching chunk.

    Why you saw "100 total hits" but only 10 results:
      ES counts ALL matching chunks across all sections and pages.
      50 patients × ~6 sections each = ~300 indexed chunks total.
      A broad query like "kidney" can match the CBC chunk AND the Metabolic chunk
      AND the Header chunk of every CKD patient → many hits per patient.
      Dedup collapses these to one row per patient.
    """
    resp = es.search(index=INDEX, body={
        "size": size * (5 if dedup else 1),   # fetch extra to have enough after dedup
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["chunk_text^2", "diagnosis^3", "patient_name", "abnormal_tests^2"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        },
        "highlight": {
            "fields": {"chunk_text": {"fragment_size": 220, "number_of_fragments": 1}}
        }
    })

    total_chunks = resp["hits"]["total"]["value"]
    hits = resp["hits"]["hits"]

    # Deduplicate: keep only highest-score chunk per patient
    seen = {}
    for h in hits:
        pid = h["_source"].get("patient_id", "?")
        if pid not in seen:
            seen[pid] = h

    display = list(seen.values())[:size] if dedup else hits[:size]
    unique_patients = len(seen)

    print(f"\n Query : '{query}'")
    print(f"    ES total chunk hits : {total_chunks}  "
          f"(each patient has ~6 section chunks — multiply patients × sections)")
    if dedup:
        print(f"    Unique patients matched : {unique_patients}  "
              f"(showing top {len(display)}, best chunk per patient)\n")
    else:
        print(f"    Showing {len(display)} raw chunk hits (no dedup)\n")

    sep = "─" * 72
    for rank, h in enumerate(display, 1):
        s  = h["_source"]
        sc = round(h["_score"], 2)
        hl = " … ".join(
            re.sub(r"<[^>]+>", "", f)
            for f in h.get("highlight", {}).get("chunk_text", [])
        )
        abn = s.get("abnormal_tests", [])
        print(f"{sep}")
        print(f"  #{rank}  [{s.get('patient_id','?')}]  {s.get('patient_name','—')}  "
              f"|  score: {sc}")
        print(f"       Diagnosis : {s.get('diagnosis','')}")
        print(f"       Specialty : {s.get('specialty','')}  |  "
              f"Section matched: {s.get('section','')}")
        if abn:
            print(f"       Abnormal  : {', '.join(abn)}")
        if hl:
            print(f"       Context   : …{hl[:250]}…")
        print()
    print(sep)
    print(f"  Tip: use --size N to see more results, --all to disable deduplication")

# ── Stats (for visualisations) ────────────────────────────────────────────────
def stats():
    # 1. Diagnosis distribution
    diag_agg = es.search(index=INDEX, body={
        "size": 0,
        "query": {"term": {"section": "Header"}},
        "aggs": {
            "diagnoses": {
                "terms": {"field": "diagnosis.keyword", "size": 20}
            }
        }
    })

    # 2. Average abnormal count per diagnosis (across all sections)
    avg_agg = es.search(index=INDEX, body={
        "size": 0,
        "aggs": {
            "by_diagnosis": {
                "terms": {"field": "diagnosis.keyword", "size": 20},
                "aggs": {
                    "avg_abnormal": {"avg": {"field": "abnormal_count"}}
                }
            }
        }
    })

    # 3. Most common abnormal tests
    # We need a nested query since abnormal_tests is keyword array
    abnormal_agg = es.search(index=INDEX, body={
        "size": 0,
        "aggs": {
            "top_abnormal": {
                "terms": {"field": "abnormal_tests", "size": 20}
            }
        }
    })

    output = {
        "diagnosis_distribution": [
            {"diagnosis": b["key"], "count": b["doc_count"]}
            for b in diag_agg["aggregations"]["diagnoses"]["buckets"]
        ],
        "avg_abnormal_per_diagnosis": [
            {"diagnosis": b["key"], "avg_abnormal": round(b["avg_abnormal"]["value"] or 0, 2)}
            for b in avg_agg["aggregations"]["by_diagnosis"]["buckets"]
        ],
        "most_common_abnormal_tests": [
            {"test": b["key"], "count": b["doc_count"]}
            for b in abnormal_agg["aggregations"]["top_abnormal"]["buckets"]
        ],
    }

    print(json.dumps(output, indent=2))
    # Also save to file for the visualisation dashboard
    with open("/home/claude/es_stats.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\n Stats saved to /home/claude/es_stats.json")
    return output


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lab Report ES toolkit")
    parser.add_argument("--ingest", action="store_true", help="Parse PDFs and ingest into ES")
    parser.add_argument("--search", type=str,            help="Full-text search query")
    parser.add_argument("--size",   type=int, default=10,help="Max results to show (default 10)")
    parser.add_argument("--all",    action="store_true", help="Disable deduplication — show every matching chunk")
    parser.add_argument("--stats",  action="store_true", help="Print aggregation stats")
    args = parser.parse_args()

    if args.ingest:
        ingest_all()
    elif args.search:
        search(args.search, size=args.size, dedup=not args.all)
    elif args.stats:
        stats()
    else:
        parser.print_help()
