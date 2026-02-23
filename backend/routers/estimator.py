"""Training parameter estimator.

Estimates VRAM usage, training time, and token counts based on model config,
LoRA parameters, and training hyperparameters. Optionally links to a ForgeRunner
dataset for actual token statistics.
"""
import logging
import math

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.example import Example

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Known model sizes (param count in billions, hidden dim, layers, heads) ──
MODEL_REGISTRY: dict[str, dict] = {
    "qwen2.5-0.5b":  {"params_b": 0.5,  "hidden": 896,   "layers": 24,  "heads": 14,  "context": 32768},
    "qwen2.5-1.5b":  {"params_b": 1.5,  "hidden": 1536,  "layers": 28,  "heads": 12,  "context": 32768},
    "qwen2.5-3b":    {"params_b": 3.0,  "hidden": 2048,  "layers": 36,  "heads": 16,  "context": 32768},
    "qwen2.5-7b":    {"params_b": 7.0,  "hidden": 3584,  "layers": 28,  "heads": 28,  "context": 131072},
    "qwen2.5-14b":   {"params_b": 14.0, "hidden": 5120,  "layers": 40,  "heads": 40,  "context": 131072},
    "qwen2.5-32b":   {"params_b": 32.0, "hidden": 5120,  "layers": 64,  "heads": 40,  "context": 131072},
    "qwen2.5-72b":   {"params_b": 72.0, "hidden": 8192,  "layers": 80,  "heads": 64,  "context": 131072},
    "llama3-8b":     {"params_b": 8.0,  "hidden": 4096,  "layers": 32,  "heads": 32,  "context": 8192},
    "llama3-70b":    {"params_b": 70.0, "hidden": 8192,  "layers": 80,  "heads": 64,  "context": 8192},
    "llama3.1-8b":   {"params_b": 8.0,  "hidden": 4096,  "layers": 32,  "heads": 32,  "context": 131072},
    "llama3.1-70b":  {"params_b": 70.0, "hidden": 8192,  "layers": 80,  "heads": 64,  "context": 131072},
    "mistral-7b":    {"params_b": 7.0,  "hidden": 4096,  "layers": 32,  "heads": 32,  "context": 32768},
    "gemma2-9b":     {"params_b": 9.0,  "hidden": 3584,  "layers": 42,  "heads": 16,  "context": 8192},
    "gemma2-27b":    {"params_b": 27.0, "hidden": 4608,  "layers": 46,  "heads": 32,  "context": 8192},
    "phi3-mini":     {"params_b": 3.8,  "hidden": 3072,  "layers": 32,  "heads": 32,  "context": 128000},
    "phi3-medium":   {"params_b": 14.0, "hidden": 5120,  "layers": 40,  "heads": 40,  "context": 128000},
    "custom":        {"params_b": 0,    "hidden": 0,     "layers": 0,   "heads": 0,   "context": 0},
}


class EstimatorRequest(BaseModel):
    # Model
    model_name: str = "qwen2.5-14b"
    custom_params_b: float | None = None  # Only used if model_name == "custom"

    # LoRA
    lora_rank: int = 128
    lora_alpha: int = 256
    lora_targets: list[str] = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    quantization: str = "4bit"  # "4bit" | "8bit" | "none"

    # Training
    batch_size: int = 1
    gradient_accumulation: int = 16
    learning_rate: float = 2e-4
    lr_scheduler: str = "cosine"  # "cosine" | "linear" | "constant"
    epochs: int = 3
    precision: str = "bf16"  # "bf16" | "fp16" | "fp32"
    gradient_checkpointing: bool = True
    max_seq_length: int = 2048

    # GPU
    gpu_name: str = "RTX 4090"
    gpu_vram_gb: float = 24.0
    gpu_tflops: float = 82.6  # FP16 TFLOPS

    # Dataset (optional)
    dataset_id: str | None = None
    manual_example_count: int | None = None
    manual_avg_tokens: int | None = None


class EstimatorResponse(BaseModel):
    # Model info
    model_name: str
    model_params_b: float
    quantized_model_size_gb: float

    # LoRA
    lora_trainable_params: int
    lora_trainable_pct: float
    lora_adapter_size_mb: float

    # VRAM estimate
    model_vram_gb: float
    optimizer_vram_gb: float
    activations_vram_gb: float
    total_vram_gb: float
    fits_in_vram: bool
    vram_headroom_gb: float

    # Training
    effective_batch_size: int
    total_examples: int
    avg_tokens_per_example: int
    total_tokens: int
    steps_per_epoch: int
    total_steps: int
    estimated_time_per_epoch_min: float
    estimated_total_time_min: float

    # Recommendations
    warnings: list[str]
    recommendations: list[str]

    # Available models
    available_models: list[str]


GPU_REGISTRY: dict[str, dict] = {
    "RTX 4090":     {"vram_gb": 24.0, "tflops": 82.6},
    "RTX 3090":     {"vram_gb": 24.0, "tflops": 35.6},
    "RTX 3090 Ti":  {"vram_gb": 24.0, "tflops": 40.0},
    "RTX 4080":     {"vram_gb": 16.0, "tflops": 48.7},
    "RTX 3080":     {"vram_gb": 10.0, "tflops": 29.8},
    "RTX A6000":    {"vram_gb": 48.0, "tflops": 38.7},
    "A100 40GB":    {"vram_gb": 40.0, "tflops": 77.9},
    "A100 80GB":    {"vram_gb": 80.0, "tflops": 77.9},
    "H100":         {"vram_gb": 80.0, "tflops": 267.6},
    "Jetson Orin Nano": {"vram_gb": 8.0, "tflops": 5.3},
}


@router.post("/estimate", response_model=EstimatorResponse)
async def estimate_training(req: EstimatorRequest, db: AsyncSession = Depends(get_db)):
    """Estimate VRAM usage, training time, and provide recommendations."""

    # ── Resolve model ──
    model_info = MODEL_REGISTRY.get(req.model_name, MODEL_REGISTRY["custom"])
    params_b = req.custom_params_b if req.model_name == "custom" and req.custom_params_b else model_info["params_b"]
    total_params = int(params_b * 1e9)
    hidden_dim = model_info["hidden"]
    num_layers = model_info["layers"]

    # ── Quantized model size ──
    bits_per_param = {"4bit": 4, "8bit": 8, "none": 16 if req.precision in ("bf16", "fp16") else 32}
    bpp = bits_per_param.get(req.quantization, 4)
    quantized_model_gb = (total_params * bpp) / 8 / 1e9

    # ── LoRA trainable params ──
    # Each target module in each layer adds rank * (hidden_dim + hidden_dim) params (simplified)
    # For attention: q,k,v,o each have hidden_dim x hidden_dim weight matrices
    # LoRA adds: 2 * rank * hidden_dim per target per layer
    targets_per_layer = len(req.lora_targets)
    lora_params_per_layer = targets_per_layer * 2 * req.lora_rank * max(hidden_dim, 1)
    total_lora_params = lora_params_per_layer * max(num_layers, 1)
    lora_pct = (total_lora_params / total_params * 100) if total_params > 0 else 0
    lora_adapter_mb = (total_lora_params * 2) / 1e6  # Stored in fp16

    # ── VRAM estimates ──
    model_vram = quantized_model_gb

    # Optimizer: AdamW stores 2 states per trainable param (in fp32)
    optimizer_vram = (total_lora_params * 4 * 2) / 1e9  # 2 states, 4 bytes each

    # Activations: depends on batch size, seq length, hidden dim, layers
    # With gradient checkpointing, activations ~= 2 * batch * seq * hidden * sqrt(layers) bytes
    if req.gradient_checkpointing:
        act_factor = math.sqrt(max(num_layers, 1))
    else:
        act_factor = max(num_layers, 1)
    activations_vram = (2 * req.batch_size * req.max_seq_length * max(hidden_dim, 1) * act_factor) / 1e9

    total_vram = model_vram + optimizer_vram + activations_vram + 1.5  # 1.5 GB overhead (CUDA, etc)
    fits = total_vram <= req.gpu_vram_gb
    headroom = req.gpu_vram_gb - total_vram

    # ── Dataset stats ──
    total_examples = 0
    avg_tokens = req.manual_avg_tokens or 350  # Default estimate

    if req.dataset_id:
        count_result = await db.execute(
            select(func.count()).where(Example.dataset_id == req.dataset_id)
        )
        total_examples = count_result.scalar() or 0

        # Estimate avg tokens from char_count (rough: 1 token ≈ 4 chars)
        avg_chars_result = await db.execute(
            select(func.avg(Example.char_count)).where(Example.dataset_id == req.dataset_id)
        )
        avg_chars = avg_chars_result.scalar()
        if avg_chars:
            avg_tokens = int(avg_chars / 4)
    elif req.manual_example_count:
        total_examples = req.manual_example_count

    total_tokens = total_examples * avg_tokens

    # ── Training time ──
    effective_batch = req.batch_size * req.gradient_accumulation
    steps_per_epoch = max(1, total_examples // effective_batch) if total_examples > 0 else 0
    total_steps = steps_per_epoch * req.epochs

    # Time estimate calibrated from real-world data:
    # RTX 4090 (82.6 TFLOPS) + Qwen 14B 4-bit LoRA: ~1500 tokens/sec
    # Scale by GPU TFLOPS relative to 4090, and inversely by model size
    base_tokens_per_sec = 1500  # Calibrated on RTX 4090 + 14B QLoRA
    gpu_factor = req.gpu_tflops / 82.6
    model_factor = 14.0 / max(params_b, 0.5)  # Inversely proportional to model size
    tokens_per_sec = base_tokens_per_sec * gpu_factor * min(model_factor, 3.0)  # Cap 3x for tiny models

    if total_examples > 0 and tokens_per_sec > 0:
        tokens_per_epoch = total_examples * avg_tokens
        time_per_epoch_min = tokens_per_epoch / tokens_per_sec / 60
    else:
        time_per_epoch_min = 0

    total_time_min = time_per_epoch_min * req.epochs

    # ── Warnings and recommendations ──
    warnings = []
    recommendations = []

    if not fits:
        warnings.append(f"Estimated VRAM ({total_vram:.1f} GB) exceeds GPU capacity ({req.gpu_vram_gb:.0f} GB)")
        if req.quantization == "none":
            recommendations.append("Enable 4-bit quantization to reduce model VRAM by ~75%")
        elif req.quantization == "8bit":
            recommendations.append("Switch to 4-bit quantization to further reduce VRAM")
        if not req.gradient_checkpointing:
            recommendations.append("Enable gradient checkpointing to reduce activation memory")
        if req.batch_size > 1:
            recommendations.append(f"Reduce batch size to 1 (currently {req.batch_size}) and increase gradient accumulation")
        if req.lora_rank > 64:
            recommendations.append(f"Reduce LoRA rank from {req.lora_rank} to 64 to save optimizer VRAM")

    if headroom < 2 and fits:
        warnings.append(f"Tight VRAM headroom ({headroom:.1f} GB). May OOM during longer sequences")

    if req.lora_rank > 256:
        warnings.append(f"LoRA rank {req.lora_rank} is very high. Diminishing returns beyond 128-256")

    if effective_batch < 8:
        recommendations.append(f"Effective batch size is {effective_batch}. Consider increasing gradient accumulation for more stable training")

    if req.learning_rate > 5e-4:
        warnings.append(f"Learning rate {req.learning_rate} is high for LoRA fine-tuning. Typical range: 1e-4 to 3e-4")

    if total_examples > 0 and total_examples < 100:
        warnings.append(f"Only {total_examples} examples. Minimum ~500 recommended for meaningful fine-tuning")
    elif total_examples > 0 and total_examples < 500:
        recommendations.append("Consider data augmentation - small datasets benefit from 5+ epochs")

    if avg_tokens > req.max_seq_length:
        warnings.append(f"Avg tokens ({avg_tokens}) exceeds max_seq_length ({req.max_seq_length}). Data will be truncated")

    return EstimatorResponse(
        model_name=req.model_name,
        model_params_b=params_b,
        quantized_model_size_gb=round(quantized_model_gb, 2),
        lora_trainable_params=total_lora_params,
        lora_trainable_pct=round(lora_pct, 2),
        lora_adapter_size_mb=round(lora_adapter_mb, 1),
        model_vram_gb=round(model_vram, 2),
        optimizer_vram_gb=round(optimizer_vram, 2),
        activations_vram_gb=round(activations_vram, 2),
        total_vram_gb=round(total_vram, 2),
        fits_in_vram=fits,
        vram_headroom_gb=round(headroom, 2),
        effective_batch_size=effective_batch,
        total_examples=total_examples,
        avg_tokens_per_example=avg_tokens,
        total_tokens=total_tokens,
        steps_per_epoch=steps_per_epoch,
        total_steps=total_steps,
        estimated_time_per_epoch_min=round(time_per_epoch_min, 1),
        estimated_total_time_min=round(total_time_min, 1),
        warnings=warnings,
        recommendations=recommendations,
        available_models=list(MODEL_REGISTRY.keys()),
    )


@router.get("/gpus")
async def list_gpus():
    """List known GPU configurations."""
    return GPU_REGISTRY


@router.get("/models")
async def list_models():
    """List known model configurations."""
    return MODEL_REGISTRY
