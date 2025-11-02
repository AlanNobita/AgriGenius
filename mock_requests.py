"""
Mock requests module for testing purposes
"""

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = str(json_data)
    
    def json(self):
        return self.json_data

def post(url, json=None, timeout=None):
    """Mock post function"""
    # Mock Ollama API response
    if "api/generate" in url:
        return MockResponse({
            "response": "This is a mock response from Ollama for testing purposes.",
            "done": True
        })
    elif "api/embeddings" in url:
        return MockResponse({
            "embedding": [0.1] * 256  # Mock 256-dimensional embedding
        })
    
    return MockResponse({"error": "Unknown endpoint"}, 404)

def get(url, timeout=None):
    """Mock get function"""
    return MockResponse({"data": "mock data"})