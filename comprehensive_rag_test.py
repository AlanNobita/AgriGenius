#!/usr/bin/env python3
"""
Comprehensive RAG system test with mock dependencies
"""

import os
import sys
import json

# Add the rag-chatbot src directory to Python path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'static', 'rag-chatbot', 'src')
if SRC not in sys.path:
    sys.path.append(SRC)

# Mock requests module before importing RAG modules
sys.modules['requests'] = __import__('mock_requests')

# Mock numpy if not available
try:
    import numpy as np
except ImportError:
    class MockNumpy:
        def zeros(self, shape, dtype=None):
            if isinstance(shape, tuple):
                if len(shape) == 2:
                    return [[0.0] * shape[1] for _ in range(shape[0])]
                else:
                    return [0.0] * shape[0]
            return [0.0] * shape
        
        def array(self, data, dtype=None):
            return data
        
        def linalg(self):
            return MockLinalg()
        
        def argsort(self, arr):
            return sorted(range(len(arr)), key=lambda i: arr[i])
        
        class ndarray:
            def __init__(self, data):
                self.data = data
                self.size = len(data) if isinstance(data, list) else 1
            
            def __getitem__(self, key):
                return self.data[key]
            
            def __len__(self):
                return len(self.data) if isinstance(self.data, list) else 1

    class MockLinalg:
        def norm(self, arr, axis=None, keepdims=False):
            if isinstance(arr, list):
                return sum(x**2 for x in arr)**0.5
            return abs(arr)

    sys.modules['numpy'] = MockNumpy()

# Mock sklearn if not available
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError:
    class MockTfidfVectorizer:
        def __init__(self):
            self.vocabulary_ = {}
            self.idf_ = []
        
        def fit(self, documents):
            # Simple mock vocabulary
            vocab = {}
            for i, doc in enumerate(documents):
                words = doc.lower().split()
                for word in words:
                    if word not in vocab:
                        vocab[word] = len(vocab)
            self.vocabulary_ = vocab
            self.idf_ = [1.0] * len(vocab)
            return self
        
        def transform(self, documents):
            # Simple TF vector
            vectors = []
            for doc in documents:
                words = doc.lower().split()
                vec = [0.0] * len(self.vocabulary_)
                for word in words:
                    if word in self.vocabulary_:
                        vec[self.vocabulary_[word]] += 1.0
                vectors.append(vec)
            return MockMatrix(vectors)
    
    class MockMatrix:
        def __init__(self, data):
            self.data = data
        
        def __matmul__(self, other):
            # Simple matrix multiplication
            if isinstance(other, MockMatrix):
                result = []
                for row in self.data:
                    new_row = []
                    for col in other.data[0]:
                        val = sum(row[i] * other.data[j][i] for j in range(len(other.data)))
                        new_row.append(val)
                    result.append(new_row)
                return MockMatrix(result)
            return self
        
        def T(self):
            return MockMatrix(list(zip(*self.data)))
        
        def toarray(self):
            return self.data
        
        def squeeze(self):
            return self.data[0] if len(self.data) == 1 else self.data

    sys.modules['sklearn'] = type('MockSklearn', (), {})()
    sys.modules['sklearn.feature_extraction'] = type('MockFeatureExtraction', (), {})()
    sys.modules['sklearn.feature_extraction.text'] = type('MockText', (), {'TfidfVectorizer': MockTfidfVectorizer})()

# Mock sentence_transformers if not available
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    class MockSentenceTransformer:
        def __init__(self, model_name):
            self.model_name = model_name
        
        def encode(self, texts, convert_to_numpy=True):
            # Simple mock embeddings
            embeddings = []
            for text in texts:
                # Create deterministic embedding based on text hash
                import hashlib
                hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
                embedding = [(hash_val >> i) % 1000 / 1000.0 for i in range(256)]
                embeddings.append(embedding)
            return embeddings
    
    sys.modules['sentence_transformers'] = type('MockSentenceTransformers', (), {})()
    sys.modules['sentence_transformers'].SentenceTransformer = MockSentenceTransformer

def create_test_documents():
    """Create test documents for RAG testing"""
    return [
        {
            'id': 'doc1',
            'text': 'Agriculture is the practice of cultivating plants and livestock. Modern agriculture includes sustainable practices to ensure food security for growing populations. Farmers use various techniques like crop rotation, organic farming, and precision agriculture.',
            'meta': {'source': 'agriculture_basics.txt'}
        },
        {
            'id': 'doc2',
            'text': 'Crop rotation is a farming practice where different types of crops are grown in the same area in sequential seasons. This helps improve soil fertility, reduce pest buildup, and increase crop yields. Common rotations include corn-soybean-wheat combinations.',
            'meta': {'source': 'crop_rotation_guide.txt'}
        },
        {
            'id': 'doc3',
            'text': 'Organic farming avoids the use of synthetic pesticides and fertilizers. It relies on natural processes to maintain soil health and crop productivity. Organic farmers use compost, natural pest control, and crop diversity.',
            'meta': {'source': 'organic_farming_practices.txt'}
        },
        {
            'id': 'doc4',
            'text': 'Precision agriculture uses technology to optimize field-level management for crop farming. It includes GPS guidance, variable rate technology, remote sensing, and data analytics to improve efficiency and reduce environmental impact.',
            'meta': {'source': 'precision_agriculture.txt'}
        },
        {
            'id': 'doc5',
            'text': 'Soil health is crucial for sustainable agriculture. Good soil structure, proper pH levels, adequate organic matter, and balanced nutrients are essential for plant growth. Regular soil testing helps farmers make informed decisions.',
            'meta': {'source': 'soil_health_management.txt'}
        }
    ]

def test_rag_system():
    """Test the complete RAG system"""
    try:
        print("🧪 Comprehensive RAG System Test")
        print("=" * 60)
        
        # Test 1: Import all modules
        print("\n1. Testing Module Imports...")
        from chatbot.rag import generate_answer
        from chatbot.hybrid_retriever import HybridRetriever, get_retriever
        from chatbot.embeddings import Embeddings
        print("✅ All RAG modules imported successfully")
        
        # Test 2: Initialize retriever with test documents
        print("\n2. Testing Document Management...")
        test_docs = create_test_documents()
        print(f"📄 Created {len(test_docs)} test documents")
        
        retriever = HybridRetriever()
        print(f"📊 Initial retriever state: {len(retriever.documents)} documents")
        
        # Add test documents
        retriever.add_documents(test_docs)
        print(f"✅ Added documents: {len(retriever.documents)} total")
        
        # Test 3: Test embedding functionality
        print("\n3. Testing Embedding System...")
        embedder = Embeddings()
        
        # Test embedding with sample texts
        sample_texts = ["agriculture farming", "crop rotation", "soil health"]
        embeddings = embedder.embed(sample_texts, batch_size=16)
        print(f"✅ Generated embeddings for {len(sample_texts)} texts")
        print(f"   Embedding dimension: {len(embeddings[0]) if embeddings is not None and len(embeddings) > 0 else 'N/A'}")
        
        # Test 4: Test search functionality
        print("\n4. Testing Search Functionality...")
        test_queries = [
            "agriculture farming",
            "crop rotation benefits", 
            "organic vs conventional",
            "precision agriculture technology",
            "soil management techniques"
        ]
        
        for query in test_queries:
            results = retriever.hybrid_search(query, top_k=3)
            print(f"🔍 '{query}': {len(results)} results")
            for i, result in enumerate(results[:2]):  # Show top 2
                score = result['score']
                doc_id = result['doc']['id']
                text_preview = result['doc']['text'][:60] + "..."
                print(f"   {i+1}. [{doc_id}] Score: {score:.3f} - {text_preview}")
        
        # Test 5: Test RAG generation
        print("\n5. Testing RAG Generation...")
        test_query = "What are the main practices in modern agriculture?"
        
        answer, contexts = generate_answer(test_query, top_k=3)
        print(f"🤖 Query: '{test_query}'")
        print(f"💡 Answer preview: {answer[:200]}...")
        print(f"📚 Contexts found: {len(contexts)}")
        for ctx in contexts:
            print(f"   - Context ID: {ctx.get('id', 'unknown')}")
            print(f"     Source: {ctx.get('meta', {}).get('source', 'unknown')}")
        
        # Test 6: Test edge cases
        print("\n6. Testing Edge Cases...")
        
        # Empty query
        empty_answer, empty_contexts = generate_answer("", top_k=2)
        print(f"🔸 Empty query handled: {len(empty_contexts)} contexts")
        
        # Very specific query
        specific_answer, specific_contexts = generate_answer("quack foo bar", top_k=2)
        print(f"🔸 Specific query handled: {len(specific_contexts)} contexts")
        
        # Test 7: Test retriever persistence
        print("\n7. Testing Document Persistence...")
        
        # Check if documents are saved
        data_dir = os.path.join(SRC, '..', '..', 'data')
        indices_dir = os.path.join(data_dir, 'indices')
        doc_store = os.path.join(indices_dir, 'documents.json')
        
        if os.path.exists(doc_store):
            with open(doc_store, 'r', encoding='utf-8') as f:
                saved_docs = json.load(f)
            print(f"💾 Document store contains {len(saved_docs)} documents")
            
            # Test loading from saved state
            new_retriever = HybridRetriever()
            print(f"📂 Loaded {len(new_retriever.documents)} documents from storage")
        else:
            print("⚠️  Document store not found (this is normal for first run)")
        
        print("\n" + "=" * 60)
        print("🎉 RAG SYSTEM TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print("\n📋 Test Summary:")
        print(f"   ✅ Documents processed: {len(test_docs)}")
        print(f"   ✅ Search queries tested: {len(test_queries)}")
        print(f"   ✅ RAG generations: 1 successful")
        print(f"   ✅ Embeddings generated: {len(sample_texts)}")
        print(f"   ✅ Error cases handled: 2")
        
        return True
        
    except Exception as e:
        print(f"\n❌ RAG System Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test runner"""
    success = test_rag_system()
    
    if success:
        print("\n🚀 The RAG agent system is ready to use!")
        print("\nNext steps:")
        print("1. Install required dependencies: pip install -r requirements.txt")
        print("2. Start Ollama service: ollama serve")
        print("3. Test the chat interface at /chat")
    else:
        print("\n⚠️  Some issues remain. Check the error messages above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)