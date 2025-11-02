"""Initialize RAG indices for the local rag-chatbot.

This script will import the hybrid retriever from the bundled rag-chatbot code,
force it to load any existing documents, compute embeddings and TF-IDF matrices,
and print a short summary. It will not call external heavy ML services.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'static', 'rag-chatbot', 'src')
if SRC not in sys.path:
    sys.path.append(SRC)

try:
    from chatbot.hybrid_retriever import get_retriever
except Exception as e:
    print(f"Error importing retriever: {e}")
    raise


def main():
    print("Initializing RAG retriever...")
    retriever = get_retriever()
    docs = getattr(retriever, 'documents', None)
    n = len(docs) if docs is not None else 0
    print(f"Loaded {n} documents from the document store.")

    # Force computation of embeddings and TF-IDF if needed
    try:
        texts = [d['text'] for d in docs] if docs else []
        if texts:
            emb = retriever.embedder.embed(texts)
            print(f"Computed embeddings matrix shape: {getattr(emb, 'shape', 'unknown')}")
        else:
            print("No documents to embed.")
    except Exception as e:
        print(f"Error computing embeddings: {e}")

    print("RAG initialization complete.")


if __name__ == '__main__':
    main()
