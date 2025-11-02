import os
import os
import json
import subprocess
import requests
import numpy as np
from typing import List

try:
    from sentence_transformers import SentenceTransformer
    _HAS_ST = True
except Exception:
    _HAS_ST = False

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "tinydolphin")
OLLAMA_EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")


def check_embedding_model_available():
    """Check if the configured embedding model is available in Ollama"""
    try:
        url = f"{OLLAMA_URL.rstrip('/')}/api/tags"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            models = resp.json()
            available_models = [model.get("name") for model in models.get("models", [])]
            if OLLAMA_EMBED_MODEL in available_models:
                print(f"Embedding model '{OLLAMA_EMBED_MODEL}' is available")
                return True
            else:
                print(f"Embedding model '{OLLAMA_EMBED_MODEL}' not found. Available models: {available_models}")
                return False
        else:
            print(f"Failed to check Ollama models: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"Error checking embedding model availability: {e}")
        return False


class Embeddings:
    """Provide text embeddings. Try Ollama CLI first, fall back to SentenceTransformers.

    Methods
    - embed(texts: List[str]) -> np.ndarray
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        if _HAS_ST:
            try:
                self.st_model = SentenceTransformer(model_name)
            except Exception:
                self.st_model = None
        else:
            self.st_model = None

    def _ollama_embed(self, texts: List[str], batch_size: int = 16):
        if not texts:
            return np.zeros((0, 0), dtype=float)
        # Prefer HTTP embeddings API (modern Ollama); fall back to CLI if present
        try:
            url = f"{OLLAMA_URL.rstrip('/')}/api/embeddings"
            vectors = []
            for text in texts:
                resp = requests.post(url, json={"model": OLLAMA_EMBED_MODEL, "prompt": text}, timeout=30)
                if resp.status_code != 200:
                    error_msg = resp.text[:200] if resp.text else f"HTTP {resp.status_code}"
                    print(f"Ollama embedding API error: {error_msg}")
                    raise RuntimeError(f"HTTP {resp.status_code}: {error_msg}")
                j = resp.json()
                emb = j.get("embedding")
                if not emb:
                    # some ollama versions wrap it in data
                    if isinstance(j.get("data"), list) and j["data"] and isinstance(j["data"][0], dict):
                        emb = j["data"][0].get("embedding")
                if not emb:
                    print(f"OLLAMA EMBED RESPONSE: {j}")
                    raise RuntimeError("No embedding field in response")
                vectors.append(emb)
            return np.array(vectors, dtype=float)
        except Exception as http_err:
            print(f"HTTP embedding API failed: {http_err}")
            # Try CLI legacy path
            try:
                proc = subprocess.run(
                    ["ollama", "embed", OLLAMA_EMBED_MODEL, "--stdin", "--json"],
                    input="\n".join(texts).encode("utf-8"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                if proc.returncode != 0:
                    error_msg = proc.stderr.decode("utf-8", errors="ignore")
                    print(f"Ollama CLI embedding error: {error_msg}")
                    raise RuntimeError(error_msg)
                out = proc.stdout.decode("utf-8", errors="ignore").strip()
                embeddings = []
                for line in out.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        j = json.loads(line)
                        if isinstance(j, dict) and "embedding" in j:
                            embeddings.append(j["embedding"])
                        elif isinstance(j, list):
                            embeddings.append(j)
                    except Exception:
                        pass
                if not embeddings:
                    try:
                        j = json.loads(out)
                        if isinstance(j, list) and isinstance(j[0], list):
                            embeddings = j
                    except Exception:
                        pass
                if not embeddings:
                    raise RuntimeError("No valid embeddings found in CLI output")
                return np.array(embeddings, dtype=float)
            except Exception as cli_err:
                print("ollama embed failed:", http_err or cli_err)
                return None

    def _st_embed(self, texts: List[str]):
        if self.st_model is None:
            return None
        try:
            arr = self.st_model.encode(texts, convert_to_numpy=True)
            return np.array(arr, dtype=float)
        except Exception as e:
            print("SentenceTransformers embed failed:", e)
            return None

    def embed(self, texts: List[str], batch_size: int = 16):
        if not texts:
            return np.zeros((0, 256), dtype=float)
            
        print(f"Embedding {len(texts)} texts using model: {OLLAMA_EMBED_MODEL}")
        
        # Try Ollama first
        res = self._ollama_embed(texts, batch_size=batch_size)
        if res is not None and res.size:
            print(f"Successfully generated embeddings with shape: {res.shape}")
            return res
            
        # fallback to local ST
        res = self._st_embed(texts)
        if res is not None and res.size:
            print(f"Successfully generated embeddings with SentenceTransformers, shape: {res.shape}")
            return res
            
        # Last-resort deterministic fallback: hash-based vector
        print("Using hash-based fallback embeddings")
        fallback = []
        for t in texts:
            h = abs(hash(t)) % (10 ** 8)
            vec = [(h >> (i % 32)) / 1e8 for i in range(256)]
            fallback.append(vec)
        return np.array(fallback, dtype=float)