"""QLoRA fine-tuning runner. Execute only on a free Colab/Kaggle GPU runtime."""
from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path

import yaml
from datasets import Dataset


def load_yaml(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def build_dataset(tokenizer, path: str) -> Dataset:
    records = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    texts = [
        tokenizer.apply_chat_template(record["messages"], tokenize=False, add_generation_prompt=False)
        for record in records
    ]
    return Dataset.from_dict({"text": texts})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/train.yaml")
    parser.add_argument("--train-file", default="data/processed/train.jsonl")
    parser.add_argument("--output", default="checkpoints/qlora-adapter")
    args = parser.parse_args()

    from unsloth import FastLanguageModel
    from trl import SFTConfig, SFTTrainer

    config = load_yaml(args.config)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=config["base_model"],
        max_seq_length=config["max_seq_length"],
        dtype=None,
        load_in_4bit=bool(config["load_in_4bit"]),
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        lora_dropout=config["lora_dropout"],
        target_modules=config["target_modules"],
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=config["seed"],
    )
    dataset = build_dataset(tokenizer, args.train_file)

    config_kwargs = {
        "output_dir": args.output,
        "per_device_train_batch_size": config["batch_size"],
        "gradient_accumulation_steps": config["gradient_accumulation_steps"],
        "num_train_epochs": config["epochs"],
        "learning_rate": config["learning_rate"],
        "weight_decay": config["weight_decay"],
        "logging_steps": 10,
        "save_steps": config["checkpoint_steps"],
        "save_total_limit": 2,
        "report_to": [],
        "seed": config["seed"],
        "optim": "adamw_torch",
        "fp16": True,
    }
    sft_params = inspect.signature(SFTConfig).parameters
    if "warmup_ratio" in sft_params:
        config_kwargs["warmup_ratio"] = config["warmup_ratio"]
    elif "warmup_steps" in sft_params:
        config_kwargs["warmup_steps"] = config["warmup_ratio"]
    if "max_length" in sft_params:
        config_kwargs["max_length"] = config["max_seq_length"]
    elif "max_seq_length" in sft_params:
        config_kwargs["max_seq_length"] = config["max_seq_length"]
    if "dataset_text_field" in sft_params:
        config_kwargs["dataset_text_field"] = "text"
    config_kwargs = {key: value for key, value in config_kwargs.items() if key in sft_params}
    training_args = SFTConfig(**config_kwargs)

    trainer_kwargs = {"model": model, "train_dataset": dataset, "args": training_args}
    signature = inspect.signature(SFTTrainer.__init__)
    if "processing_class" in signature.parameters:
        trainer_kwargs["processing_class"] = tokenizer
    elif "tokenizer" in signature.parameters:
        trainer_kwargs["tokenizer"] = tokenizer
    trainer = SFTTrainer(**trainer_kwargs)
    trainer.train()

    adapter_dir = Path(args.output)
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    print(f"Adapter saved to {adapter_dir}")


if __name__ == "__main__":
    main()
