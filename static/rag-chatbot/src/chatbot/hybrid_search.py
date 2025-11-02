"""Compatibility proxy for older imports.

This file intentionally provides a very small, stable surface so older
imports that used ``chatbot.hybrid_search`` continue to work. The real
implementation lives in ``hybrid_retriever.py``.
"""

from .hybrid_retriever import HybridRetriever, get_retriever

__all__ = ["HybridRetriever", "get_retriever"]
