# Embedding Issues Troubleshooting Guide

## Problem Description

You're seeing the error message:
```
init: embeddings required but some input tokens were not marked as outputs -> overriding
```

This error occurs when the embedding model is not properly configured or available in your Ollama instance.

## Root Causes

1. **Incorrect Model Name**: The embedding model name in your `.env` file doesn't exist in Ollama
2. **Ollama Not Running**: The Ollama service is not started or accessible
3. **Model Not Pulled**: The specified embedding model hasn't been downloaded to your system
4. **Network Issues**: Ollama can't connect to download models

## Solution Steps

### Step 1: Verify Ollama is Running

Check if Ollama is accessible:
```bash
curl http://127.0.0.1:11434/api/tags
```

If you get an error, start Ollama:
```bash
ollama serve
```

### Step 2: Pull the Correct Embedding Model

The recommended embedding model is `nomic-embed-text`. Pull it with:
```bash
ollama pull nomic-embed-text
```

### Step 3: Update Environment Configuration

Ensure your `.env` file has the correct configuration:
```
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_MODEL=tinydolphin
```

### Step 4: Test the Embedding System

Run the test script to verify everything works:
```bash
python test_embeddings.py
```

## Alternative Solutions

### Option A: Use a Different Embedding Model

If `nomic-embed-text` doesn't work, try these alternatives:
```bash
ollama pull all-minilm
ollama pull mxbai-embed-large
```

Then update your `.env` file accordingly:
```
OLLAMA_EMBED_MODEL=all-minilm
```

### Option B: Use SentenceTransformers Fallback

If Ollama embedding models continue to fail, the system will automatically fall back to using SentenceTransformers locally. Make sure you have it installed:
```bash
pip install sentence-transformers
```

### Option C: Use Hash-based Fallback

As a last resort, the system will generate hash-based deterministic embeddings if all other methods fail.

## Testing Your Fix

After making changes, test the embedding functionality:

1. Run the test script:
   ```bash
   python test_embeddings.py
   ```

2. Test the RAG system:
   ```bash
   python -c "
   from static.rag_chatbot.src.chatbot.hybrid_retriever import get_retriever
   retriever = get_retriever()
   results = retriever.hybrid_search('test query', top_k=3)
   print(f'Found {len(results)} results')
   "

3. Upload a test PDF and query it through the web interface.

## Common Error Messages and Solutions

### "No embedding field in response"
- **Cause**: Ollama model doesn't support embeddings or wrong model name
- **Solution**: Pull a correct embedding model like `nomic-embed-text`

### "HTTP 404"
- **Cause**: Ollama service not running or wrong URL
- **Solution**: Start Ollama with `ollama serve`

### "Connection refused"
- **Cause**: Ollama not running on the specified port
- **Solution**: Check Ollama status and start if needed

### Model name not found
- **Cause**: Model not pulled from Ollama registry
- **Solution**: Pull the model with `ollama pull <model-name>`

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama service URL |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model name |
| `OLLAMA_MODEL` | `tinydolphin` | Chat model name |

### Recommended Models

| Model Type | Model Name | Description |
|------------|------------|-------------|
| **Embedding** | `nomic-embed-text` | Recommended for general use |
| **Embedding** | `all-minilm` | Lightweight alternative |
| **Embedding** | `mxbai-embed-large` | High performance |
| **Chat** | `tinydolphin` | Small, fast chat model |
| **Chat** | `mistral` | Balanced performance |

## Getting Help

If you continue to experience issues:

1. Check the [Ollama documentation](https://github.com/ollama/ollama)
2. Verify your system meets the requirements
3. Check the logs for detailed error messages
4. Run the test script to identify specific issues