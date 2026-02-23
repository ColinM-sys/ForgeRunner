import api from './client';

export interface EstimatorRequest {
  model_name: string;
  custom_params_b?: number;
  lora_rank: number;
  lora_alpha: number;
  lora_targets: string[];
  quantization: '4bit' | '8bit' | 'none';
  batch_size: number;
  gradient_accumulation: number;
  learning_rate: number;
  lr_scheduler: 'cosine' | 'linear' | 'constant';
  epochs: number;
  precision: 'bf16' | 'fp16' | 'fp32';
  gradient_checkpointing: boolean;
  max_seq_length: number;
  gpu_name: string;
  gpu_vram_gb: number;
  gpu_tflops: number;
  dataset_id?: string;
  manual_example_count?: number;
  manual_avg_tokens?: number;
}

export interface EstimatorResponse {
  model_name: string;
  model_params_b: number;
  quantized_model_size_gb: number;
  lora_trainable_params: number;
  lora_trainable_pct: number;
  lora_adapter_size_mb: number;
  model_vram_gb: number;
  optimizer_vram_gb: number;
  activations_vram_gb: number;
  total_vram_gb: number;
  fits_in_vram: boolean;
  vram_headroom_gb: number;
  effective_batch_size: number;
  total_examples: number;
  avg_tokens_per_example: number;
  total_tokens: number;
  steps_per_epoch: number;
  total_steps: number;
  estimated_time_per_epoch_min: number;
  estimated_total_time_min: number;
  warnings: string[];
  recommendations: string[];
  available_models: string[];
}

export async function estimateTraining(params: EstimatorRequest): Promise<EstimatorResponse> {
  const { data } = await api.post('/estimator/estimate', params);
  return data;
}

export async function getGpus(): Promise<Record<string, { vram_gb: number; tflops: number }>> {
  const { data } = await api.get('/estimator/gpus');
  return data;
}

export async function getModels(): Promise<Record<string, { params_b: number; hidden: number; layers: number; context: number }>> {
  const { data } = await api.get('/estimator/models');
  return data;
}
