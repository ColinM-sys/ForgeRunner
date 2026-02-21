import api from './client';
import type { ExportRequest, ExportResponse } from '../types';

export async function createExport(request: ExportRequest): Promise<ExportResponse> {
  const { data } = await api.post('/export', request);
  return data;
}
