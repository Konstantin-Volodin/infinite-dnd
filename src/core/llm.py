"""LLM Client - Wrapper for OpenAI-compatible APIs."""

import os
import json
import time
import requests
from typing import List, Dict
from datetime import datetime
from pathlib import Path

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
        entry = {
            "ts": datetime.now().isoformat(),
            "ms": round(ms, 2),
            "req": req,
            "resp": self._clean(resp),
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _clean(self, resp: Dict) -> Dict:
        if "error" in resp:
            return resp
        try:
            msg = resp["choices"][0]["message"]
            cleaned = {
                "content": msg.get("content"),
                "tool_calls": [
                    {"name": t["function"]["name"], "args": t["function"]["arguments"]}
                    for t in msg.get("tool_calls", [])
                ]
                if msg.get("tool_calls")
                else None,
                "usage": resp.get("usage"),
            }
            # Capture reasoning from thinking models
            if msg.get("reasoning_content"):
                cleaned["reasoning"] = msg.get("reasoning_content")
            return cleaned
        except Exception:
            return {"raw": str(resp)[:200]}


class LLMClient:
    """Client for LLM API calls with tool support."""

    def __init__(self):
        self.base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
        self.model = os.getenv("LLM_MODEL", "")
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "-1"))
        self.logger = get_logger()

        # Set parameters based on thinking mode
        self.is_thinking = "thinking" in self.model.lower()
        if self.is_thinking:
            self.temperature = 0.6
            self.top_p = 0.95
        else:
            self.temperature = 0.7
            self.top_p = 0.8

    def _call(self, payload: Dict) -> Dict:
        """Make API call with logging."""
        start = time.time()
        try:
            timeout = 600
            resp = requests.post(
                f"{self.base_url}/chat/completions", json=payload, timeout=timeout
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            result = {"error": str(e)}
        self.logger.log(payload, result, (time.time() - start) * 1000)
        return result

    def chat(
        self, messages: List[Dict], tools: List = None, require_tool: bool = False
    ) -> Dict:
        """Raw chat completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            # "required" forces the model to always call a tool
            # "auto" lets the model choose
            payload["tool_choice"] = "required" if require_tool else "auto"
        return self._call(payload)

    def chat_with_tools(
        self, system: str, user: str, tools: List[Dict], require_tool: bool = False
    ) -> Dict:
        """Chat with tool calling."""
        resp = self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            tools,
            require_tool=require_tool,
        )
        if "error" in resp:
            return {"type": "error", "message": resp["error"]}
        try:
            msg = resp["choices"][0]["message"]
            if msg.get("tool_calls"):
                return {
                    "type": "tool_calls",
                    "calls": [
                        {
                            "tool": tc["function"]["name"],
                            "arguments": json.loads(tc["function"]["arguments"]),
                        }
                        for tc in msg["tool_calls"]
                    ],
                }
            # Fallback: Try to parse XML-style tool calls from content
            content = msg.get("content", "")
            if "<tool_call>" in content:
                calls = self._parse_xml_tool_calls(content)
                if calls:
                    return {"type": "tool_calls", "calls": calls}
            return {"type": "text", "content": content}
        except Exception as e:
            return {"type": "error", "message": str(e)}

    def _parse_xml_tool_calls(self, content: str) -> List[Dict]:
        """Parse XML-style tool calls from model output."""
        import re
        calls = []
        # Pattern: <tool_call>toolname<arg_key>key</arg_key><arg_value>value</arg_value>...</tool_call>
        tool_pattern = r'<tool_call>(.*?)</tool_call>'
        for match in re.finditer(tool_pattern, content, re.DOTALL):
            tool_content = match.group(1)
            # Extract tool name (first text before any tag)
            name_match = re.match(r'([a-z_]+)', tool_content)
            if not name_match:
                continue
            tool_name = name_match.group(1)
            # Extract arguments
            args = {}
            arg_pattern = r'<arg_key>([^<]+)</arg_key><arg_value>([^<]*)</arg_value>'
            for arg_match in re.finditer(arg_pattern, tool_content):
                key = arg_match.group(1).strip()
                value = arg_match.group(2).strip()
                args[key] = value
            calls.append({"tool": tool_name, "arguments": args})
        return calls

    def chat_step(
        self, messages: List[Dict], tools: List[Dict], *, require_tool: bool = False
    ) -> Dict:
        """Single LLM call returning parsed result + raw assistant message for conversation threading."""
        resp = self.chat(messages, tools, require_tool=require_tool)
        if "error" in resp:
            return {"type": "error", "message": resp["error"]}
        try:
            msg = resp["choices"][0]["message"]
            if msg.get("tool_calls"):
                calls = []
                for tc in msg["tool_calls"]:
                    calls.append({
                        "id": tc.get("id", f"call_{len(calls)}"),
                        "tool": tc["function"]["name"],
                        "arguments": json.loads(tc["function"]["arguments"]),
                    })
                return {"type": "tool_calls", "calls": calls, "raw_message": msg}
            content = msg.get("content", "")
            if "<tool_call>" in content:
                parsed = self._parse_xml_tool_calls(content)
                if parsed:
                    # Synthesize raw_message with tool_calls for threading
                    synth_tcs = []
                    for i, p in enumerate(parsed):
                        synth_tcs.append({
                            "id": f"call_{i}",
                            "type": "function",
                            "function": {"name": p["tool"], "arguments": json.dumps(p["arguments"])},
                        })
                    synth_msg = {"role": "assistant", "tool_calls": synth_tcs}
                    calls = [{"id": f"call_{i}", **p} for i, p in enumerate(parsed)]
                    return {"type": "tool_calls", "calls": calls, "raw_message": synth_msg}
            return {"type": "text", "content": content, "raw_message": msg}
        except Exception as e:
            return {"type": "error", "message": str(e)}

    def chat_json(self, system: str, user: str, schema: Dict = None) -> Dict:
        """Request JSON response. Schema is included in prompt for guidance."""
        hint = ""
        if schema:
            hint = f"\nExpected JSON schema: {json.dumps(schema)}"
        messages = [
            {
                "role": "system",
                "content": system
                + hint
                + "\nRespond ONLY with valid JSON, no markdown.",
            },
            {"role": "user", "content": user},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

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
