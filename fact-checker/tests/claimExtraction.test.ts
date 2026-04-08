import { beforeEach, describe, expect, it, vi } from 'vitest';

const { chatOpenAiCtor, structuredInvoke, withStructuredOutput } = vi.hoisted(() => {
  const structuredInvoke = vi.fn();
  const withStructuredOutput = vi.fn(() => ({
    invoke: structuredInvoke,
  }));
  const chatOpenAiCtor = vi.fn(() => ({
    withStructuredOutput,
  }));

  return { chatOpenAiCtor, structuredInvoke, withStructuredOutput };
});

vi.mock('@langchain/openai', () => ({
  ChatOpenAI: chatOpenAiCtor,
}));

import { extractClaimsFromText } from '../src/core/claimExtraction';

describe('extractClaimsFromText', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns parsed extracted claims from structured output', async () => {
    structuredInvoke.mockResolvedValueOnce({
      claims: [
        {
          claim: 'Paris is the capital of France.',
          sourceText: 'Paris is the capital of France',
        },
      ],
    });

    await expect(
      extractClaimsFromText('Paris is the capital of France.')
    ).resolves.toEqual([
      {
        claim: 'Paris is the capital of France.',
        sourceText: 'Paris is the capital of France',
      },
    ]);
  });

  it('sends isolated system and user messages to the model', async () => {
    const text = 'She wrote: "Paris is the Capital of France."\nThen left.';
    structuredInvoke.mockResolvedValueOnce({
      claims: [
        {
          claim: 'She wrote that Paris is the capital of France.',
          sourceText: '"Paris is the Capital of France."\n',
        },
      ],
    });

    await expect(extractClaimsFromText(text)).resolves.toEqual([
      {
        claim: 'She wrote that Paris is the capital of France.',
        sourceText: '"Paris is the Capital of France."\n',
      },
    ]);

    expect(structuredInvoke).toHaveBeenCalledTimes(1);
    expect(structuredInvoke).toHaveBeenCalledWith([
      expect.objectContaining({
        role: 'system',
        content: expect.stringContaining('exact unchanged substring'),
      }),
      expect.objectContaining({
        role: 'user',
        content: text,
      }),
    ]);

    const schema = withStructuredOutput.mock.calls[0]?.[0];
    expect(schema?.safeParse({ claims: [] }).success).toBe(true);
    expect(schema?.safeParse([]).success).toBe(false);
  });

  it('rejects malformed structured output', async () => {
    structuredInvoke.mockResolvedValueOnce({
      claims: [
        {
          claim: 'Paris is the capital of France.',
          sourceText: '',
        },
      ],
    });

    await expect(
      extractClaimsFromText('Paris is the capital of France.')
    ).rejects.toThrow();
  });

  it('rejects malformed claim values', async () => {
    structuredInvoke.mockResolvedValueOnce({
      claims: [
        {
          claim: '   ',
          sourceText: 'Paris',
        },
        {
          claim: '!!!',
          sourceText: 'Paris',
        },
      ],
    });

    await expect(
      extractClaimsFromText('Paris is the capital of France.')
    ).rejects.toThrow();
  });

  it('omits claims whose sourceText is not an exact substring', async () => {
    structuredInvoke.mockResolvedValueOnce({
      claims: [
        {
          claim: 'Paris is the capital of France.',
          sourceText: 'Paris is the capital of France',
        },
        {
          claim: 'France is in Europe.',
          sourceText: 'France is in Europe',
        },
      ],
    });

    await expect(
      extractClaimsFromText('Paris is the capital of France.')
    ).resolves.toEqual([
      {
        claim: 'Paris is the capital of France.',
        sourceText: 'Paris is the capital of France',
      },
    ]);
  });

  it('rejects degenerate exact substrings', async () => {
    structuredInvoke.mockResolvedValueOnce({
      claims: [
        {
          claim: 'Whitespace only.',
          sourceText: '   ',
        },
        {
          claim: 'Punctuation only.',
          sourceText: '!!!',
        },
      ],
    });

    await expect(
      extractClaimsFromText('Paris is the capital of France.')
    ).rejects.toThrow();
  });
});
