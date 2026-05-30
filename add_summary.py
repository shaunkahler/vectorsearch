import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

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

print("Adding summary column to companies table...")
cur.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS summary TEXT;")

print("Loading CSV...")
df = pd.read_csv('combined_data.csv')
# The IDs in the database are strictly sequential from 1 to 21800, matching the CSV index.
df['id'] = df.index + 1 

print("Updating database with summaries...")
update_query = "UPDATE companies SET summary = %s WHERE id = %s;"

data_to_update = [
    (str(row['Summary']) if not pd.isna(row['Summary']) else "", row['id'])
    for _, row in df.iterrows()
]

execute_batch(cur, update_query, data_to_update, page_size=1000)

print("Successfully added summaries to the database!")
cur.close()
conn.close()
