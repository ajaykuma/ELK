from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

# Elasticsearch connection
es = Elasticsearch(
    ["https://localhost:9200"],
    basic_auth=("elastic", "9_W6d34GiGU8gKoZfLlO"),
    ca_certs="/home/hdu/elasticsearch/config/certs/http_ca.crt"
)

# Same embedding model used during indexing
model = SentenceTransformer("all-MiniLM-L6-v2")

query = "technical approaches in business intelligence"

# Convert query to embedding
query_embedding = model.encode(query).tolist()

response = es.search(
    index="pdf_chunks",
    knn={
        "field": "embedding",
        "query_vector": query_embedding,
        "k": 5,
        "num_candidates": 20
    }
)

for hit in response["hits"]["hits"]:

    print("\nSCORE:", hit["_score"])

    print("PAGE:", hit["_source"]["page"])

    print(hit["_source"]["text"][:500])