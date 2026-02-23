import api from './client';

export interface SourceResult {
  url: string;
  reachable: boolean;
  status_code: number | null;
  title: string | null;
  word_count: number;
  content_preview: string;
  scores: Record<string, number>;
  overall_score: number;
  details: string;
}

export interface SourceCheckResponse {
  results: SourceResult[];
  total_checked: number;
  avg_score: number;
  checked_at: string;
}

export async function checkSources(urls: string[]): Promise<SourceCheckResponse> {
  const { data } = await api.post('/sources/check', { urls });
  return data;
}

// ── Gap Analysis ──────────────────────────────────────────────────

export interface GapSourceResult {
  url: string;
  reachable: boolean;
  title: string | null;
  word_count: number;
  content_preview: string;
  content_quality: number;
  novelty_score: number;
  closest_bucket: string | null;
  closest_bucket_color: string | null;
  bucket_coverage: number;
  closest_examples: Array<{
    preview: string;
    similarity: number;
    bucket: string;
    score: number;
  }>;
  recommendation: 'high_value' | 'moderate_value' | 'low_value' | 'redundant';
  recommendation_reason: string;
  details: string;
}

export interface BucketStats {
  name: string;
  display_name: string;
  color: string;
  count: number;
  avg_score: number;
}

export interface GapAnalysisResponse {
  results: GapSourceResult[];
  dataset_name: string;
  dataset_size: number;
  bucket_breakdown: BucketStats[];
  analyzed_at: string;
}

export async function analyzeGaps(urls: string[], datasetId: string): Promise<GapAnalysisResponse> {
  const { data } = await api.post('/sources/gap-analysis', { urls, dataset_id: datasetId });
  return data;
}
