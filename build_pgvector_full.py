import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_batch
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import sys
import torch

# 1. Connect to Postgres (Docker)
print("Connecting to database...")
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="mysecretpassword",
    host="127.0.0.1",
    port="5433"
)
conn.autocommit = True
cur = conn.cursor()

# Enable pgvector extension
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
register_vector(conn)

# 2. Setup Database Table with 1024 dimensions for bge-large
print("Creating table with 1024 dimensions...")
cur.execute("DROP TABLE IF EXISTS companies;")
cur.execute("""
    CREATE TABLE companies (
        id SERIAL PRIMARY KEY,
        company_name TEXT,
        stage TEXT,
        year_founded INTEGER,
        hq TEXT,
        latest_funding NUMERIC,
        total_funding NUMERIC,
        employee_count INTEGER,
        status TEXT,
        links TEXT,
        embedding vector(1024) -- 1024 is the dimension for bge-large-en-v1.5
    );
""")

# 3. Load and Clean Data
print("Loading all 21,800 CSV rows...")
df = pd.read_csv('combined_data.csv')

def clean_money(val):
    if pd.isna(val) or val == '—' or val == '$0':
        return 0
    val = str(val).replace('$', '').replace(',', '').strip()
    if val.endswith('M'):
        return float(val[:-1]) * 1_000_000
    elif val.endswith('k') or val.endswith('K'):
        return float(val[:-1]) * 1_000
    elif val.endswith('B'):
        return float(val[:-1]) * 1_000_000_000
    try:
        return float(val)
    except:
        return 0

def clean_employees(val):
    if pd.isna(val) or val == '—':
        return 0
    val = str(val).lower().replace(',', '').strip()
    if val.endswith('k'):
        return int(float(val[:-1]) * 1000)
    try:
        return int(float(val))
    except:
        return 0

print("Cleaning data...")
df['Total Funding Clean'] = df['Total Funding'].apply(clean_money)
df['Latest Funding Clean'] = df['Latest Funding'].apply(clean_money)
df['Employee Count Clean'] = df['Employee Count'].apply(clean_employees)
df['Year Founded'] = pd.to_numeric(df['Year Founded'], errors='coerce')

# 4. Generate Embeddings Block
print("Building text for embeddings...")
df['Text_to_Embed'] = df.apply(lambda row: f"Company Name: {row['Company']}. "
                                           f"Main Products: {row['Main Products'] if not pd.isna(row['Main Products']) else 'Unknown'}. "
                                           f"Summary: {row['Summary'] if not pd.isna(row['Summary']) else ''}. "
                                           f"Tags: {row['Tags'] if not pd.isna(row['Tags']) else ''}. "
                                           f"Technologies used: {row['Technology Used'] if not pd.isna(row['Technology Used']) else 'Unknown'}.", 
                               axis=1)

# 5. Load Embedding Model
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading BAAI/bge-large-en-v1.5 model. Hardware detected: {device.upper()}")
model = SentenceTransformer('BAAI/bge-large-en-v1.5', device=device)

# 7. Generate Embeddings AND Insert in Chunks (so it saves progress and doesn't time out!)
print("Batch processing and inserting data into PostgreSQL in chunks of 2500...")
insert_query = """
    INSERT INTO companies 
    (company_name, stage, year_founded, hq, latest_funding, total_funding, employee_count, status, links, embedding)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""

chunk_size = 2500
total_chunks = (len(df) // chunk_size) + 1

for chunk_idx in range(total_chunks):
    start_idx = chunk_idx * chunk_size
    end_idx = min((chunk_idx + 1) * chunk_size, len(df))
    
    if start_idx >= len(df):
        break
        
    print(f"\nProcessing Chunk {chunk_idx + 1}/{total_chunks} (Rows {start_idx} to {end_idx})...")
    chunk_df = df.iloc[start_idx:end_idx]
    
    # Generate embeddings for just this chunk
    chunk_embeddings = model.encode(chunk_df['Text_to_Embed'].tolist(), show_progress_bar=True, batch_size=128)
    
    data_to_insert = [
        (
            str(row['Company']),
            str(row['Stage']) if not pd.isna(row['Stage']) else None,
            row['Year Founded'] if not pd.isna(row['Year Founded']) else None,
            str(row['HQ']) if not pd.isna(row['HQ']) else None,
            row['Latest Funding Clean'],
            row['Total Funding Clean'],
            row['Employee Count Clean'],
            str(row['Status']) if not pd.isna(row['Status']) else None,
            str(row['Links']) if not pd.isna(row['Links']) else None,
            chunk_embeddings[i].tolist()
        )
        for i, (_, row) in enumerate(chunk_df.iterrows())
    ]
    
    execute_batch(cur, insert_query, data_to_insert, page_size=100)
    print(f"-> Inserted chunk {chunk_idx + 1} successfully.")

print(f"\nSuccessfully processed and inserted all {len(df)} rows into pgvector!")
cur.close()
conn.close()
