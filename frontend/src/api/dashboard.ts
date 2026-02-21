import api from './client';
import type { DashboardOverview } from '../types';

export async function getDashboardOverview(): Promise<DashboardOverview> {
  const { data } = await api.get('/dashboard/overview');
  return data;
}
