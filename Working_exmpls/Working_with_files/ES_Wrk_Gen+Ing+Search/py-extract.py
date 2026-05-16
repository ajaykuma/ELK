#pip install pymupdf sentence-transformers elasticsearch==8.19.0

import fitz
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from sentence_transformers import SentenceTransformer
import uuid

# Elasticsearch connection
es = Elasticsearch(
    ["https://localhost:9200"],
    basic_auth=("elastic", "9_W6d34GiGU8gKoZfLlO"),
    ca_certs="/home/hdu/elasticsearch/config/certs/http_ca.crt"
)

print("Connected:", es.ping())

# Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

PDF_PATH = "/home/hdu/datasets/pdfs/BI_approaches.pdf"

doc = fitz.open(PDF_PATH)

bulk_docs = []

CHUNK_SIZE = 1000

for page_num in range(len(doc)):

    print(f"Processing page {page_num+1}")

    page = doc[page_num]

    text = page.get_text()

    print("Text length:", len(text))

    chunks = [
        text[i:i+CHUNK_SIZE]
        for i in range(0, len(text), CHUNK_SIZE)
    ]

    for idx, chunk in enumerate(chunks):

        embedding = model.encode(chunk).tolist()

        bulk_docs.append({
            "_index": "pdf_chunks",
            "_id": str(uuid.uuid4()),
            "_source": {
                "document_id": PDF_PATH,
                "file_name": PDF_PATH,
                "page": page_num + 1,
                "chunk_id": f"{page_num+1}_{idx}",
                "text": chunk,
                "embedding": embedding
            }
        })

print(f"Prepared {len(bulk_docs)} chunks")

success, failed = bulk(
    es,
    bulk_docs,
    stats_only=True,
    raise_on_error=False
)

print("Indexed:", success)
print("Failed:", failed)
