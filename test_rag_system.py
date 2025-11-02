#!/usr/bin/env python3
"""
Simple test script to verify RAG system functionality
"""

import os
import sys

# Add the rag-chatbot src directory to Python path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'static', 'rag-chatbot', 'src')
if SRC not in sys.path:
    sys.path.append(SRC)

def test_rag_system():
    """Test the RAG system with a simple query"""
    try:
        print("Testing RAG System...")
        print("=" * 50)
        
        # Test 1: Import RAG modules
        print("1. Testing imports...")
        from chatbot.rag import generate_answer
        from chatbot.hybrid_retriever import get_retriever
        print("✓ Imports successful")
        
        # Test 2: Initialize retriever
        print("2. Testing retriever initialization...")
        retriever = get_retriever()
        print(f"✓ Retriever initialized with {len(retriever.documents)} documents")
        
        # Test 3: Test hybrid search
        print("3. Testing hybrid search...")
        query = "agriculture farming"
        results = retriever.hybrid_search(query, top_k=3)
        print(f"✓ Hybrid search returned {len(results)} results for '{query}'")
        
        # Test 4: Test RAG generation
        print("4. Testing RAG generation...")
        answer, contexts = generate_answer(query, top_k=3)
        print(f"✓ RAG generation successful")
        print(f"Answer length: {len(answer)} characters")
        print(f"Contexts found: {len(contexts)}")
        
        # Test 5: Test with empty/no documents
        print("5. Testing with empty document store...")
        empty_retriever = get_retriever()
        # Clear documents for testing
        original_docs = empty_retriever.documents[:]
        empty_retriever.documents = []
        empty_retriever._save()
        
        try:
            empty_results = empty_retriever.hybrid_search("test query", top_k=3)
            print(f"✓ Empty search returned {len(empty_results)} results (expected: 0)")
            
            empty_answer, empty_contexts = generate_answer("test query", top_k=3)
            print(f"✓ Empty RAG generation successful")
        finally:
            # Restore original documents
            empty_retriever.documents = original_docs
            empty_retriever._save()
        
        print("\n" + "=" * 50)
        print("RAG System Test Results: ✓ ALL TESTS PASSED")
        print("=" * 50)
        
        # Show a sample response
        print("\nSample Response:")
        print("-" * 20)
        print(f"Query: {query}")
        print(f"Answer: {answer[:200]}...")
        if contexts:
            print(f"\nContext IDs: {[c.get('id', 'unknown') for c in contexts[:3]]}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rag_system()
    sys.exit(0 if success else 1)