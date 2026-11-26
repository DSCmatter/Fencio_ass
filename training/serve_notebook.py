"""Serve the fine-tuned adapter as an OpenAI-compatible endpoint behind cloudflared.

Runs only inside the Colab/Kaggle GPU notebook. The local agent never loads a model.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import threading
import urllib.request
from pathlib import Path

import yaml
from fastapi import FastAPI
from pydantic import BaseModel

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
    urllib.request.urlretrieve(url, binary)
    binary.chmod(0o755)
    return binary


def load_model(base_model: str, adapter: str, load_in_4bit: bool):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    kwargs: dict = {"device_map": {"": 0}, "dtype": torch.float16}
    if load_in_4bit:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    model = AutoModelForCausalLM.from_pretrained(base_model, **kwargs)
    model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return model, tokenizer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/train.yaml")
    parser.add_argument("--adapter", default="checkpoints/qlora-adapter")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    model, tokenizer = load_model(
        config["base_model"], args.adapter, bool(config.get("load_in_4bit", True))
    )
    device = next(model.parameters()).device

    app = FastAPI()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "model": config["base_model"]}

    @app.post("/v1/chat/completions")
    def chat_completion(request: CompletionRequest) -> dict:
        import torch

        prompt = tokenizer.apply_chat_template(
            request.messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(device)
        greedy = request.temperature <= 0
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                do_sample=not greedy,
                temperature=None if greedy else request.temperature,
                pad_token_id=tokenizer.eos_token_id,
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
