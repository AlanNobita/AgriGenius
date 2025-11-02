from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
from PyPDF2 import PdfReader

from chatbot.hybrid_retriever import get_retriever
from chatbot.rag import generate_answer

api_bp = Blueprint('api', __name__)


@api_bp.route('/query', methods=['POST'])
def query():
    try:
        data = request.get_json(silent=True) or {}
        user_query = (
            data.get('query')
            or data.get('message')
            or request.form.get('query')
            or request.form.get('message')
            or ''
        )
        if not isinstance(user_query, str) or not user_query.strip():
            return jsonify({'error': 'Query is required', 'received': data}), 400
        
        print(f"Received query via /query endpoint: '{user_query}'")
        answer, contexts = generate_answer(user_query.strip(), top_k=4)
        
        # Ensure consistent response format
        response_data = {
            'response': answer,
            'contexts': contexts,
            'success': True
        }
        
        return jsonify(response_data)
    except Exception as e:
        print(f"Error in /query endpoint: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'success': False
        }), 500


PDF_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'pdfs')
os.makedirs(PDF_DIR, exist_ok=True)


def extract_text_from_pdf(path: str) -> str:
    texts = []
    try:
        reader = PdfReader(path)
        for p in reader.pages:
            try:
                texts.append(p.extract_text() or "")
            except Exception:
                continue
    except Exception as e:
        print("PDF read error:", e)
    return "\n".join(texts)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    if not text:
        return []
    chunks = []
    i = 0
    L = len(text)
    while i < L:
        chunk = text[i: i + chunk_size]
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


@api_bp.route('/api/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'pdf' not in request.files:
        return jsonify({'error': 'no file'}), 400
    f = request.files['pdf']
    if f.filename == '':
        return jsonify({'error': 'empty filename'}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext != '.pdf':
        return jsonify({'error': 'only pdf allowed'}), 400
    fname = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
    path = os.path.join(PDF_DIR, fname)
    f.save(path)
    text = extract_text_from_pdf(path)
    chunks = chunk_text(text)
    docs = []
    for i, ch in enumerate(chunks):
        docs.append({
            'id': f"{fname}__{i}",
            'text': ch,
            'meta': {'source': f.filename}
        })
    retriever = get_retriever()
    retriever.add_documents(docs)
    return jsonify({'status': 'ingested', 'chunks': len(chunks)})


@api_bp.route('/api/chat_rag', methods=['POST'])
def chat_rag():
    try:
        payload = request.get_json(silent=True) or {}
        q = (
            payload.get('query')
            or payload.get('message')
            or request.form.get('query')
            or request.form.get('message')
            or ''
        )
        if not isinstance(q, str) or not q.strip():
            return jsonify({'error': 'empty query', 'received': payload}), 400
        
        print(f"Received query via /api/chat_rag endpoint: '{q}'")
        answer, contexts = generate_answer(q.strip(), top_k=4)
        
        # Ensure consistent response format with /query endpoint
        response_data = {
            'response': answer,  # Use 'response' instead of 'answer' for consistency
            'contexts': contexts,
            'success': True
        }
        
        return jsonify(response_data)
    except Exception as e:
        print(f"Error in /api/chat_rag endpoint: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'success': False
        }), 500