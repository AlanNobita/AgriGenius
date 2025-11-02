"""
RAG Integration Module
This module provides the interface between the main application and the RAG chatbot functionality.
"""

import os
import sys

# Add the rag-chatbot src directory to the Python path to import the chatbot module
# This allows the application to find the RAG implementation.
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'static', 'rag-chatbot', 'src')
if SRC not in sys.path:
    sys.path.append(SRC)

from chatbot.rag import generate_answer

def get_rag_response(query: str):
    """
    Get RAG response for a given query.
    
    Args:
        query (str): The user query
        
    Returns:
        tuple: (response, contexts)
    """
    try:
        response, contexts = generate_answer(query, top_k=4)
        return response, contexts
    except Exception as e:
        print(f"RAG integration error: {e}")
        return f"[RAG integration failed: {e}]", []