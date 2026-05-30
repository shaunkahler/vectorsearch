from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from sentence_transformers import SentenceTransformer
import torch
import uvicorn

app = FastAPI(title="Company Vector Search API")

# Allow React app to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the model on startup (utilizing GPU if available)
print("Loading BAAI/bge-large-en-v1.5 model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer('BAAI/bge-large-en-v1.5', device=device)
print("Model loaded successfully!")

def get_db():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="mysecretpassword",
        host="127.0.0.1",
        port="5433"
    )

class SearchRequest(BaseModel):
    query: str
    min_funding: int = 0
    status: str = "Active"
    limit: int = 10

@app.post("/search")
def search_companies(req: SearchRequest):
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # If the user provides a search query, do a semantic vector search
        if req.query.strip() != "":
            query_vector = model.encode([req.query])[0]
            cur.execute("""
                SELECT company_name, hq, total_funding, employee_count, status, stage, links, year_founded, latest_funding, summary
                FROM companies
                WHERE total_funding >= %s AND status ILIKE %s
                ORDER BY embedding <-> %s::vector
                LIMIT %s;
            """, (req.min_funding, f"%{req.status}%", query_vector.tolist(), req.limit))
        
        # If the query is empty, just return the data matching the filters
        else:
            cur.execute("""
                SELECT company_name, hq, total_funding, employee_count, status, stage, links, year_founded, latest_funding, summary
                FROM companies
                WHERE total_funding >= %s AND status ILIKE %s
                ORDER BY total_funding DESC
                LIMIT %s;
            """, (req.min_funding, f"%{req.status}%", req.limit))
            
        rows = cur.fetchall()
        
        results = []
        for r in rows:
            results.append({
                "company_name": r[0],
                "hq": r[1] if r[1] else "Unknown HQ",
                "total_funding": float(r[2]) if r[2] else 0,
                "employee_count": r[3] if r[3] else 0,
                "status": r[4],
                "stage": r[5] if r[5] else "Unknown",
                "links": r[6] if r[6] else "",
                "year_founded": r[7] if r[7] else 0,
                "latest_funding": float(r[8]) if r[8] else 0,
                "summary": r[9] if r[9] else ""
            })
            
        cur.close()
        conn.close()
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
