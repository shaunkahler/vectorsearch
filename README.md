# StartupDB: Vector Search for Companies

StartupDB is a full-stack application that provides semantic search capabilities over startup and company data. By leveraging natural language processing and vector embeddings, it allows users to search for companies based on descriptions, technologies, and summaries, moving beyond simple keyword matching. 

## Features

- **Semantic Search**: Powered by `sentence-transformers` using the robust **`BAAI/bge-large-en-v1.5`** model. This provides highly accurate, 1024-dimensional context-aware embeddings to understand the deep semantics of your startup search queries. (A smaller script `build_pgvector.py` using `all-MiniLM-L6-v2` is also provided for quicker 384-dimensional testing).
- **Hardware Acceleration**: Automatically detects and utilizes local GPU acceleration via **PyTorch / CUDA** for blazing-fast embedding generation and real-time query encoding, smoothly falling back to CPU if no GPU is present.
- **Vector Database**: Utilizes **PostgreSQL** with the `pgvector` extension for efficient and scalable similarity search.
- **RESTful API**: Fast and robust backend built with **FastAPI**.
- **Interactive UI**: Modern frontend built with **React** and **Vite** for a seamless user experience.
- **Data Filtering**: Combine semantic search with hard filters like funding amount and company status.

## Tech Stack

- **Backend**: Python, FastAPI, SentenceTransformers, Pandas
- **AI / Embeddings**: `BAAI/bge-large-en-v1.5` (via Hugging Face), utilizing **PyTorch and CUDA** for local GPU inference.
- **Database**: PostgreSQL, `pgvector`, Docker
- **Frontend**: React, Vite, Node.js

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js & npm
- Docker (for PostgreSQL)

### 1. Database Setup
Start a PostgreSQL container with `pgvector` enabled (mapped to port 5433 by default in the scripts):
```bash
docker run --name pgvector -e POSTGRES_PASSWORD=mysecretpassword -p 5433:5432 -d pgvector/pgvector:pg16
```

### 2. Backend Setup
Install Python dependencies and load the data into the database:
```bash
pip install -r requirements.txt # (Ensure fastapi, uvicorn, psycopg2-binary, sentence-transformers, pandas are installed)

# Build the vector database and insert data
python build_pgvector_full.py
```

Run the FastAPI backend:
```bash
python api.py
```
The API will be available at `http://localhost:8000`.

### 3. Frontend Setup
Navigate to the `search-ui` directory, install dependencies, and start the development server:
```bash
cd search-ui
npm install
npm run dev
```

## Data Ingestion pipeline

Data ingestion scripts (`build_pgvector.py`, `build_pgvector_full.py`) handle:
1. Connecting to the Postgres instance.
2. Creating tables and enabling the `vector` extension.
3. Loading and cleaning data (funding amounts, employee counts).
4. Generating text embeddings locally using Hugging Face models.
5. Batch inserting embeddings and metadata into PostgreSQL.

## License
MIT License
