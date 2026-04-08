import { beforeEach, describe, expect, it, vi } from 'vitest';

const { graphInvoke, structuredInvoke } = vi.hoisted(() => ({
  graphInvoke: vi.fn(),
  structuredInvoke: vi.fn(),
}));

vi.mock('../src/core/graph', () => ({
  createGraph: () => ({
    invoke: graphInvoke,
  }),
}));

vi.mock('@langchain/openai', () => ({
  ChatOpenAI: class {
    withStructuredOutput() {
      return {
        invoke: structuredInvoke,
      };
    }
  },
}));

import { checkFact } from '../src/core/factCheck';

const TEST_API_KEY = 'test-key';

describe('checkFact', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('extracts a verdict from plain string output', async () => {
    const verdict = {
      verdict: 'SUPPORTED',
      explanation: 'Confirmed.',
    } as const;

    graphInvoke.mockResolvedValueOnce({
      messages: [{ content: 'Verdict: SUPPORTED\nExplanation: Confirmed.' }],
    });
    structuredInvoke.mockResolvedValueOnce(verdict);

    await expect(checkFact('Kyiv is the capital of Ukraine.', TEST_API_KEY)).resolves.toEqual(verdict);
    expect(structuredInvoke).toHaveBeenCalledWith(
      'Extract the fact-check verdict from this text:\n\nVerdict: SUPPORTED\nExplanation: Confirmed.'
    );
  });

  it('extracts text from structured content blocks', async () => {
    const verdict = {
      verdict: 'REFUTED',
      explanation: 'The evidence contradicts the claim.',
    } as const;

    graphInvoke.mockResolvedValueOnce({
      messages: [
        {
          content: [
            { type: 'text', text: 'Verdict: REFUTED' },
            { type: 'text', text: 'Explanation: The evidence contradicts the claim.' },
          ],
        },
      ],
    });
    structuredInvoke.mockResolvedValueOnce(verdict);

    await expect(checkFact('Berlin is the capital of France.', TEST_API_KEY)).resolves.toEqual(verdict);
    expect(structuredInvoke).toHaveBeenCalledWith(
      'Extract the fact-check verdict from this text:\n\nVerdict: REFUTED\nExplanation: The evidence contradicts the claim.'
    );
  });
});
