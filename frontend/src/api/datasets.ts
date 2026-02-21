import api from './client';
import type { Dataset, UploadResponse } from '../types';

export async function listDatasets(): Promise<Dataset[]> {
  const { data } = await api.get('/datasets');
  return data;
}

export async function getDataset(id: string): Promise<Dataset> {
  const { data } = await api.get(`/datasets/${id}`);
  return data;
}

export async function uploadDataset(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function deleteDataset(id: string): Promise<void> {
  await api.delete(`/datasets/${id}`);
}
