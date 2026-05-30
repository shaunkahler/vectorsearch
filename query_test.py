import psycopg2
from sentence_transformers import SentenceTransformer

print("Connecting to database...")
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="mysecretpassword",
    host="127.0.0.1",
    port="5433"
)
cur = conn.cursor()

# Load the same high-quality embedding model
model = SentenceTransformer('BAAI/bge-large-en-v1.5')

# The user's semantic search query
query_text = "Find me healthcare AI companies that have raised more than $1 Million"
print(f"\nQuerying: '{query_text}'\n")

# Convert the text into a 1024-dimension vector using the model
query_vector = model.encode([query_text])[0]

# Perform Hybrid Search (Vector Similarity + Hard SQL Filters)
# `<->` is the pgvector operator for Euclidean distance
cur.execute("""
    SELECT 
        company_name, 
        total_funding, 
        hq, 
        status
    FROM companies
    WHERE total_funding > 1000000 
      AND status = 'Active'
    ORDER BY embedding <-> %s::vector
    LIMIT 5;
""", (query_vector.tolist(),))

results = cur.fetchall()

print("TOP 5 HYBRID MATCHES:")
for i, row in enumerate(results):
    company, funding, hq, status = row
    print(f"{i+1}. {company}")
    print(f"   HQ: {hq}")
    print(f"   Funding: ${funding:,.2f}")
    print(f"   Status: {status}\n")

cur.close()
conn.close()
