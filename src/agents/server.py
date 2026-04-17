"""Manages a local llama.cpp server subprocess."""

import os
import subprocess
import time
import logging
import urllib.error
import urllib.request

class LlamaServer:
    """manages a local llama-server subprocess."""

    _DEFAULT_PORT = 1234
    _DEFAULT_MODEL = "Jackrong/Qwopus3.5-4B-v3-GGUF:Q8_0"

    def __init__(self):
        port = os.getenv("LLM_PORT", str(self._DEFAULT_PORT))
        model = os.getenv("LLM_MODEL", self._DEFAULT_MODEL)
        self._health_url = f"http://localhost:{port}/health"
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

        # wait for the server to become healthy
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                response = urllib.request.urlopen(self._health_url, timeout=1)
                response.close()
                break
            except (urllib.error.URLError, urllib.error.HTTPError):
                time.sleep(0.25)
        else:
            raise RuntimeError(f"llama-server did not become healthy: {self._health_url}")

    def stop(self):
        self._process.terminate()
        self._process.wait()

    def __enter__(self): return self
    def __exit__(self, *_): self.stop()