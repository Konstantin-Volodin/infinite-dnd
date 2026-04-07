# src/llm/server.py
"""Handles the llama.cpp server management."""

import os
import subprocess
import time
import logging

class LlamaServer:
    """manages a local llama-server subprocess."""

    _DEFAULT_PORT = 1234
    _DEFAULT_MODEL = "Jackrong/Qwopus3.5-4B-v3-GGUF:Q8_0"

    def __init__(self):
        port = os.getenv("LLM_PORT", str(self._DEFAULT_PORT))
        model = os.getenv("LLM_MODEL", self._DEFAULT_MODEL)
        cmd = [
            "llama-server", "-hf", model, "--port", port,
            "--ctx-size", "20000",
            "--n-predict", "-1",
            "-ngl", "99",
            "--batch-size", "1024",
            "--ubatch-size", "512",
            "--flash-attn", "on",
            "--log-disable",
            "--metrics",
            "--cache-type-k", "q8_0",
            "--cache-type-v", "q8_0",
        ]
        logging.info(f"Starting LlamaServer with command: {' '.join(str(a) for a in cmd)}")
        self._process = subprocess.Popen(cmd)
        time.sleep(10)

    def stop(self):
        self._process.terminate()
        self._process.wait()

    def __enter__(self): return self
    def __exit__(self, *_): self.stop()