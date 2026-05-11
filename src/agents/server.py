"""Manages a local llama.cpp server subprocess."""

import os
import subprocess
import time
import logging
import urllib.error
import urllib.parse
import urllib.request
from dotenv import load_dotenv
load_dotenv()

class LlamaServer:
    """manages a local llama-server subprocess."""

    def __init__(self):
        model = os.getenv("LLM_MODEL")
        if not model:
            raise RuntimeError("LLM_MODEL must be set")
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
        port = urllib.parse.urlparse(base_url).port or 1234
        self._health_url = f"http://localhost:{port}/health"
        cmd = [
            "llama-server", "-hf", model, "--port", str(port),
            "--ctx-size", "8192",
            "--n-predict", "-1",
            "-ngl", "99",
            "--n-cpu-moe", "10",
            "--batch-size", "1024",
            "--ubatch-size", "512",
            "--flash-attn", "on",
            "--metrics",
            "--jinja",
            "--temp", "1.0",
            "--top-p", "0.95",
            "--top-k", "64",
            "--min-p", "0.01",
            "--log-disable",
            "--repeat-penalty", "1.0",
        ]
        logging.info(f"Starting LlamaServer with command: {' '.join(str(a) for a in cmd)}")
        self._process = subprocess.Popen(cmd)

        # Loads of 26B models can take 60s+ from disk; first-time HF downloads take longer.
        deadline = time.time() + 300
        while time.time() < deadline:
            if self._process.poll() is not None:
                raise RuntimeError(f"llama-server exited during startup with code {self._process.returncode}")
            try:
                urllib.request.urlopen(self._health_url, timeout=1).close()
                return
            except (urllib.error.URLError, urllib.error.HTTPError):
                time.sleep(0.5)
        self._process.terminate()
        raise RuntimeError(f"llama-server did not become healthy in 300s: {self._health_url}")

    def stop(self):
        self._process.terminate()
        self._process.wait()

    def __enter__(self): return self
    def __exit__(self, *_): self.stop()