# AgriGenius RAG Chat Access Guide

This guide helps a new user get the Retrieval-Augmented Generation (RAG) chat working locally and explains how to use it from the website UI.

## 1) Prerequisites

- Python 3.10+ and pip
- Node is NOT required (frontend is template-based)
- Ollama installed and running for text generation
  - Install: https://ollama.com
  - Start server: `ollama serve`
  - Pull a model (default used here is `mistral`): `ollama pull mistral`
- Optional (for embeddings fallback): `sentence-transformers`

Notes:
- If Ollama isn’t available, the system falls back to a graceful text-only message. Embeddings may also fall back to local `sentence-transformers` if available.

## 2) Install and run the web app

1. Create/activate a virtualenv (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables (optional):
   - `OLLAMA_MODEL` (default: `mistral`)
   - `RAG_SYSTEM_PROMPT` (optional custom system prompt)
4. Start the Flask app:
   ```bash
   export FLASK_APP=app.py
   flask run
   ```
   The app will be available at `http://127.0.0.1:5000`.

## 3) Where the RAG routes live

- RAG API is mounted under the `/rag` prefix.
  - Query endpoint: `POST /rag/api/chat_rag` (JSON body: `{ "query": "your question" }`)
  - Upload PDFs: `POST /rag/api/upload_pdf` (multipart form field: `pdf`)

These are provided by the bundled RAG module in `static/rag-chatbot/src/api/routes.py` and mounted by the main Flask app.

## 4) Access the RAG chat page in the UI

1. Open your browser at `http://127.0.0.1:5000/chat`.
2. Type a question in the input box and press Send.
3. The chat will call `POST /rag/api/chat_rag` behind the scenes.
4. The assistant reply will include a compact source list like:
   ```
   Sources: [file1.pdf__0] [file2.pdf__3] ...
   ```

If sources are not shown or a fallback message appears, see Troubleshooting below.

## 5) Add your own documents (improves answers)

Option A: Through the Documents page
- Go to `http://127.0.0.1:5000/documents`.
- Use the upload form to select a PDF.
- On success, you’ll see a confirmation and the document will appear in the list.
- Your PDF is chunked and added to the retriever’s index for future queries.

Option B: Raw API upload
- Send a `multipart/form-data` `POST` request to `/rag/api/upload_pdf` with a `pdf` file field.

Uploaded PDFs are stored under `static/rag-chatbot/data/pdfs/` and chunked into the in-memory store.

## 6) Optional: Pre-warm the RAG indexes

You can initialize and verify embeddings loading with:
```bash
python init_rag.py
```
This loads existing documents, computes embeddings if needed, and prints a short summary.

## 7) Troubleshooting

- No answer or a message like `[RAG generation failed: ...]`:
  - Ensure Ollama server is running: `ollama serve`
  - Ensure the model exists: `ollama pull mistral` (or set `OLLAMA_MODEL`)
  - Check your terminal for errors when you started Flask
- Sources don’t appear:
  - If there are no ingested documents, upload at least one PDF
  - Verify `/rag/api/chat_rag` returns `contexts` with items
- Upload fails:
  - Confirm you are sending a `.pdf` file
  - Check server logs for `PDF read error`
- Slow responses:
  - The first model run can be slower due to model loading
  - Consider smaller PDFs or fewer pages for testing

## 8) Security notes (local/dev)

- The upload endpoint accepts PDFs only, stored beneath `static/rag-chatbot/data/pdfs/`.
- For production, place uploads outside the web root, add auth/limits, and use a persistent vector store.

## 9) Where to look in code

- RAG integration in the app: `rag_integration.py` (simple helper)
- RAG API and ingestion: `static/rag-chatbot/src/api/routes.py`
- Answer generation: `static/rag-chatbot/src/chatbot/rag.py`
- Embeddings: `static/rag-chatbot/src/chatbot/embeddings.py`
- Chat page UI: `templates/chat.html`, `static/js/chat.js`

You’re all set. Start Ollama, run the app, open `/chat`, and ask your questions. Upload PDFs via `/documents` to enrich the RAG knowledge base.
