# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the fine-tuning module.

## Overview

Qwen2.5-7B fine-tuning using LoRA to train a Russian-language digital secretary "Lydia" for LLC "Shaerware Digital". The model learns the owner's communication style from Telegram chat exports.

## Commands

```bash
cd finetune
source /home/shaerware/qwen-finetune/train_venv/bin/activate

# Prepare dataset from Telegram export
python prepare_dataset.py

# Train LoRA adapters
python train.py

# Merge LoRA into base model (requires ~30GB RAM)
python merge_lora.py

# Quantize to W4A16 (optional)
source /home/shaerware/qwen-finetune/quant_venv/bin/activate
python quantize_awq.py
```

## Pipeline

1. **prepare_dataset.py** - Converts Telegram JSON export to JSONL training format
2. **train.py** - Fine-tunes with 4-bit NF4 quantized loading, LoRA rank 8, targets q/k/v projections
3. **merge_lora.py** - Combines LoRA weights with base model on CPU
4. **quantize_awq.py** - W4A16 quantization with 512 calibration samples

## Training Configuration

| Parameter | Value |
|-----------|-------|
| Base model | Qwen/Qwen2.5-7B-Instruct |
| GPU | RTX 3060 (CUDA device 1) |
| Max sequence length | 768 tokens |
| Batch size | 1 |
| Gradient accumulation | 64 |
| LoRA rank | 8 |
| LoRA alpha | 16 |
| Target modules | q_proj, k_proj, v_proj |
| Optimizer | paged_adamw_8bit |
| Quantization | 4-bit NF4 + double quantization |

## Data Files

All data stored externally via symlinks (not in git):

| File | Description |
|------|-------------|
| `datasets/result.json` | Raw Telegram export |
| `datasets/lydia_dataset_v3.jsonl` | Training dataset (1918 dialogs, 33K messages) |
| `adapters/qwen2.5-7b-lydia-lora/` | Trained LoRA adapters |

## Dataset Format

JSONL with structure:
```json
{"messages": [{"from": "user", "value": "text"}, {"from": "assistant", "value": "text"}]}
```

## Virtual Environments

Located in `/home/shaerware/qwen-finetune/`:
- `train_venv/` - For training (trl, peft, bitsandbytes)
- `quant_venv/` - For quantization (llmcompressor)
