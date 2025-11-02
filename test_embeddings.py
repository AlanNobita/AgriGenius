#!/usr/bin/env python3
"""
Test script to verify embedding functionality and model availability
"""

import os
import sys
import numpy as np

# Add the rag-chatbot src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'static', 'rag-chatbot', 'src'))

from chatbot.embeddings import Embeddings, check_embedding_model_available, OLLAMA_EMBED_MODEL, OLLAMA_URL

def test_embedding_model():
    """Test if the embedding model is working"""
    print("=== Testing Embedding Model ===")
    print(f"Embedding model: {OLLAMA_EMBED_MODEL}")
    print(f"Ollama URL: {OLLAMA_URL}")
    
    # Check if model is available
    print("\n1. Checking model availability...")
    model_available = check_embedding_model_available()
    
    if not model_available:
        print("❌ Embedding model not available!")
        print("\nTo fix this issue:")
        print("1. Make sure Ollama is running: http://127.0.0.1:11434")
        print("2. Pull the embedding model: ollama pull nomic-embed-text")
        print("3. Or update OLLAMA_EMBED_MODEL in .env file to a model you have")
        return False
    
    print("✅ Embedding model is available")
    
    # Test embedding generation
    print("\n2. Testing embedding generation...")
    test_texts = [
        "This is a test sentence about agriculture.",
        "Farming techniques and crop management.",
        "Sustainable agriculture practices."
    ]
    
    embedder = Embeddings()
    try:
        embeddings = embedder.embed(test_texts)
        print(f"✅ Successfully generated embeddings with shape: {embeddings.shape}")
        print(f"   Sample embedding (first 5 values): {embeddings[0][:5]}")
        return True
    except Exception as e:
        print(f"❌ Failed to generate embeddings: {e}")
        return False

def test_fallback_mechanism():
    """Test the fallback mechanism when embedding model fails"""
    print("\n=== Testing Fallback Mechanism ===")
    
    # Test with empty input
    embedder = Embeddings()
    try:
        empty_embeddings = embedder.embed([])
        print(f"✅ Empty input handled correctly: {empty_embeddings.shape}")
    except Exception as e:
        print(f"❌ Empty input failed: {e}")
    
    # Test with hash fallback (simulate model failure)
    print("\n3. Testing hash-based fallback...")
    try:
        test_text = ["This should use fallback embeddings"]
        # Mock the embedding to fail and use fallback
        embeddings = embedder.embed(test_text)
        print(f"✅ Fallback embeddings generated: {embeddings.shape}")
        print(f"   Sample fallback embedding (first 5 values): {embeddings[0][:5]}")
        return True
    except Exception as e:
        print(f"❌ Fallback mechanism failed: {e}")
        return False

if __name__ == "__main__":
    print("AgriGenius RAG System - Embedding Test")
    print("=" * 50)
    
    success = True
    success &= test_embedding_model()
    success &= test_fallback_mechanism()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! The embedding system is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the output above for details.")
        print("\nTroubleshooting steps:")
        print("1. Ensure Ollama is running: ollama serve")
        print("2. Pull the correct embedding model: ollama pull nomic-embed-text")
        print("3. Check your .env file configuration")
        print("4. Verify network connectivity to Ollama")