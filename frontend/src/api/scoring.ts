import api from './client';
import type { ScoringStatus } from '../types';

export async function startScoring(datasetId: string): Promise<{ job_id: string }> {
  const { data } = await api.post(`/scoring/start/${datasetId}`);
  return data;
}

export async function getScoringStatus(jobId: string): Promise<ScoringStatus> {
  const { data } = await api.get(`/scoring/status/${jobId}`);
  return data;
}
