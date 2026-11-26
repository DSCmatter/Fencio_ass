"""Serve the fine-tuned adapter as an OpenAI-compatible endpoint behind cloudflared.

Runs only inside the Colab/Kaggle GPU notebook. The local agent never loads a model.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import threading
from pathlib import Path

import yaml
from fastapi import FastAPI
from pydantic import BaseModel
from unsloth import FastLanguageModel

TUNNEL_URL = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


class CompletionRequest(BaseModel):
    model: str | None = None
    messages: list[dict]
    temperature: float = 0.4
    max_tokens: int = 1024


def download_cloudflared() -> Path:
    binary = Path("cloudflared")
    if binary.exists():
        return binary
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    import urllib.request

    urllib.request.urlretrieve(url, binary)
    binary.chmod(0o755)
    return binary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/train.yaml")
    parser.add_argument("--adapter", default="checkpoints/qlora-adapter")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=config["base_model"],
        max_seq_length=config["max_seq_length"],
        dtype=None,
        load_in_4bit=True,
    )
    if hasattr(model, "load_adapter"):
        model.load_adapter(args.adapter)
    FastLanguageModel.for_inference(model)

    app = FastAPI()

    @app.post("/v1/chat/completions")
    def chat_completion(request: CompletionRequest) -> dict:
        prompt = tokenizer.apply_chat_template(
            request.messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer([prompt], return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=request.max_tokens,
            temperature=request.temperature,
            do_sample=True,
        )
        text = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
        return {
            "choices": [{"message": {"role": "assistant", "content": text}}],
            "model": config["base_model"] + "+qlora",
        }

    import uvicorn

    server = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": "127.0.0.1", "port": args.port, "log_level": "warning"},
        daemon=True,
    )
    server.start()

    binary = download_cloudflared()
    process = subprocess.Popen(
        [str(binary), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{args.port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert process.stdout is not None
    for line in process.stdout:
        match = TUNNEL_URL.search(line)
        if match:
            url = match.group(0)
            print(f"TUNNEL_URL={url}/v1", flush=True)
            print("Paste this URL into configs/agent.yaml as model.base_url", flush=True)
            break
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()


if __name__ == "__main__":
    main()
