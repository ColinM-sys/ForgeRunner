// Waits for the backend before the app asks it for data, so the first screens do not show 500s while it is starting.
// The probe, the wait and the sleep are parameters, so the logic runs in a plain test with no browser or server.

export type ProbeResult = { ok: boolean; status: number };
export type Probe = (url: string) => Promise<ProbeResult>;

export interface WaitOptions {
  attempts?: number;
  delayMs?: number;
  probe?: Probe;
  sleep?: (ms: number) => Promise<void>;
}

const defaultProbe: Probe = (url) => fetch(url).then((r) => ({ ok: r.ok, status: r.status }));
const defaultSleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/** True once GET /api/health answers 200; false if it never does within `attempts` tries. */
export async function waitForBackend(opts: WaitOptions = {}): Promise<boolean> {
  const attempts = opts.attempts ?? 40;
  const delayMs = opts.delayMs ?? 500;
  const probe = opts.probe ?? defaultProbe;
  const sleep = opts.sleep ?? defaultSleep;
  for (let i = 0; i < attempts; i++) {
    try {
      const result = await probe('/api/health');
      if (result.ok) return true;
    } catch {
      // not answering yet: try again
    }
    if (i < attempts - 1) await sleep(delayMs);
  }
  return false;
}

/** React Query's retry rule: retry network failures and 5xx a few times; never a 4xx (the request itself is wrong). */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= 4) return false;
  const status = (error as { response?: { status?: number } } | null)?.response?.status;
  return status === undefined || status >= 500;
}

/** The wait before retry number `attempt` (0-based): 500 ms, 1 s, 2 s, then 4 s at most. */
export function retryDelay(attempt: number): number {
  return Math.min(500 * 2 ** attempt, 4000);
}
