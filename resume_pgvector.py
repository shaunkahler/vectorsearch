import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_batch
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import sys
import torch
import os

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

print("Checking table status...")
cur.execute("SELECT COUNT(*) FROM companies")
count = cur.fetchone()[0]
print(f"Already inserted {count} rows")

if count == 0:
    print("Table is empty, need to re-run from scratch.")
    sys.exit(1)

print("Loading CSV data...")
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

df['Total Funding Clean'] = df['Total Funding'].apply(clean_money)
df['Latest Funding Clean'] = df['Latest Funding'].apply(clean_money)
df['Employee Count Clean'] = df['Employee Count'].apply(clean_employees)
df['Year Founded'] = pd.to_numeric(df['Year Founded'], errors='coerce')

df['Text_to_Embed'] = df.apply(lambda row: f"Company Name: {row['Company']}. "
                                           f"Main Products: {row['Main Products'] if not pd.isna(row['Main Products']) else 'Unknown'}. "
                                           f"Summary: {row['Summary'] if not pd.isna(row['Summary']) else ''}. "
                                           f"Tags: {row['Tags'] if not pd.isna(row['Tags']) else ''}. "
                                           f"Technologies used: {row['Technology Used'] if not pd.isna(row['Technology Used']) else 'Unknown'}.", 
                               axis=1)

# WE WILL PROCESS FROM COUNT TO THE END
df_subset = df.iloc[count:]

if len(df_subset) == 0:
    print("All rows already processed!")
    sys.exit(0)

print(f"Loading model... remaining rows to process: {len(df_subset)}")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer('BAAI/bge-large-en-v1.5', device=device)

print("Generating embeddings...")
embeddings = model.encode(df_subset['Text_to_Embed'].tolist(), show_progress_bar=True, batch_size=128)

print("Batch inserting data into PostgreSQL...")
insert_query = """
    INSERT INTO companies 
    (company_name, stage, year_founded, hq, latest_funding, total_funding, employee_count, status, links, embedding)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""

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
        embeddings[i].tolist()
    )
    for i, (_, row) in enumerate(df_subset.iterrows())
]

execute_batch(cur, insert_query, data_to_insert, page_size=100)

print("Finished!")
cur.close()
conn.close()