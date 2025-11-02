"""Chatbot package initializer.

This file makes the `static/rag-chatbot/src/chatbot` directory importable as a package.
It can also export commonly used symbols for convenience.
"""
from .embeddings import Embeddings
from .hybrid_retriever import get_retriever
from .rag import generate_answer

__all__ = ["Embeddings", "get_retriever", "generate_answer"]
