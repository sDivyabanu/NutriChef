"""Local LLM runtime: manages a llama.cpp `llama-server` subprocess bound to 127.0.0.1.

No remote endpoints. The server is started lazily on the first generation request (or eagerly via
NUTRICHEF_LLM_EAGER=1) and stopped when the API shuts down.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..config import PROJECT_DIR, settings

log = logging.getLogger(__name__)

LLAMA_DIR = PROJECT_DIR / "models" / "llama.cpp"
LLM_DIR = PROJECT_DIR / "models" / "llm"
# Preference order when NUTRICHEF_LLM_PATH is not set (chosen by eval/bench_llm.py results).
PREFERRED_MODELS = ["Qwen3-4B-Instruct-2507-Q4_K_M.gguf", "Llama-3.2-3B-Instruct-Q4_K_M.gguf", "Qwen3-1.7B-Q4_K_M.gguf"]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_model() -> Path | None:
    if settings.llm_path:
        p = Path(settings.llm_path)
        return p if p.exists() else None
    for name in PREFERRED_MODELS:
        p = LLM_DIR / name
        if p.exists():
            return p
    found = sorted(LLM_DIR.glob("*.gguf")) if LLM_DIR.exists() else []
    return found[0] if found else None


def find_server(backend: str | None = None) -> Path | None:
    backend = backend or os.getenv("NUTRICHEF_LLM_BACKEND", "cpu")
    exe = LLAMA_DIR / f"{backend}-x64" / "llama-server.exe"
    if exe.exists():
        return exe
    alt = LLAMA_DIR / f"{backend}-x64" / "llama-server"
    return alt if alt.exists() else None


class LlamaServer:
    def __init__(self, model: Path, backend: str = "cpu", ctx: int | None = None, threads: int | None = None):
        self.model = model
        self.backend = backend
        self.ctx = ctx or settings.llm_ctx
        self.threads = threads or settings.llm_threads
        self.port = _free_port()
        self.proc: subprocess.Popen | None = None
        self.lock = threading.Lock()
        self.started_at: float | None = None
        self.load_seconds: float | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self, timeout: float = 180) -> None:
        exe = find_server(self.backend)
        if not exe:
            raise RuntimeError(f"llama-server not found for backend '{self.backend}' in {LLAMA_DIR}")
        args = [str(exe), "-m", str(self.model), "-c", str(self.ctx), "-t", str(self.threads), "--host", "127.0.0.1",
                "--port", str(self.port), "--no-webui", "-np", "1"]
        if self.backend != "cpu":
            args += ["-ngl", "99"]
        log.info("starting llama-server: %s", " ".join(args))
        t0 = time.perf_counter()
        creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"llama-server exited with code {self.proc.returncode}")
            try:
                with urllib.request.urlopen(self.url + "/health", timeout=2) as r:
                    if json.loads(r.read()).get("status") == "ok":
                        self.load_seconds = time.perf_counter() - t0
                        self.started_at = time.time()
                        return
            except (urllib.error.URLError, ConnectionError, TimeoutError, json.JSONDecodeError):
                pass
            time.sleep(0.5)
        self.stop()
        raise RuntimeError("llama-server did not become healthy in time")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def chat(self, messages: list[dict], schema: dict | None = None, max_tokens: int = 1200, temperature: float = 0.6,
             timeout: float | None = None) -> dict:
        body = {"messages": messages, "max_tokens": max_tokens, "temperature": temperature, "top_p": 0.9,
                "chat_template_kwargs": {"enable_thinking": False}}
        if schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "recipe", "schema": schema}}
        req = urllib.request.Request(self.url + "/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        t0 = time.perf_counter()
        with self.lock, urllib.request.urlopen(req, timeout=timeout or settings.generation_timeout_s) as r:
            data = json.loads(r.read())
        elapsed = time.perf_counter() - t0
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        timings = data.get("timings", {})
        return {"content": content, "seconds": elapsed, "completion_tokens": usage.get("completion_tokens"),
                "prompt_tokens": usage.get("prompt_tokens"), "tokens_per_second": timings.get("predicted_per_second")}


class LLMService:
    """Lazily-started singleton around LlamaServer."""

    def __init__(self) -> None:
        self.server: LlamaServer | None = None
        self.error: str | None = None
        self._lock = threading.Lock()

    def status(self) -> dict:
        model = find_model()
        return {
            "model": model.name if model else None,
            "backend": os.getenv("NUTRICHEF_LLM_BACKEND", "cpu"),
            "server_binary": bool(find_server()),
            "running": bool(self.server and self.server.alive()),
            "load_seconds": round(self.server.load_seconds, 1) if self.server and self.server.load_seconds else None,
            "error": self.error,
        }

    def available(self) -> bool:
        return find_model() is not None and find_server() is not None

    def get(self) -> LlamaServer:
        with self._lock:
            if self.server and self.server.alive():
                return self.server
            model = find_model()
            if not model or not find_server():
                raise RuntimeError("No local LLM installed (run scripts/download_models.py --llm qwen3-4b)")
            try:
                self.server = LlamaServer(model, os.getenv("NUTRICHEF_LLM_BACKEND", "cpu"))
                self.server.start()
                self.error = None
            except Exception as exc:
                self.error = str(exc)
                self.server = None
                raise
            return self.server

    def shutdown(self) -> None:
        if self.server:
            self.server.stop()


llm_service = LLMService()
