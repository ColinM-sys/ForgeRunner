// node --test frontend/test/backendReady.test.ts  (Node 23.6+ runs TypeScript directly)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { waitForBackend, shouldRetry, retryDelay } from '../src/api/backendReady.ts';

const noSleep = async () => {};

test('waits through connection errors until /api/health answers 200', async () => {
  const urls: string[] = [];
  let calls = 0;
  const probe = async (url: string) => {
    urls.push(url);
    calls += 1;
    if (calls <= 3) throw new TypeError('fetch failed');
    return { ok: true, status: 200 };
  };
  assert.equal(await waitForBackend({ probe, sleep: noSleep, delayMs: 1 }), true);
  assert.equal(calls, 4);
  assert.ok(urls.every((u) => u === '/api/health'));
});

test('a 500 from the health check is not ready yet', async () => {
  let calls = 0;
  const probe = async () => {
    calls += 1;
    return calls < 3 ? { ok: false, status: 500 } : { ok: true, status: 200 };
  };
  assert.equal(await waitForBackend({ probe, sleep: noSleep }), true);
  assert.equal(calls, 3);
});

test('gives up after the attempts, and says so', async () => {
  let calls = 0;
  const probe = async () => {
    calls += 1;
    throw new Error('down');
  };
  assert.equal(await waitForBackend({ probe, attempts: 5, sleep: noSleep }), false);
  assert.equal(calls, 5);
});

test('waits between attempts, and not after the last one', async () => {
  const waits: number[] = [];
  const sleep = async (ms: number) => {
    waits.push(ms);
  };
  await waitForBackend({ probe: async () => ({ ok: false, status: 503 }), attempts: 3, delayMs: 250, sleep });
  assert.deepEqual(waits, [250, 250]);
});

test('retries network failures and server errors, a few times', () => {
  assert.equal(shouldRetry(0, new TypeError('network')), true);
  assert.equal(shouldRetry(1, { response: { status: 500 } }), true);
  assert.equal(shouldRetry(3, { response: { status: 503 } }), true);
  assert.equal(shouldRetry(4, { response: { status: 500 } }), false, 'the fifth failure is final');
});

test('never retries a client error: the request itself is wrong', () => {
  for (const status of [400, 401, 403, 404, 422]) {
    assert.equal(shouldRetry(0, { response: { status } }), false, String(status));
  }
});

test('the wait grows and is capped at 4 seconds', () => {
  assert.deepEqual([0, 1, 2, 3, 4, 9].map(retryDelay), [500, 1000, 2000, 4000, 4000, 4000]);
});
