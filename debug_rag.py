#!/usr/bin/env python3
"""
Comprehensive RAG System Debug Script
Measures latency, tests embedding functionality, and identifies performance bottlenecks
"""

import os
import sys
import time
import json
import requests
import numpy as np
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the rag-chatbot src directory to Python path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'static', 'rag-chatbot', 'src')
if SRC not in sys.path:
    sys.path.append(SRC)

# Import RAG modules
from chatbot.rag import generate_answer
from chatbot.hybrid_retriever import get_retriever
from chatbot.embeddings import Embeddings, check_embedding_model_available, OLLAMA_EMBED_MODEL, OLLAMA_URL

def measure_latency(func, *args, **kwargs):
    """Measure execution time of a function"""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time

def test_embedding_performance():
    """Test embedding generation performance"""
    print("=== Embedding Performance Test ===")
    
    embedder = Embeddings()
    test_queries = [
        "agriculture farming techniques",
        "crop rotation benefits",
        "soil health management",
        "organic farming practices",
        "precision agriculture technology"
    ]
    
    # Test single query embedding
    print("\n1. Single query embedding performance:")
    for query in test_queries:
        embedding, latency = measure_latency(embedder.embed, [query])
        print(f"   Query: '{query[:30]}...' - Latency: {latency:.3f}s")
    
    # Test batch embedding performance
    print("\n2. Batch embedding performance:")
    batch_sizes = [1, 3, 5, 10]
    for batch_size in batch_sizes:
        batch_queries = test_queries[:batch_size]
        embeddings, latency = measure_latency(embedder.embed, batch_queries)
        print(f"   Batch size {batch_size}: {latency:.3f}s ({latency/batch_size:.3f}s per query)")
    
    return True

def test_retrieval_performance():
    """Test document retrieval performance"""
    print("\n=== Retrieval Performance Test ===")
    
    # Initialize retriever
    retriever = get_retriever()
    print(f"Loaded {len(retriever.documents)} documents")
    
    if not retriever.documents:
        print("⚠️  No documents found. Adding test documents...")
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
        retriever.add_documents(test_docs)
    
    test_queries = [
        "agriculture farming",
        "crop rotation",
        "soil health",
        "organic farming",
        "sustainable agriculture"
    ]
    
    # Test semantic search
    print("\n1. Semantic search performance:")
    for query in test_queries:
        results, latency = measure_latency(retriever.semantic_scores, query, top_k=3)
        print(f"   Query: '{query}' - Latency: {latency:.3f}s, Results: {len(results)}")
    
    # Test lexical search
    print("\n2. Lexical search performance:")
    for query in test_queries:
        results, latency = measure_latency(retriever.lexical_scores, query, top_k=3)
        print(f"   Query: '{query}' - Latency: {latency:.3f}s, Results: {len(results)}")
    
    # Test hybrid search
    print("\n3. Hybrid search performance:")
    for query in test_queries:
        results, latency = measure_latency(retriever.hybrid_search, query, top_k=3)
        print(f"   Query: '{query}' - Latency: {latency:.3f}s, Results: {len(results)}")
    
    return True

def test_rag_generation_performance():
    """Test RAG answer generation performance"""
    print("\n=== RAG Generation Performance Test ===")
    
    test_queries = [
        "What are the main practices in modern agriculture?",
        "Explain crop rotation and its benefits",
        "How does organic farming differ from conventional farming?",
        "What techniques are used for soil health management?",
        "Describe precision agriculture technologies"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Test RAG generation
        answer, contexts, latency = measure_latency(generate_answer, query, top_k=3)
        print(f"   Total RAG latency: {latency:.3f}s")
        print(f"   Answer length: {len(answer)} characters")
        print(f"   Contexts found: {len(contexts)}")
        
        # Break down the timing components
        retriever = get_retriever()
        
        # Measure retrieval time
        results, retrieval_latency = measure_latency(retriever.hybrid_search, query, top_k=3)
        print(f"   Retrieval latency: {retrieval_latency:.3f}s")
        
        # Calculate estimated generation time
        generation_latency = latency - retrieval_latency
        print(f"   Estimated generation latency: {generation_latency:.3f}s")
        
        # Check if latency exceeds thresholds
        if latency > 5.0:
            print("   ⚠️  WARNING: Total latency exceeds 5 seconds!")
        elif latency > 1.0:
            print("   ⚠️  WARNING: Total latency exceeds 1 second!")
        else:
            print("   ✅ Latency is acceptable")
    
    return True

def test_embedding_model_configuration():
    """Test embedding model configuration and availability"""
    print("\n=== Embedding Model Configuration Test ===")
    
    print(f"Configuration:")
    print(f"   Ollama URL: {OLLAMA_URL}")
    print(f"   Embedding Model: {OLLAMA_EMBED_MODEL}")
    print(f"   Chat Model: {os.environ.get('OLLAMA_MODEL', 'Not set')}")
    
    # Check if Ollama is running
    print("\n1. Testing Ollama connection...")
    try:
        response = requests.get(f"{OLLAMA_URL.rstrip('/')}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json()
            available_models = [model.get("name") for model in models.get("models", [])]
            print(f"   ✅ Ollama is running")
            print(f"   Available models: {available_models}")
            
            if OLLAMA_EMBED_MODEL in available_models:
                print(f"   ✅ Embedding model '{OLLAMA_EMBED_MODEL}' is available")
            else:
                print(f"   ❌ Embedding model '{OLLAMA_EMBED_MODEL}' is NOT available")
                print(f"   Available embedding models: {[m for m in available_models if 'embed' in m.lower()]}")
        else:
            print(f"   ❌ Ollama connection failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Ollama connection error: {e}")
    
    # Test embedding model availability
    print("\n2. Testing embedding model availability...")
    model_available = check_embedding_model_available()
    if model_available:
        print("   ✅ Embedding model is available")
    else:
        print("   ❌ Embedding model is not available")
    
    # Test embedding generation
    print("\n3. Testing embedding generation...")
    embedder = Embeddings()
    test_text = ["This is a test sentence for embedding generation."]
    try:
        embeddings, latency = measure_latency(embedder.embed, test_text)
        print(f"   ✅ Embedding generation successful: {latency:.3f}s")
        print(f"   Embedding shape: {embeddings.shape}")
    except Exception as e:
        print(f"   ❌ Embedding generation failed: {e}")
    
    return model_available

def analyze_embedding_error():
    """Analyze the specific embedding error message"""
    print("\n=== Embedding Error Analysis ===")
    
    # Check for the specific error message in logs
    error_patterns = [
        "input tokens were not marked as outputs",
        "embeddings required but some input tokens were not marked as outputs",
        "overriding"
    ]
    
    print("1. Checking for embedding error patterns...")
    print("   Error patterns to look for:")
    for pattern in error_patterns:
        print(f"   - '{pattern}'")
    
    # Test embedding with verbose logging
    print("\n2. Testing embedding with verbose logging...")
    embedder = Embeddings()
    test_texts = [
        "Test sentence for error analysis.",
        "Another test sentence to check for issues."
    ]
    
    try:
        embeddings = embedder.embed(test_texts)
        print(f"   ✅ Embedding generation successful")
        print(f"   Embedding shape: {embeddings.shape}")
        
        # Check if embeddings are reasonable
        if embeddings is not None and embeddings.size > 0:
            sample_embedding = embeddings[0]
            print(f"   Sample embedding stats:")
            print(f"     - Min value: {np.min(sample_embedding):.6f}")
            print(f"     - Max value: {np.max(sample_embedding):.6f}")
            print(f"     - Mean value: {np.mean(sample_embedding):.6f}")
            print(f"     - Std value: {np.std(sample_embedding):.6f}")
            
            # Check for zero embeddings (indicates fallback)
            if np.all(sample_embedding == 0):
                print("   ⚠️  WARNING: All embedding values are zero (fallback mode)")
            else:
                print("   ✅ Embedding values look reasonable")
        
    except Exception as e:
        print(f"   ❌ Embedding test failed: {e}")
        import traceback
        traceback.print_exc()
    
    return True

def test_rag_quality():
    """Test RAG system quality with sample queries"""
    print("\n=== RAG Quality Test ===")
    
    quality_test_queries = [
        {
            "query": "What are sustainable agriculture practices?",
            "expected_keywords": ["sustainable", "agriculture", "practices"]
        },
        {
            "query": "How does crop rotation improve soil health?",
            "expected_keywords": ["crop", "rotation", "soil", "health"]
        },
        {
            "query": "What are the benefits of organic farming?",
            "expected_keywords": ["organic", "farming", "benefits"]
        },
        {
            "query": "Explain precision agriculture technologies",
            "expected_keywords": ["precision", "agriculture", "technologies"]
        }
    ]
    
    for i, test_case in enumerate(quality_test_queries, 1):
        query = test_case["query"]
        expected_keywords = test_case["expected_keywords"]
        
        print(f"\n{i}. Testing query: '{query}'")
        
        # Generate RAG response
        answer, contexts, latency = measure_latency(generate_answer, query, top_k=3)
        
        print(f"   Latency: {latency:.3f}s")
        print(f"   Answer: {answer[:200]}...")
        print(f"   Contexts found: {len(contexts)}")
        
        # Check answer quality
        answer_lower = answer.lower()
        found_keywords = [kw for kw in expected_keywords if kw.lower() in answer_lower]
        
        keyword_score = len(found_keywords) / len(expected_keywords)
        print(f"   Keyword relevance: {keyword_score:.2f} ({len(found_keywords)}/{len(expected_keywords)})")
        
        if keyword_score >= 0.5:
            print("   ✅ Answer relevance: GOOD")
        elif keyword_score >= 0.3:
            print("   ⚠️  Answer relevance: FAIR")
        else:
            print("   ❌ Answer relevance: POOR")
        
        # Check context relevance
        if contexts:
            context_relevance = sum(1 for ctx in contexts if any(kw.lower() in ctx['text'].lower() for kw in expected_keywords))
            context_score = context_relevance / len(contexts)
            print(f"   Context relevance: {context_score:.2f} ({context_relevance}/{len(contexts)})")
        
        # Check latency
        if latency > 5.0:
            print("   ❌ Latency: TOO SLOW (>5s)")
        elif latency > 1.0:
            print("   ⚠️  Latency: SLOW (>1s)")
        else:
            print("   ✅ Latency: FAST (<1s)")
    
    return True

def generate_performance_report():
    """Generate a comprehensive performance report"""
    print("\n" + "="*60)
    print("RAG SYSTEM PERFORMANCE REPORT")
    print("="*60)
    
    # Test components
    print("\n1. Testing System Components...")
    
    # Check embedding model
    model_available = test_embedding_model_configuration()
    
    # Test embedding performance
    test_embedding_performance()
    
    # Test retrieval performance
    test_retrieval_performance()
    
    # Test RAG generation
    test_rag_generation_performance()
    
    # Test RAG quality
    test_rag_quality()
    
    # Analyze errors
    analyze_embedding_error()
    
    # Generate recommendations
    print("\n" + "="*60)
    print("PERFORMANCE RECOMMENDATIONS")
    print("="*60)
    
    recommendations = []
    
    # Check for common issues
    if not model_available:
        recommendations.append("❌ EMBEDDING MODEL ISSUE:")
        recommendations.append("   - Pull the correct embedding model: ollama pull nomic-embed-text")
        recommendations.append("   - Verify Ollama is running: ollama serve")
        recommendations.append("   - Check .env file configuration")
    
    recommendations.append("\n⚡ LATENCY OPTIMIZATION:")
    recommendations.append("   - Use smaller embedding model (all-minilm instead of nomic-embed-text)")
    recommendations.append("   - Implement query batching for multiple requests")
    recommendations.append("   - Consider using GPU acceleration if available")
    recommendations.append("   - Reduce top_k parameter from 4 to 2-3")
    
    recommendations.append("\n🔍 QUALITY IMPROVEMENTS:")
    recommendations.append("   - Use larger document chunks for better context")
    recommendations.append("   - Implement better re-ranking algorithms")
    recommendations.append("   - Add relevance filtering before final ranking")
    
    recommendations.append("\n📊 MONITORING:")
    recommendations.append("   - Add performance logging to track response times")
    recommendations.append("   - Implement alerts for slow queries (>1s)")
    recommendations.append("   - Monitor embedding generation success rates")
    
    for rec in recommendations:
        print(rec)
    
    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)

def main():
    """Main debug function"""
    print("AgriGenius RAG System - Performance Debug")
    print("="*60)
    
    try:
        generate_performance_report()
        return True
    except Exception as e:
        print(f"\n❌ Debug failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)