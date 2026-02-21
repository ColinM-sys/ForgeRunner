export interface Dataset {
  id: string;
  name: string;
  filename: string;
  total_examples: number;
  status: 'uploading' | 'processing' | 'scored' | 'error';
  created_at: string;
}

export interface Example {
  id: string;
  dataset_id: string;
  line_number: number;
  system_prompt: string;
  user_content: string;
  assistant_content: string;
  message_count: number;
  char_count: number;
  bucket_id: string | null;
  bucket_name: string | null;
  review_status: 'pending' | 'approved' | 'rejected' | 'needs_edit';
  aggregate_score: number | null;
  created_at: string;
}

export interface ExampleDetail extends Example {
  raw_json: string;
  scores: Score[];
}

export interface Score {
  id: string;
  engine_name: 'cleanlab' | 'forge_embedder' | 'argilla' | 'label_studio';
  score_type: string;
  score_value: number;
  details: string | null;
  created_at: string;
}

export interface Bucket {
  id: string;
  name: string;
  display_name: string;
  description: string;
  is_system: boolean;
  color: string;
  example_count: number;
}

export interface ExampleList {
  items: Example[];
  total: number;
  page: number;
  page_size: number;
}

export interface UploadResponse {
  dataset_id: string;
  filename: string;
  total_lines: number;
  valid_lines: number;
  invalid_lines: number;
  errors: string[];
}

export interface ScoringStatus {
  job_id: string;
  dataset_id: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  current_engine: string;
  error: string | null;
}

export interface DashboardOverview {
  total_examples: number;
  total_datasets: number;
  approved_count: number;
  rejected_count: number;
  pending_count: number;
  approval_rate: number;
  average_score: number | null;
  bucket_breakdown: { name: string; display_name: string; color: string; count: number }[];
  score_distribution: { range: string; count: number }[];
  engine_coverage: Record<string, number>;
}

export interface ExportRequest {
  dataset_ids?: string[];
  bucket_ids?: string[];
  review_status?: string;
  min_score?: number;
  max_score?: number;
}

export interface ExportResponse {
  filename: string;
  total_examples: number;
  download_url: string;
}
