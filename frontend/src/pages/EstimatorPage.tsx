import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  estimateTraining, getGpus,
  type EstimatorRequest, type EstimatorResponse,
} from '../api/estimator';
import { listDatasets } from '../api/datasets';
import {
  Cpu, HardDrive, Zap, Clock, AlertTriangle, CheckCircle, Database,
  ChevronDown, ChevronUp, Layers, Settings2, MemoryStick,
} from 'lucide-react';

const LORA_TARGETS = [
  'q_proj', 'k_proj', 'v_proj', 'o_proj',
  'gate_proj', 'up_proj', 'down_proj',
];

const DEFAULT_PARAMS: EstimatorRequest = {
  model_name: 'qwen2.5-14b',
  lora_rank: 128,
  lora_alpha: 256,
  lora_targets: ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'],
  quantization: '4bit',
  batch_size: 1,
  gradient_accumulation: 16,
  learning_rate: 2e-4,
  lr_scheduler: 'cosine',
  epochs: 3,
  precision: 'bf16',
  gradient_checkpointing: true,
  max_seq_length: 2048,
  gpu_name: 'RTX 4090',
  gpu_vram_gb: 24,
  gpu_tflops: 82.6,
};

export default function EstimatorPage() {
  const [params, setParams] = useState<EstimatorRequest>(DEFAULT_PARAMS);
  const [result, setResult] = useState<EstimatorResponse | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { data: datasets } = useQuery({ queryKey: ['datasets'], queryFn: listDatasets });
  const { data: gpus } = useQuery({ queryKey: ['gpus'], queryFn: getGpus });

  const scoredDatasets = (datasets || []).filter(d => d.status === 'scored');

  const mutation = useMutation({
    mutationFn: estimateTraining,
    onSuccess: setResult,
  });

  const update = <K extends keyof EstimatorRequest>(key: K, value: EstimatorRequest[K]) => {
    setParams(prev => ({ ...prev, [key]: value }));
  };

  const handleGpuChange = (name: string) => {
    update('gpu_name', name);
    if (gpus && gpus[name]) {
      update('gpu_vram_gb', gpus[name].vram_gb);
      update('gpu_tflops', gpus[name].tflops);
    }
  };

  const toggleTarget = (target: string) => {
    const current = params.lora_targets;
    if (current.includes(target)) {
      update('lora_targets', current.filter(t => t !== target));
    } else {
      update('lora_targets', [...current, target]);
    }
  };

  const handleEstimate = () => mutation.mutate(params);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold">Input Params Estimator</h2>
        <p className="text-gray-500 text-sm mt-1">
          Estimate VRAM usage, training time, and get recommendations for your fine-tuning configuration.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Left column: Input parameters */}
        <div className="space-y-4">
          {/* Model Selection */}
          <Section icon={<Cpu className="w-4 h-4" />} title="Model">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Model">
                <select
                  value={params.model_name}
                  onChange={e => update('model_name', e.target.value)}
                  className="input-field"
                >
                  <option value="qwen2.5-0.5b">Qwen 2.5 0.5B</option>
                  <option value="qwen2.5-1.5b">Qwen 2.5 1.5B</option>
                  <option value="qwen2.5-3b">Qwen 2.5 3B</option>
                  <option value="qwen2.5-7b">Qwen 2.5 7B</option>
                  <option value="qwen2.5-14b">Qwen 2.5 14B</option>
                  <option value="qwen2.5-32b">Qwen 2.5 32B</option>
                  <option value="qwen2.5-72b">Qwen 2.5 72B</option>
                  <option value="llama3-8b">Llama 3 8B</option>
                  <option value="llama3-70b">Llama 3 70B</option>
                  <option value="llama3.1-8b">Llama 3.1 8B</option>
                  <option value="llama3.1-70b">Llama 3.1 70B</option>
                  <option value="mistral-7b">Mistral 7B</option>
                  <option value="gemma2-9b">Gemma 2 9B</option>
                  <option value="gemma2-27b">Gemma 2 27B</option>
                  <option value="phi3-mini">Phi-3 Mini (3.8B)</option>
                  <option value="phi3-medium">Phi-3 Medium (14B)</option>
                  <option value="custom">Custom</option>
                </select>
              </Field>
              <Field label="GPU">
                <select
                  value={params.gpu_name}
                  onChange={e => handleGpuChange(e.target.value)}
                  className="input-field"
                >
                  {gpus && Object.keys(gpus).map(name => (
                    <option key={name} value={name}>{name} ({gpus[name].vram_gb}GB)</option>
                  ))}
                </select>
              </Field>
            </div>
            {params.model_name === 'custom' && (
              <Field label="Custom Model Size (Billion params)">
                <input
                  type="number" step="0.1"
                  value={params.custom_params_b || ''}
                  onChange={e => update('custom_params_b', parseFloat(e.target.value) || undefined)}
                  className="input-field"
                  placeholder="e.g. 14.0"
                />
              </Field>
            )}
          </Section>

          {/* LoRA Configuration */}
          <Section icon={<Layers className="w-4 h-4" />} title="LoRA Configuration">
            <div className="grid grid-cols-3 gap-3">
              <Field label="Rank">
                <input
                  type="number"
                  value={params.lora_rank}
                  onChange={e => update('lora_rank', parseInt(e.target.value) || 64)}
                  className="input-field"
                />
              </Field>
              <Field label="Alpha">
                <input
                  type="number"
                  value={params.lora_alpha}
                  onChange={e => update('lora_alpha', parseInt(e.target.value) || 128)}
                  className="input-field"
                />
              </Field>
              <Field label="Quantization">
                <select
                  value={params.quantization}
                  onChange={e => update('quantization', e.target.value as '4bit' | '8bit' | 'none')}
                  className="input-field"
                >
                  <option value="4bit">4-bit (QLoRA)</option>
                  <option value="8bit">8-bit</option>
                  <option value="none">None (Full)</option>
                </select>
              </Field>
            </div>
            <Field label="Target Modules">
              <div className="flex flex-wrap gap-1.5">
                {LORA_TARGETS.map(t => (
                  <button
                    key={t}
                    onClick={() => toggleTarget(t)}
                    className={`px-2 py-1 rounded text-xs font-mono transition-colors ${
                      params.lora_targets.includes(t)
                        ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                        : 'bg-gray-800 text-gray-500 border border-gray-700 hover:border-gray-600'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </Field>
          </Section>

          {/* Training Configuration */}
          <Section icon={<Settings2 className="w-4 h-4" />} title="Training Configuration">
            <div className="grid grid-cols-3 gap-3">
              <Field label="Batch Size">
                <input
                  type="number"
                  value={params.batch_size}
                  onChange={e => update('batch_size', parseInt(e.target.value) || 1)}
                  className="input-field"
                />
              </Field>
              <Field label="Grad Accum">
                <input
                  type="number"
                  value={params.gradient_accumulation}
                  onChange={e => update('gradient_accumulation', parseInt(e.target.value) || 1)}
                  className="input-field"
                />
              </Field>
              <Field label="Epochs">
                <input
                  type="number"
                  value={params.epochs}
                  onChange={e => update('epochs', parseInt(e.target.value) || 1)}
                  className="input-field"
                />
              </Field>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Learning Rate">
                <input
                  type="text"
                  value={params.learning_rate}
                  onChange={e => update('learning_rate', parseFloat(e.target.value) || 2e-4)}
                  className="input-field font-mono"
                />
              </Field>
              <Field label="LR Scheduler">
                <select
                  value={params.lr_scheduler}
                  onChange={e => update('lr_scheduler', e.target.value as 'cosine' | 'linear' | 'constant')}
                  className="input-field"
                >
                  <option value="cosine">Cosine</option>
                  <option value="linear">Linear</option>
                  <option value="constant">Constant</option>
                </select>
              </Field>
              <Field label="Precision">
                <select
                  value={params.precision}
                  onChange={e => update('precision', e.target.value as 'bf16' | 'fp16' | 'fp32')}
                  className="input-field"
                >
                  <option value="bf16">BF16</option>
                  <option value="fp16">FP16</option>
                  <option value="fp32">FP32</option>
                </select>
              </Field>
            </div>

            {/* Advanced toggle */}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs text-gray-500 hover:text-gray-400 flex items-center gap-1 mt-1"
            >
              {showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              Advanced
            </button>
            {showAdvanced && (
              <div className="grid grid-cols-2 gap-3 mt-2">
                <Field label="Max Seq Length">
                  <input
                    type="number"
                    value={params.max_seq_length}
                    onChange={e => update('max_seq_length', parseInt(e.target.value) || 2048)}
                    className="input-field"
                  />
                </Field>
                <Field label="Gradient Checkpointing">
                  <button
                    onClick={() => update('gradient_checkpointing', !params.gradient_checkpointing)}
                    className={`w-full text-left px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                      params.gradient_checkpointing
                        ? 'bg-green-500/10 border-green-500/30 text-green-400'
                        : 'bg-gray-800 border-gray-700 text-gray-500'
                    }`}
                  >
                    {params.gradient_checkpointing ? 'Enabled' : 'Disabled'}
                  </button>
                </Field>
              </div>
            )}
          </Section>

          {/* Dataset link */}
          <Section icon={<Database className="w-4 h-4" />} title="Dataset">
            <Field label="Link to ForgeRunner dataset (optional)">
              <select
                value={params.dataset_id || ''}
                onChange={e => update('dataset_id', e.target.value || undefined)}
                className="input-field"
              >
                <option value="">Manual input / No dataset</option>
                {scoredDatasets.map(d => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.total_examples.toLocaleString()} examples)
                  </option>
                ))}
              </select>
            </Field>
            {!params.dataset_id && (
              <div className="grid grid-cols-2 gap-3">
                <Field label="Example Count">
                  <input
                    type="number"
                    value={params.manual_example_count || ''}
                    onChange={e => update('manual_example_count', parseInt(e.target.value) || undefined)}
                    className="input-field"
                    placeholder="e.g. 4529"
                  />
                </Field>
                <Field label="Avg Tokens/Example">
                  <input
                    type="number"
                    value={params.manual_avg_tokens || ''}
                    onChange={e => update('manual_avg_tokens', parseInt(e.target.value) || undefined)}
                    className="input-field"
                    placeholder="~350"
                  />
                </Field>
              </div>
            )}
          </Section>

          {/* Estimate button */}
          <button
            onClick={handleEstimate}
            disabled={mutation.isPending}
            className="w-full flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-500/50 text-white py-3 rounded-xl transition-colors font-medium text-sm"
          >
            {mutation.isPending ? (
              <><Clock className="w-4 h-4 animate-spin" /> Estimating...</>
            ) : (
              <><Zap className="w-4 h-4" /> Estimate Training</>
            )}
          </button>
        </div>

        {/* Right column: Results */}
        <div className="space-y-4">
          {!result && !mutation.isPending && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-8 text-center">
              <MemoryStick className="w-10 h-10 text-gray-700 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">Configure parameters and click Estimate</p>
              <p className="text-gray-600 text-xs mt-1">
                Pre-filled with your v4 intake training config
              </p>
            </div>
          )}

          {result && (
            <>
              {/* VRAM Breakdown */}
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
                  <HardDrive className="w-4 h-4" /> VRAM Usage
                </h3>
                <div className="space-y-2">
                  <VramBar label="Model" gb={result.model_vram_gb} total={params.gpu_vram_gb} color="#3B82F6" />
                  <VramBar label="Optimizer" gb={result.optimizer_vram_gb} total={params.gpu_vram_gb} color="#8B5CF6" />
                  <VramBar label="Activations" gb={result.activations_vram_gb} total={params.gpu_vram_gb} color="#10B981" />
                  <VramBar label="Overhead" gb={1.5} total={params.gpu_vram_gb} color="#6B7280" />
                </div>
                <div className="mt-3 pt-3 border-t border-gray-800 flex items-center justify-between">
                  <span className="text-sm text-gray-400">Total</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-lg font-bold ${result.fits_in_vram ? 'text-green-400' : 'text-red-400'}`}>
                      {result.total_vram_gb} GB
                    </span>
                    <span className="text-xs text-gray-600">/ {params.gpu_vram_gb} GB</span>
                    {result.fits_in_vram ? (
                      <CheckCircle className="w-4 h-4 text-green-400" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-red-400" />
                    )}
                  </div>
                </div>
                {/* VRAM bar visual */}
                <div className="mt-2 h-4 bg-gray-800 rounded-full overflow-hidden relative">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, (result.total_vram_gb / params.gpu_vram_gb) * 100)}%`,
                      background: result.fits_in_vram
                        ? 'linear-gradient(90deg, #3B82F6, #8B5CF6, #10B981)'
                        : 'linear-gradient(90deg, #EF4444, #F87171)',
                    }}
                  />
                  <div
                    className="absolute top-0 h-full border-r-2 border-white/30"
                    style={{ left: `${Math.min(100, (params.gpu_vram_gb / params.gpu_vram_gb) * 100)}%` }}
                  />
                </div>
                <p className={`text-xs mt-1 ${result.vram_headroom_gb > 0 ? 'text-gray-500' : 'text-red-400'}`}>
                  {result.vram_headroom_gb > 0
                    ? `${result.vram_headroom_gb} GB headroom`
                    : `${Math.abs(result.vram_headroom_gb)} GB over capacity`}
                </p>
              </div>

              {/* LoRA Stats */}
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
                  <Layers className="w-4 h-4" /> LoRA Adapter
                </h3>
                <div className="grid grid-cols-3 gap-3">
                  <Stat label="Trainable Params" value={formatNumber(result.lora_trainable_params)} />
                  <Stat label="% of Model" value={`${result.lora_trainable_pct}%`} />
                  <Stat label="Adapter Size" value={`${result.lora_adapter_size_mb} MB`} />
                </div>
              </div>

              {/* Training Estimates */}
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
                  <Clock className="w-4 h-4" /> Training Estimates
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  <Stat label="Effective Batch" value={String(result.effective_batch_size)} />
                  <Stat label="Total Examples" value={result.total_examples.toLocaleString()} />
                  <Stat label="Avg Tokens/Ex" value={result.avg_tokens_per_example.toLocaleString()} />
                  <Stat label="Total Tokens" value={formatNumber(result.total_tokens)} />
                  <Stat label="Steps/Epoch" value={result.steps_per_epoch.toLocaleString()} />
                  <Stat label="Total Steps" value={result.total_steps.toLocaleString()} />
                </div>
                <div className="mt-3 pt-3 border-t border-gray-800 grid grid-cols-2 gap-3">
                  <div className="bg-gray-800/50 rounded-lg p-3 text-center">
                    <p className="text-xs text-gray-500">Per Epoch</p>
                    <p className="text-xl font-bold text-blue-400">{formatTime(result.estimated_time_per_epoch_min)}</p>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3 text-center">
                    <p className="text-xs text-gray-500">Total ({params.epochs} epochs)</p>
                    <p className="text-xl font-bold text-orange-400">{formatTime(result.estimated_total_time_min)}</p>
                  </div>
                </div>
              </div>

              {/* Warnings and Recommendations */}
              {(result.warnings.length > 0 || result.recommendations.length > 0) && (
                <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3">
                  {result.warnings.map((w, i) => (
                    <div key={`w-${i}`} className="flex items-start gap-2 text-xs">
                      <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 mt-0.5 shrink-0" />
                      <span className="text-yellow-400/80">{w}</span>
                    </div>
                  ))}
                  {result.recommendations.map((r, i) => (
                    <div key={`r-${i}`} className="flex items-start gap-2 text-xs">
                      <CheckCircle className="w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0" />
                      <span className="text-blue-400/80">{r}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Model summary */}
              <div className="text-[10px] text-gray-600 text-center">
                {result.model_name} &middot; {result.model_params_b}B params &middot; {result.quantized_model_size_gb} GB quantized
              </div>
            </>
          )}

          {mutation.isError && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
              <AlertTriangle className="w-4 h-4 inline mr-2" />
              {(mutation.error as Error).message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


// ── Helper components ────────────────────────────────────────────

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-400 flex items-center gap-2">
        {icon} {title}
      </h3>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[10px] text-gray-600 uppercase tracking-wider block mb-1">{label}</label>
      {children}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800/30 rounded-lg p-2">
      <p className="text-[10px] text-gray-600">{label}</p>
      <p className="text-sm font-mono font-medium text-gray-300">{value}</p>
    </div>
  );
}

function VramBar({ label, gb, total, color }: { label: string; gb: number; total: number; color: string }) {
  const pct = (gb / total) * 100;
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500 w-20">{label}</span>
      <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs text-gray-400 font-mono w-14 text-right">{gb.toFixed(1)} GB</span>
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return String(n);
}

function formatTime(minutes: number): string {
  if (minutes < 1) return '<1 min';
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const hrs = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
}
