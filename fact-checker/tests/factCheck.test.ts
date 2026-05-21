import { beforeEach, describe, expect, it, vi } from 'vitest';

const { graphInvoke } = vi.hoisted(() => ({
  graphInvoke: vi.fn(),
}));

vi.mock('../src/core/graph', () => ({
  createGraph: () => ({
    invoke: graphInvoke,
  }),
}));

import { checkFact } from '../src/core/factCheck';

const TEST_API_KEY = 'test-key';

describe('checkFact', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns the verdict produced by the graph', async () => {
    const verdict = {
      verdict: 'SUPPORTED' as const,
      explanation: 'Confirmed.',
    };
    graphInvoke.mockResolvedValueOnce({
      messages: [{ content: 'Kyiv is the capital of Ukraine.' }],
      verdict,
    });

    await expect(checkFact('Kyiv is the capital of Ukraine.', TEST_API_KEY)).resolves.toEqual(
      verdict
    );
    expect(graphInvoke).toHaveBeenCalledWith({
      messages: [{ role: 'user', content: 'Kyiv is the capital of Ukraine.' }],
    });
  });

  it('propagates a refuted verdict verbatim', async () => {
    const verdict = {
      verdict: 'REFUTED' as const,
      explanation: 'Wikipedia says Paris is the capital of France.',
    };
    graphInvoke.mockResolvedValueOnce({
      messages: [{ content: 'Berlin is the capital of France.' }],
      verdict,
    });

    await expect(checkFact('Berlin is the capital of France.', TEST_API_KEY)).resolves.toEqual(
      verdict
    );
  });

  it('throws when the graph produced no verdict', async () => {
    graphInvoke.mockResolvedValueOnce({
      messages: [{ content: 'something' }],
      verdict: null,
    });

    await expect(checkFact('Unknown claim.', TEST_API_KEY)).rejects.toThrow(
      'Graph did not produce a verdict'
    );
  });
});
