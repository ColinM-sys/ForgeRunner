import api from './client';
import type { Bucket } from '../types';

export async function listBuckets(): Promise<Bucket[]> {
  const { data } = await api.get('/buckets');
  return data;
}
