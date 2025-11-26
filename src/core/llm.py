"""LLM Client - Wrapper for OpenAI-compatible APIs."""
import os
import json
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# === Singleton Logger ===
_LOGGER = None

def setup_logger(path: str):
    global _LOGGER
    _LOGGER = LLMLogger(path)
    return _LOGGER

def get_logger():
    global _LOGGER
    return _LOGGER or LLMLogger()


class LLMLogger:
    """Logs LLM requests/responses to JSONL."""
    
    def __init__(self, path: str = None):
        if path:
            self.log_file = Path(path)
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            Path("logs").mkdir(exist_ok=True)
            self.log_file = Path("logs") / f"llm_{datetime.now():%Y%m%d_%H%M%S}.jsonl"

    def log(self, req: Dict, resp: Dict, ms: float):
        entry = {"ts": datetime.now().isoformat(), "ms": round(ms, 2), "req": req, "resp": self._clean(resp)}
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _clean(self, resp: Dict) -> Dict:
        if "error" in resp:
            return resp
        try:
            msg = resp["choices"][0]["message"]
            cleaned = {
                "content": msg.get("content"),
                "tool_calls": [{"name": t["function"]["name"], "args": t["function"]["arguments"]} 
                               for t in msg.get("tool_calls", [])] if msg.get("tool_calls") else None,
                "usage": resp.get("usage")
            }
            # Capture reasoning from thinking models
            if msg.get("reasoning_content"):
                cleaned["reasoning"] = msg.get("reasoning_content")
            return cleaned
        except:
            return {"raw": str(resp)[:200]}


class LLMClient:
    """Client for LLM API calls with tool support."""
    
    def __init__(self):
        self.base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
        self.model = os.getenv("LLM_MODEL", "qwen/qwen3-4b-2507")
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "8192"))
        self.logger = get_logger()
        
        # Set parameters based on thinking mode
        self.is_thinking = "thinking" in self.model.lower()
        if self.is_thinking:
            self.temperature = 0.6
            self.top_p = 0.95
            self.top_k = 20
            self.min_p = 0.0
        else:
            self.temperature = 0.7
            self.top_p = 0.8
            self.top_k = 20
            self.min_p = 0.0

    def _call(self, payload: Dict) -> Dict:
        """Make API call with logging."""
        start = time.time()
        try:
            resp = requests.post(f"{self.base_url}/chat/completions", json=payload, timeout=120)
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            result = {"error": str(e)}
        self.logger.log(payload, result, (time.time() - start) * 1000)
        return result

    def chat(self, messages: List[Dict], tools: List = None) -> Dict:
        """Raw chat completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "min_p": self.min_p,
            "max_tokens": self.max_tokens,
            "stream": False
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return self._call(payload)

    def chat_with_tools(self, system: str, user: str, tools: List[Dict]) -> Dict:
        """Chat with tool calling."""
        resp = self.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], tools)
        if "error" in resp:
            return {"type": "error", "message": resp["error"]}
        try:
            msg = resp["choices"][0]["message"]
            if msg.get("tool_calls"):
                return {"type": "tool_calls", "calls": [
                    {"tool": tc["function"]["name"], "arguments": json.loads(tc["function"]["arguments"])}
                    for tc in msg["tool_calls"]
                ]}
            return {"type": "text", "content": msg.get("content", "")}
        except Exception as e:
            return {"type": "error", "message": str(e)}

    def chat_json(self, system: str, user: str, schema: Dict = None) -> Dict:
        """Request JSON response. Schema is included in prompt for guidance."""
        hint = ""
        if schema:
            hint = f"\nExpected JSON schema: {json.dumps(schema)}"
        messages = [{"role": "system", "content": system + hint + "\nRespond ONLY with valid JSON, no markdown."}, 
                    {"role": "user", "content": user}]
        payload = {"model": self.model, "messages": messages, "temperature": self.temperature,
                   "max_tokens": self.max_tokens}
        
        resp = self._call(payload)
        if "error" in resp:
            return {"type": "error", "message": resp["error"]}
        try:
            content = resp["choices"][0]["message"]["content"]
            if "```" in content:
                content = content.split("```")[1].split("```")[0].replace("json", "", 1)
            return {"type": "json", "data": json.loads(content.strip())}
        except Exception as e:
            return {"type": "error", "message": str(e)}
