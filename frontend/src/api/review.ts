import api from './client';

export async function reviewExample(
  exampleId: string,
  action: 'approved' | 'rejected' | 'needs_edit',
  notes?: string,
): Promise<void> {
  await api.post(`/review/${exampleId}`, { action, notes });
}

export async function batchReview(
  exampleIds: string[],
  action: 'approved' | 'rejected' | 'needs_edit',
  notes?: string,
): Promise<{ count: number }> {
  const { data } = await api.post('/review/batch', {
    example_ids: exampleIds,
    action,
    notes,
  });
  return data;
}
