"""Compare the base model and the fine-tuned adapter on response-analysis examples.

Runs only inside the Colab/Kaggle GPU notebook. The local machine never loads a model.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
from pathlib import Path

import yaml

JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def load_yaml(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_examples(path: str) -> list[dict]:
    rows: list[dict] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        messages = record.get("messages", [])
        if len(messages) < 2 or messages[-1].get("role") != "assistant":
            continue
        try:
            gold = json.loads(messages[-1]["content"])
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(gold, dict) or "vulnerable" not in gold:
            continue
        rows.append({"messages": messages[:-1], "gold": gold})
    return rows


def parse_output(text: str) -> dict | None:
    match = JSON_OBJECT.search(text)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def load_model(base_model: str, load_in_4bit: bool):
    import torch
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
    model.eval()
    return model, tokenizer


def generate_batch(model, tokenizer, examples: list[dict], max_new_tokens: int = 256) -> list[dict]:
    import torch

    device = next(model.parameters()).device
    results: list[dict] = []
    for example in examples:
        prompt = tokenizer.apply_chat_template(
            example["messages"], tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(device)
        started = time.perf_counter()
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        elapsed = time.perf_counter() - started
        text = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )
        results.append({"text": text, "prediction": parse_output(text), "latency_s": elapsed})
    return results


def score(examples: list[dict], results: list[dict]) -> dict:
    n = len(examples)
    valid = sum(1 for result in results if result["prediction"] is not None)
    vulnerable_hits = 0
    category_hits = 0
    confidence_error = 0.0
    confidence_n = 0
    for example, result in zip(examples, results):
        prediction = result["prediction"]
        if not prediction:
            continue
        if bool(prediction.get("vulnerable")) == bool(example["gold"].get("vulnerable")):
            vulnerable_hits += 1
        predicted_category = str(prediction.get("category", "")).strip().lower()
        gold_category = str(example["gold"].get("category", "")).strip().lower()
        if predicted_category == gold_category:
            category_hits += 1
        try:
            confidence_error += abs(
                float(prediction.get("confidence", 0.0))
                - float(example["gold"].get("confidence", 0.0))
            )
            confidence_n += 1
        except (TypeError, ValueError):
            pass
    return {
        "examples": n,
        "json_valid": valid,
        "json_valid_rate": valid / n if n else 0.0,
        "vulnerable_accuracy": vulnerable_hits / n if n else 0.0,
        "category_accuracy": category_hits / n if n else 0.0,
        "mean_confidence_error": confidence_error / confidence_n if confidence_n else None,
        "mean_latency_s": sum(result["latency_s"] for result in results) / n if n else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/train.yaml")
    parser.add_argument("--test-file", default="data/processed/test.jsonl")
    parser.add_argument("--adapter", default="checkpoints/qlora-adapter")
    parser.add_argument("--out", "--output", dest="out", default="eval/results/model_eval.json")
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    config = load_yaml(args.config)
    examples = load_examples(args.test_file)
    random.Random(config["seed"]).shuffle(examples)
    examples = examples[: args.limit]
    if not examples:
        raise SystemExit("No response-analysis examples found in the test split")

    model, tokenizer = load_model(config["base_model"], bool(config["load_in_4bit"]))
    print(f"Evaluating base model on {len(examples)} examples", flush=True)
    base_results = generate_batch(model, tokenizer, examples)
    base_score = score(examples, base_results)

    from peft import PeftModel

    model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    print(f"Evaluating tuned adapter on {len(examples)} examples", flush=True)
    tuned_results = generate_batch(model, tokenizer, examples)
    tuned_score = score(examples, tuned_results)

    payload = {
        "base_model": config["base_model"],
        "adapter": args.adapter,
        "test_file": args.test_file,
        "limit": args.limit,
        "seed": config["seed"],
        "base": base_score,
        "tuned": tuned_score,
        "examples": [
            {
                "gold": example["gold"],
                "base": base_results[index],
                "tuned": tuned_results[index],
            }
            for index, example in enumerate(examples)
        ],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"base": base_score, "tuned": tuned_score}, indent=2))
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
