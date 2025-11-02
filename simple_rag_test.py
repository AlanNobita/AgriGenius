#!/usr/bin/env python3
"""
Simple test script to verify RAG system functionality without external dependencies
"""

import os
import sys
import json

# Add the rag-chatbot src directory to Python path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'static', 'rag-chatbot', 'src')
if SRC not in sys.path:
    sys.path.append(SRC)

def create_test_documents():
    """Create some test documents for testing"""
    test_docs = [
        {
            'id': 'doc1',
            'text': 'Agriculture is the practice of cultivating plants and livestock. Modern agriculture includes sustainable practices to ensure food security for growing populations.',
            'meta': {'source': 'test_agriculture.txt'}
        },
        {
            'id': 'doc2', 
            'text': 'Crop rotation is a farming practice where different types of crops are grown in the same area in sequential seasons. This helps improve soil fertility and reduce pest buildup.',
            'meta': {'source': 'test_crop_rotation.txt'}
        },
        {
            'id': 'doc3',
            'text': 'Organic farming avoids the use of synthetic pesticides and fertilizers. It relies on natural processes to maintain soil health and crop productivity.',
            'meta': {'source': 'test_organic_farming.txt'}
        }
    ]
    return test_docs

def test_document_storage():
    """Test document storage functionality"""
    try:
        print("Testing document storage...")
        
        # Test document creation
        test_docs = create_test_documents()
        print(f"✓ Created {len(test_docs)} test documents")
        
        # Test JSON serialization
        json_str = json.dumps(test_docs, ensure_ascii=False, indent=2)
        parsed_docs = json.loads(json_str)
        print(f"✓ JSON serialization successful")
        
        # Test document saving
        data_dir = os.path.join(SRC, '..', '..', 'data')
        indices_dir = os.path.join(data_dir, 'indices')
        os.makedirs(indices_dir, exist_ok=True)
        
        doc_store = os.path.join(indices_dir, 'documents.json')
        with open(doc_store, 'w', encoding='utf-8') as f:
            json.dump(parsed_docs, f, ensure_ascii=False, indent=2)
        print(f"✓ Documents saved to {doc_store}")
        
        # Test document loading
        with open(doc_store, 'r', encoding='utf-8') as f:
            loaded_docs = json.load(f)
        print(f"✓ Documents loaded successfully: {len(loaded_docs)} documents")
        
        return True, loaded_docs
        
    except Exception as e:
        print(f"❌ Document storage test failed: {e}")
        return False, []

def test_basic_functionality():
    """Test basic RAG functionality without external dependencies"""
    try:
        print("\nTesting basic RAG functionality...")
        
        # Test 1: Import basic modules
        print("1. Testing basic imports...")
        try:
            from chatbot.hybrid_retriever import HybridRetriever
            print("✓ HybridRetriever import successful")
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            return False
        
        # Test 2: Initialize retriever with test documents
        print("2. Testing retriever initialization...")
        storage_success, test_docs = test_document_storage()
        if not storage_success:
            print("❌ Cannot proceed without document storage")
            return False
        
        # Create a simple retriever instance
        retriever = HybridRetriever()
        print(f"✓ Retriever created with {len(retriever.documents)} documents")
        
        # Test 3: Test basic document operations
        print("3. Testing document operations...")
        if len(retriever.documents) == 0:
            # Add test documents if none exist
            retriever.add_documents(test_docs)
            print(f"✓ Added {len(test_docs)} test documents")
        
        # Test 4: Test basic search functionality
        print("4. Testing search functionality...")
        query = "agriculture farming"
        results = retriever.hybrid_search(query, top_k=2)
        print(f"✓ Search for '{query}' returned {len(results)} results")
        
        for result in results:
            print(f"  - Document ID: {result['doc']['id']}")
            print(f"  - Score: {result['score']:.4f}")
            print(f"  - Text preview: {result['doc']['text'][:100]}...")
        
        # Test 5: Test different queries
        print("5. Testing different queries...")
        queries = ["crop rotation", "organic farming", "soil health"]
        for q in queries:
            results = retriever.hybrid_search(q, top_k=1)
            print(f"  Query '{q}': {len(results)} results")
        
        print("\n✓ All basic functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling scenarios"""
    try:
        print("\nTesting error handling...")
        
        # Test 1: Empty query
        print("1. Testing empty query...")
        from chatbot.hybrid_retriever import HybridRetriever
        retriever = HybridRetriever()
        
        empty_results = retriever.hybrid_search("", top_k=3)
        print(f"✓ Empty query returned {len(empty_results)} results")
        
        # Test 2: Non-existent documents
        print("2. Testing with no documents...")
        original_docs = retriever.documents[:]
        retriever.documents = []
        
        no_doc_results = retriever.hybrid_search("test", top_k=3)
        print(f"✓ No documents returned {len(no_doc_results)} results")
        
        # Restore documents
        retriever.documents = original_docs
        
        print("✓ Error handling tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Main test function"""
    print("RAG System Test Suite")
    print("=" * 50)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} Test...")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} Test PASSED")
            else:
                print(f"❌ {test_name} Test FAILED")
        except Exception as e:
            print(f"❌ {test_name} Test ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! RAG system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)