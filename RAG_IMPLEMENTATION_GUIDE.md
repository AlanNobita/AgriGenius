# 🚀 AgriGenius RAG System Implementation Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [System Components](#system-components)
4. [Setup and Installation](#setup-and-installation)
5. [Running the RAG System](#running-the-rag-system)
6. [Integration with Chat Interface](#integration-with-chat-interface)
7. [Document Management](#document-management)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## 🎯 Overview

AgriGenius implements a sophisticated **Retrieval-Augmented Generation (RAG)** system that combines the power of large language models with domain-specific agricultural knowledge. The RAG system enables the AI assistant to provide accurate, context-aware responses by retrieving relevant information from a curated knowledge base before generating answers.

### Key Features:
- **Hybrid Search**: Combines semantic search (embeddings) with lexical search (TF-IDF)
- **Document Processing**: Automatic PDF text extraction and chunking
- **Persistent Storage**: Document embeddings stored locally for fast retrieval
- **Real-time Integration**: Seamlessly integrated with the main chat interface
- **Agricultural Focus**: Specialized for farming and agricultural queries

---

## 🏗️ Architecture

### High-Level Architecture:
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Interface│    │   Flask Backend  │    │   RAG System    │
│   (Chat UI)     │◄──►│   (app.py)       │◄──►│   (rag-chatbot) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Database      │    │   Document      │
                       │   (SQLite)      │    │   Storage       │
                       └─────────────────┘    └─────────────────┘
```

### Data Flow:
1. **User Query** → Chat Interface
2. **Query Processing** → Flask Backend (`/api/chat`)
3. **RAG Retrieval** → Hybrid Search System
4. **Context Building** → System Prompt Construction
5. **Response Generation** → LLM (Ollama/OpenRouter)
6. **Response Display** → Chat Interface

---

## 🔧 System Components

### 1. Core RAG Components

#### **RAG Engine** (`static/rag-chatbot/src/chatbot/rag.py`)
- **Purpose**: Main RAG orchestration
- **Key Functions**:
  - `generate_answer(query, top_k=4)`: Main entry point
  - `build_prompt(query, contexts)`: Constructs system prompt with retrieved context
  - **Integration**: Uses Ollama for local LLM inference

#### **Hybrid Retriever** (`static/rag-chatbot/src/chatbot/hybrid_retriever.py`)
- **Purpose**: Combines semantic and lexical search
- **Key Features**:
  - **Semantic Search**: Uses embeddings for meaning-based retrieval
  - **Lexical Search**: Uses TF-IDF for keyword-based matching
  - **Hybrid Scoring**: Weighted combination (60% semantic, 40% lexical)
  - **Persistent Storage**: Documents stored in JSON format

#### **Embeddings Engine** (`static/rag-chatbot/src/chatbot/embeddings.py`)
- **Purpose**: Generates text embeddings for semantic search
- **Fallback Strategy**:
  1. **Primary**: Ollama embeddings (local)
  2. **Secondary**: SentenceTransformers (local)
  3. **Tertiary**: Hash-based deterministic embeddings

#### **Document Processing** (`static/rag-chatbot/src/api/routes.py`)
- **Purpose**: Handles document upload and processing
- **Features**:
  - PDF text extraction using PyPDF2
  - Automatic chunking (1000 chars, 200 char overlap)
  - Document ingestion into RAG system

### 2. Backend Integration

#### **Main Application** (`app.py`)
- **RAG Integration Points**:
  - Lines 985-986: RAG response generation
  - Lines 1100-1172: System prompt construction with context
  - Lines 959-977: AI response orchestration

#### **RAG Integration Module** (`rag_integration.py`)
- **Purpose**: Bridge between main app and RAG system
- **Key Function**: `get_rag_response(query)`
- **Error Handling**: Graceful fallback on RAG failures

### 3. Frontend Integration

#### **Chat Interface** (`templates/chat.html`)
- **Features**:
  - Real-time chat with typing indicators
  - Document upload capability
  - Conversation history management
  - Mobile-responsive design

#### **JavaScript Chat Handler** (`static/js/chat.js`)
- **Key Features**:
  - Async message handling
  - File upload integration
  - Conversation persistence
  - Error handling and user feedback

---

## 🛠️ Setup and Installation

### Prerequisites

#### System Requirements:
- **Python**: 3.8+
- **Memory**: 4GB+ RAM (8GB recommended)
- **Storage**: 1GB+ for documents and embeddings
- **Network**: Internet connection for initial setup

#### Required Software:
- **Ollama**: For local LLM inference
- **Git**: For code management
- **Python Virtual Environment**: Recommended

### Step-by-Step Installation

#### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd AgriGenius

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Install Ollama (Local LLM)
```bash
# Install Ollama (follow instructions for your OS)
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.ai/install.sh | sh
# Windows: Download from https://ollama.ai/download

# Pull the recommended model
ollama pull mistral
```

#### 3. Initialize Database
```bash
# Initialize the main database
python init_db.py

# Initialize RAG system
python init_rag.py
```

#### 4. Configure Environment Variables
Create a `.env` file in the project root:
```env
# OpenRouter API (Optional - for cloud LLM)
OPENROUTER_API_KEY=your-openrouter-api-key-here
OPENROUTER_MODEL=meta-llama/llama-4-maverick:free

# Ollama Configuration
OLLAMA_MODEL=mistral

# RAG System Configuration
RAG_SYSTEM_PROMPT=You are an assistant that uses supplied documents to answer.
```

---

## 🚀 Running the RAG System

### Method 1: Quick Start
```bash
# Activate virtual environment
source venv/bin/activate

# Run the application
python app.py
```

### Method 2: Production Setup
```bash
# Install Gunicorn for production
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Access Points
- **Main Application**: http://localhost:5000
- **Chat Interface**: http://localhost:5000/chat
- **API Documentation**: http://localhost:5000/api/conversations

---

## 🔗 Integration with Chat Interface

### How RAG Works in Chat

#### 1. User Query Processing
```
User: "What are the best practices for tomato cultivation?"
↓
Chat Interface → /api/chat endpoint
```

#### 2. RAG Retrieval
```python
# In app.py line 985-986
from rag_integration import generate_answer
rag_response, contexts = generate_answer(user_input)
```

#### 3. Context Integration
```python
# System prompt construction (app.py lines 1100-1172)
system_prompt = build_system_prompt(sensor_data, user_memory, contexts)
```

#### 4. Response Generation
```python
# Combined with conversation history and sensor data
messages = [
    {"role": "system", "content": system_prompt},
    # ... conversation history
    {"role": "user", "content": user_input}
]
```

### Chat Features

#### **Real-time Communication**
- WebSocket-style real-time updates
- Typing indicators
- Message streaming

#### **Document Upload**
- PDF upload directly in chat
- Automatic processing and indexing
- Immediate availability in RAG system

#### **Conversation Management**
- Persistent conversation history
- Multiple concurrent conversations
- Search and filtering

---

## 📄 Document Management

### Supported Formats
- **Primary**: PDF files
- **Future**: Support for DOCX, TXT, MD planned

### Document Processing Pipeline

#### 1. Upload
```bash
# Via web interface: /chat page
# Or via API: POST /api/upload_pdf
```

#### 2. Text Extraction
```python
# From static/rag-chatbot/src/api/routes.py
def extract_text_from_pdf(path: str) -> str:
    texts = []
    reader = PdfReader(path)
    for p in reader.pages:
        texts.append(p.extract_text() or "")
    return "\n".join(texts)
```

#### 3. Chunking
```python
# Text chunking with overlap
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    chunks = []
    i = 0
    L = len(text)
    while i < L:
        chunk = text[i: i + chunk_size]
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks
```

#### 4. Indexing
```python
# Add to RAG system
docs = []
for i, ch in enumerate(chunks):
    docs.append({
        'id': f"{filename}__{i}",
        'text': ch,
        'meta': {'source': filename}
    })
retriever.add_documents(docs)
```

### Document Storage Structure
```
static/rag-chatbot/data/
├── pdfs/                    # Original PDF files
│   ├── 5583eefd5682_model feed.pdf
├── indices/                 # Processed documents
│   └── documents.json       # Document metadata and chunks
```

---

## 🔍 Troubleshooting

### Common Issues and Solutions

#### 1. RAG System Not Loading
**Problem**: RAG responses not working
```bash
# Check if Ollama is running
ollama list

# Restart Ollama service
sudo systemctl restart ollama

# Re-initialize RAG system
python init_rag.py
```

#### 2. Document Upload Failing
**Problem**: PDF upload not processing
```bash
# Check file permissions
ls -la static/rag-chatbot/data/pdfs/

# Ensure directory exists
mkdir -p static/rag-chatbot/data/pdfs/

# Check disk space
df -h
```

#### 3. Slow Performance
**Problem**: RAG responses are slow
```bash
# Check system resources
htop

# Reduce document complexity
# Lower top_k parameter in generate_answer(query, top_k=2)

# Consider using smaller embeddings model
export OLLAMA_MODEL=llama3.2-1b-instruct
```

#### 4. Error Messages
**Problem**: "RAG integration failed"
```python
# Check logs
tail -f flask.log

# Test RAG system independently
python -c "
from rag_integration import get_rag_response
response, contexts = get_rag_response('test query')
print(response)
"
```

### Performance Optimization

#### 1. Embedding Caching
- Pre-compute embeddings for common queries
- Cache frequently accessed documents

#### 2. Search Optimization
- Adjust `alpha` parameter in hybrid search
- Use smaller `top_k` values for faster responses

#### 3. System Resources
- Monitor memory usage during document processing
- Consider batch processing for large documents

---

## 🎯 Best Practices

### Document Management

#### **Quality Guidelines**
- Use clear, well-structured documents
- Ensure text is extractable (avoid scanned images)
- Keep documents focused on specific topics

#### **File Organization**
- Use descriptive filenames
- Organize by categories (crops, techniques, equipment)
- Regular cleanup of outdated documents

### RAG Configuration

#### **Optimal Settings**
```python
# Hybrid search balance (semantic vs lexical)
alpha = 0.6  # 60% semantic, 40% lexical

# Number of retrieved documents
top_k = 4    # Good balance of relevance and speed

# Document chunking
chunk_size = 1000    # Characters
overlap = 200        # Characters
```

#### **Prompt Engineering**
- Provide clear context in system prompts
- Include relevant sensor data and user memory
- Cite sources properly for transparency

### Security and Privacy

#### **Data Protection**
- Documents are stored locally
- No external document processing
- User conversations remain private

#### **Access Control**
- Document upload requires authentication
- Admin verification for sensitive content
- Regular access reviews

### Monitoring and Maintenance

#### **Regular Tasks**
- Monitor document storage usage
- Update LLM models periodically
- Review system performance metrics

#### **Error Handling**
- Implement comprehensive logging
- Set up alerts for system failures
- Maintain backup of document indices

---

## 🎉 Success Criteria

### Working RAG System Checklist
- [ ] Documents can be uploaded via web interface
- [ ] Chat responses include relevant document context
- [ ] Search results are accurate and relevant
- [ ] System performs within acceptable time limits
- [ ] Error handling works gracefully
- [ ] Mobile interface functions properly

### Testing Your Implementation

#### 1. Document Upload Test
1. Navigate to `/chat`
2. Upload a PDF document
3. Verify processing message appears
4. Check document appears in RAG system

#### 2. Chat Integration Test
1. Ask a question related to uploaded document content
2. Verify response includes document references
3. Check response accuracy and relevance

#### 3. Performance Test
1. Upload multiple documents
2. Test various query types
3. Measure response times
4. Monitor system resource usage

---

## 📞 Support and Resources

### Documentation
- **Main README**: [`README.md`](README.md)
- **Quick Start**: [`QUICK_START_GUIDE.md`](QUICK_START_GUIDE.md)
- **Troubleshooting**: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)

### Community and Support
- **Issues**: Report bugs and request features
- **Discussions**: Share implementation tips
- **Updates**: Follow project developments

### Additional Resources
- **Ollama Documentation**: https://github.com/ollama/ollama
- **SentenceTransformers**: https://www.sbert.net/
- **Flask Documentation**: https://flask.palletsprojects.com/

---

**🌱 Happy Farming with AgriGenius AI!**

This comprehensive RAG system implementation empowers farmers with intelligent, context-aware agricultural assistance. By following this guide, you'll have a fully functional RAG system integrated into your chat interface, ready to provide valuable agricultural insights based on your specific knowledge base.