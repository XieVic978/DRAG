# Ask Your Documents

A local RAG web application that accepts batches of PDF, TXT, and CSV files,
indexes their contents with Sentence Transformers and FAISS, and answers
questions with Groq.

## How it works

1. React sends selected files as multipart form data.
2. FastAPI streams each file to `backend/data/uploads`.
3. The loader extracts text and preserves the filename and PDF page.
4. The embedding pipeline splits the text into overlapping chunks.
5. New vectors and metadata are appended to the persisted FAISS index.
6. A SQLite registry tracks uploaded documents and their processing status.
7. Search retrieves the closest chunks and asks Groq to answer only from them.

## Tech Stack

| Layer | Tech |
| --- | --- |
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI, Uvicorn, Pydantic |
| RAG pipeline | LangChain document loaders and text splitters |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Vector search | FAISS |
| LLM | Groq through `langchain-groq` |
| Data storage | SQLite, local file storage, persisted FAISS metadata |
| Document processing | PyPDF, TXT, and CSV loaders |

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

Install frontend dependencies:

```bash
npm install
```

Copy the environment template and add your Groq key:

```bash
cp .env.example .env
```

## Run the application

Start FastAPI in the first terminal:

```bash
source .venv/bin/activate
python app.py
```

Start React in a second terminal:

```bash
npm run dev
```

Open `http://localhost:5173`.

The first backend start may download `all-MiniLM-L6-v2` from Hugging Face.

## API

- `POST /api/documents` uploads and indexes up to 50 files per request.
- `GET /api/documents` lists registered documents and the indexed chunk count.
- `DELETE /api/documents/{document_id}` removes a file and its vectors.
- `POST /api/search` answers a question and returns retrieved sources.

Uploads accept PDF, TXT, and CSV files up to 20 MB each. Repeated upload batches
let the library grow over time; the limit is per request, not the whole library.

## Local data

The application stores runtime data in:

- `backend/data/uploads/` for original uploads
- `backend/data/documents.sqlite3` for the document registry
- `faiss_store/faiss.index` for vectors
- `faiss_store/metadata.pkl` for chunk text and source metadata

Run a single FastAPI worker with this local FAISS architecture. A production
multi-worker deployment should use shared object storage, a job queue, and a
network-accessible vector database.
