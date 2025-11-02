import os
import json
import subprocess
from typing import List, Tuple
import requests
from dotenv import load_dotenv

from .hybrid_retriever import get_retriever

load_dotenv()  # Load environment variables from .env file

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "tinydolphin")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
SYSTEM_PROMPT = os.environ.get("RAG_SYSTEM_PROMPT", "You are an assistant that uses supplied documents to answer.")


def build_prompt(query: str, contexts: List[dict]) -> str:
    ctx_text = "\n\n---\n\n".join([f"Source ({c['id']}):\n{c['text']}" for c in contexts])
    prompt = f"{SYSTEM_PROMPT}\n\nUse the following extracted document snippets to answer the user query. Be concise, cite source ids in brackets.\n\nContext:\n{ctx_text}\n\nUser question: {query}\n\nAnswer:"
    return prompt


def generate_answer(query: str, top_k: int = 4) -> Tuple[str, List[dict]]:
    retriever = get_retriever()
    results = retriever.hybrid_search(query, top_k=top_k * 2)  # Retrieve more to re-rank
    
    # Re-rank results: prioritize longer documents
    results.sort(key=lambda x: len(x['doc']['text']), reverse=True)
    results = results[:top_k]

    contexts = [r["doc"] for r in results]
    prompt = build_prompt(query, contexts)
    # Prefer HTTP API (modern Ollama) with non-streaming for simplicity
    try:
        url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
        resp = requests.post(
            url,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"num_gpu": 0},
            },
            timeout=120,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        print(f"OLLAMA RESPONSE: {data}")
        text = (
            data.get("response")
            or data.get("text")
            or data.get("message", {}).get("content")
            or ""
        )
        return text, contexts
    except Exception as http_err:
        # Fallback to CLI if available
        try:
            proc = subprocess.run(
                ["ollama", "run", OLLAMA_MODEL],
                input=prompt.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore"))
            out = proc.stdout.decode("utf-8", errors="ignore")
            return out.strip(), contexts
        except Exception as cli_err:
            fallback = f"[RAG generation failed: {http_err or cli_err}]"
            fallback += "\n\nContext used:\n" + "\n\n".join([c["text"][:500] for c in contexts])
            return fallback, contexts