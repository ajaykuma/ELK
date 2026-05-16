"""
es_ingest_semantic.py
─────────────────────────────────────────────────────────────────────────────
Lab-report ingestion pipeline with:
  • Structured section chunking  (kept from original es_ingest.py)
  • Patient metadata extraction  (kept from original)
  • Abnormal-test detection      (kept from original)
  • sentence-transformers embeddings on every chunk  (new)
  • kNN semantic search          (new)
  • Hybrid BM25 + kNN search     (new)
  • All original CLI flags preserved + two new ones

Requirements:
  pip install pdfplumber elasticsearch=8.18 sentence-transformers --break-system-packages

Usage:
  # Ingest all PDFs (builds embeddings — takes ~1-2 min for 50 PDFs):
  python es_ingest_semantic.py --ingest

  # Full-text BM25 search (original behaviour):
  python es_ingest_semantic.py --search "diabetes high glucose"

  # Semantic kNN search (new):
  python es_ingest_semantic.py --semantic "patient with poor kidney function and high sugar"

  # Hybrid BM25 + kNN (new, usually best):
  python es_ingest_semantic.py --hybrid "thyroid hormone imbalance fatigue"

  # Stats:
  python es_ingest_semantic.py --stats
─────────────────────────────────────────────────────────────────────────────
"""

import os, re, json, argparse, uuid
import pdfplumber
from elasticsearch import Elasticsearch, helpers
from sentence_transformers import SentenceTransformer

# ── Config ────────────────────────────────────────────────────────────────────
ES_HOST    = "http://localhost:9200"
INDEX      = "lab_reports_semantic"
PDF_DIR    = "E:\\ES_Wrk_Gen+Ing+Search\\lab_reports"
EMBED_MODEL = "all-MiniLM-L6-v2"   # 384-dim, fast, good general quality
EMBED_DIMS  = 384                   # must match model output

es    = Elasticsearch(ES_HOST)
model = SentenceTransformer(EMBED_MODEL)

# ── Index mapping ─────────────────────────────────────────────────────────────
# dense_vector added alongside all original fields
MAPPING = {
    "mappings": {
        "properties": {
            # ── patient metadata (unchanged) ──────────────────────────────
            "patient_id":    {"type": "keyword"},
            "patient_name":  {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "gender":        {"type": "keyword"},
            "dob":           {"type": "keyword"},
            "doctor":        {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "specialty":     {"type": "keyword"},
            "report_date":   {"type": "keyword"},
            "sample_date":   {"type": "keyword"},
            "diagnosis":     {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            # ── chunk fields (unchanged) ──────────────────────────────────
            "section":       {"type": "keyword"},
            "chunk_text":    {"type": "text"},
            "abnormal_tests":{"type": "keyword"},
            "abnormal_count":{"type": "integer"},
            "source_file":   {"type": "keyword"},
            "chunk_index":   {"type": "integer"},
            # ── NEW: embedding vector ─────────────────────────────────────
            "embedding": {
                "type":       "dense_vector",
                "dims":       EMBED_DIMS,
                "index":      True,          # required for kNN search
                "similarity": "cosine",      # cosine distance for sentence-transformers
            },
        }
    }
}

# ── PDF Parser (unchanged from original) ─────────────────────────────────────
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

def find_abnormal(section_text):
    abnormal = []
    for line in section_text.splitlines():
        if "HIGH" in line or "LOW" in line:
            m = re.match(r"^([A-Za-z /%().-]+?)\s+[\d.]", line)
            if m:
                abnormal.append(m.group(1).strip())
    return abnormal

# ── Build chunks with embeddings ──────────────────────────────────────────────
def build_chunks(pdf_path):
    """
    Parse one PDF into section chunks.
    Each chunk gets:
      - all patient metadata fields
      - section name + body text
      - abnormal test list
      - a 384-dim sentence-transformer embedding of the chunk text
    """
    text     = extract_text(pdf_path)
    info     = parse_patient_info(text)
    sections = split_into_sections(text)
    filename = os.path.basename(pdf_path)

    chunks = []
    for idx, (section_name, body) in enumerate(sections.items()):
        chunk_text = f"{section_name}\n{body}"
        abnormal   = find_abnormal(body)

        # Embed the chunk text — encode returns a numpy array, convert to list for ES
        embedding = model.encode(chunk_text, show_progress_bar=False).tolist()

        chunk = {
            **info,
            "section":        section_name,
            "chunk_text":     chunk_text,
            "abnormal_tests": abnormal,
            "abnormal_count": len(abnormal),
            "source_file":    filename,
            "chunk_index":    idx,
            "embedding":      embedding,   # NEW
        }
        chunks.append(chunk)
    return chunks

# ── Ingest ────────────────────────────────────────────────────────────────────
def ingest_all():
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)
        print(f"Deleted existing index '{INDEX}'")
    es.indices.create(index=INDEX, body=MAPPING)
    print(f"Created index '{INDEX}'")
    print(f"Embedding model : {EMBED_MODEL}  ({EMBED_DIMS} dims)\n")

    all_docs = []
    pdfs     = sorted(f for f in os.listdir(PDF_DIR) if f.endswith(".pdf"))
    for pdf_file in pdfs:
        path   = os.path.join(PDF_DIR, pdf_file)
        chunks = build_chunks(path)
        for c in chunks:
            all_docs.append({
                "_index":  INDEX,
                "_id":     str(uuid.uuid4()),   # stable unique ID per chunk
                "_source": c,
            })
        print(f"  {pdf_file}  →  {len(chunks)} chunks embedded")

    success, errors = helpers.bulk(es, all_docs, raise_on_error=False)
    print(f"\n Indexed {success} chunks from {len(pdfs)} PDFs")
    if errors:
        print(f" Errors: {len(errors)}")

# ── Helper: print results ─────────────────────────────────────────────────────
def _print_results(hits, query, mode, dedup, size):
    total = len(hits)

    # Deduplicate by patient_id — keep highest-score chunk per patient
    if dedup:
        seen = {}
        for h in hits:
            pid = h["_source"].get("patient_id", "?")
            if pid not in seen:
                seen[pid] = h
        display = list(seen.values())[:size]
    else:
        display = hits[:size]

    print(f"\n [{mode}] Query : '{query}'")
    print(f"    Raw hits : {total}  |  Showing : {len(display)}"
          + (" (deduped by patient)" if dedup else "") + "\n")

    sep = "─" * 72
    for rank, h in enumerate(display, 1):
        s  = h["_source"]
        sc = round(h.get("_score") or 0, 4)
        hl = " … ".join(
            re.sub(r"<[^>]+>", "", f)
            for f in h.get("highlight", {}).get("chunk_text", [])
        )
        abn = s.get("abnormal_tests", [])
        print(sep)
        print(f"  #{rank}  [{s.get('patient_id','?')}]  {s.get('patient_name','—')}  "
              f"|  score: {sc}")
        print(f"       Diagnosis : {s.get('diagnosis','')}")
        print(f"       Specialty : {s.get('specialty','')}  "
              f"|  Section: {s.get('section','')}")
        if abn:
            print(f"       Abnormal  : {', '.join(abn)}")
        if hl:
            print(f"       Context   : …{hl[:250]}…")
        print()
    print(sep)

# ── BM25 full-text search (original behaviour, unchanged) ─────────────────────
def search(query, size=10, dedup=True):
    resp = es.search(index=INDEX, body={
        "size": size * (5 if dedup else 1),
        "query": {
            "multi_match": {
                "query":     query,
                "fields":    ["chunk_text^2", "diagnosis^3", "patient_name", "abnormal_tests^2"],
                "type":      "best_fields",
                "fuzziness": "AUTO",
            }
        },
        "highlight": {
            "fields": {"chunk_text": {"fragment_size": 220, "number_of_fragments": 1}}
        },
    })
    _print_results(resp["hits"]["hits"], query, "BM25 full-text", dedup, size)

# ── Semantic kNN search (new) ─────────────────────────────────────────────────
def semantic_search(query, size=10, dedup=True):
    """
    Pure semantic search using kNN over the dense_vector field.
    Good for natural-language questions where exact terms don't appear in the text.
    e.g. "patient with poor kidney function and high sugar" finds CKD + diabetes
         even if those exact words aren't in the chunk.
    """
    query_vec = model.encode(query).tolist()
    resp = es.search(index=INDEX, body={
        "knn": {
            "field":          "embedding",
            "query_vector":   query_vec,
            "k":              size * (5 if dedup else 1),
            "num_candidates": 150,   # ES searches this many candidates, returns k
        },
        "_source": True,
    })
    _print_results(resp["hits"]["hits"], query, "Semantic kNN", dedup, size)

# ── Hybrid BM25 + kNN search (new) ───────────────────────────────────────────
def hybrid_search(query, size=10, dedup=True):
    """
    Combines BM25 keyword relevance with semantic kNN using Reciprocal Rank Fusion.
    Generally the best of both worlds:
      - BM25 catches exact test names like "HbA1c", "TSH", "eGFR"
      - kNN catches conceptual matches like "blood sugar" → Glucose / HbA1c chunks
    RRF merges both ranked lists without needing manual score weighting.
    """
    query_vec = model.encode(query).tolist()
    resp = es.search(index=INDEX, body={
        "query": {
            "multi_match": {
                "query":     query,
                "fields":    ["chunk_text^2", "diagnosis^3", "patient_name", "abnormal_tests^2"],
                "type":      "best_fields",
                "fuzziness": "AUTO",
            }
        },
        "knn": {
            "field":          "embedding",
            "query_vector":   query_vec,
            "k":              size * (5 if dedup else 1),
            "num_candidates": 150,
        },
        "rank": {"rrf": {}},   # Reciprocal Rank Fusion — no manual score tuning needed
        "size": size * (5 if dedup else 1),
        "highlight": {
            "fields": {"chunk_text": {"fragment_size": 220, "number_of_fragments": 1}}
        },
    })
    _print_results(resp["hits"]["hits"], query, "Hybrid BM25+kNN (RRF)", dedup, size)

# ── Stats (unchanged from original) ──────────────────────────────────────────
def stats():
    diag_agg = es.search(index=INDEX, body={
        "size": 0,
        "query": {"term": {"section": "Header"}},
        "aggs": {"diagnoses": {"terms": {"field": "diagnosis.keyword", "size": 20}}},
    })
    avg_agg = es.search(index=INDEX, body={
        "size": 0,
        "aggs": {
            "by_diagnosis": {
                "terms": {"field": "diagnosis.keyword", "size": 20},
                "aggs": {"avg_abnormal": {"avg": {"field": "abnormal_count"}}},
            }
        },
    })
    abnormal_agg = es.search(index=INDEX, body={
        "size": 0,
        "aggs": {"top_abnormal": {"terms": {"field": "abnormal_tests", "size": 20}}},
    })

    output = {
        "index": INDEX,
        "embed_model": EMBED_MODEL,
        "embed_dims": EMBED_DIMS,
        "diagnosis_distribution": [
            {"diagnosis": b["key"], "count": b["doc_count"]}
            for b in diag_agg["aggregations"]["diagnoses"]["buckets"]
        ],
        "avg_abnormal_per_diagnosis": [
            {"diagnosis": b["key"],
             "avg_abnormal": round(b["avg_abnormal"]["value"] or 0, 2)}
            for b in avg_agg["aggregations"]["by_diagnosis"]["buckets"]
        ],
        "most_common_abnormal_tests": [
            {"test": b["key"], "count": b["doc_count"]}
            for b in abnormal_agg["aggregations"]["top_abnormal"]["buckets"]
        ],
    }

    print(json.dumps(output, indent=2))
    out_path = os.path.join(os.path.dirname(__file__), "es_stats.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n Stats saved to {out_path}")
    return output

# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Lab Report ES toolkit — with sentence-transformer semantic search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python es_ingest_semantic.py --ingest
  python es_ingest_semantic.py --search   "diabetes high glucose"
  python es_ingest_semantic.py --semantic "patient with poor kidney function and high sugar"
  python es_ingest_semantic.py --hybrid   "thyroid hormone imbalance"  --size 5
  python es_ingest_semantic.py --stats
        """,
    )
    parser.add_argument("--ingest",   action="store_true", help="Parse PDFs, embed, and index")
    parser.add_argument("--search",   type=str,            help="BM25 full-text search (original)")
    parser.add_argument("--semantic", type=str,            help="Semantic kNN search (new)")
    parser.add_argument("--hybrid",   type=str,            help="Hybrid BM25+kNN search (new, recommended)")
    parser.add_argument("--size",     type=int, default=10,help="Max results (default 10)")
    parser.add_argument("--all",      action="store_true", help="Disable per-patient deduplication")
    parser.add_argument("--stats",    action="store_true", help="Print aggregation stats")
    args = parser.parse_args()

    dedup = not args.all

    if args.ingest:
        ingest_all()
    elif args.search:
        search(args.search,   size=args.size, dedup=dedup)
    elif args.semantic:
        semantic_search(args.semantic, size=args.size, dedup=dedup)
    elif args.hybrid:
        hybrid_search(args.hybrid,  size=args.size, dedup=dedup)
    elif args.stats:
        stats()
    else:
        parser.print_help()
