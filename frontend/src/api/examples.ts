import api from './client';
import type { ExampleDetail, ExampleList } from '../types';

export interface ExampleFilters {
  dataset_id?: string;
  bucket_id?: string;
  review_status?: string;
  min_score?: number;
  max_score?: number;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
}

export async function listExamples(filters: ExampleFilters = {}): Promise<ExampleList> {
  const { data } = await api.get('/examples', { params: filters });
  return data;
}

export async function getExample(id: string): Promise<ExampleDetail> {
  const { data } = await api.get(`/examples/${id}`);
  return data;
}

export async function assignBucket(exampleId: string, bucketId: string): Promise<void> {
  await api.patch(`/examples/${exampleId}/bucket`, { bucket_id: bucketId });
}
