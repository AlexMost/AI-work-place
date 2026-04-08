import { beforeEach, describe, expect, it, vi } from 'vitest';

const { extractClaimsFromText, checkFact } = vi.hoisted(() => ({
  extractClaimsFromText: vi.fn(),
  checkFact: vi.fn(),
}));

vi.mock('../src/claimExtraction', () => ({
  extractClaimsFromText,
}));

vi.mock('../src/factCheck', async () => {
  const actual = await vi.importActual<typeof import('../src/factCheck')>('../src/factCheck');

  return {
    ...actual,
    checkFact,
  };
});

import { checkText } from '../src/checkText';

describe('checkText', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('groups supported and refuted claims with offsets', async () => {
    extractClaimsFromText.mockResolvedValueOnce([
      {
        claim: 'Paris is the capital of France.',
        sourceText: 'Paris is the capital of France',
      },
      {
        claim: 'Berlin is the capital of France.',
        sourceText: 'Berlin is the capital of France',
      },
    ]);
    checkFact.mockResolvedValueOnce({
      verdict: 'SUPPORTED',
      explanation: 'Confirmed by Wikipedia.',
    });
    checkFact.mockResolvedValueOnce({
      verdict: 'REFUTED',
      explanation: 'Wikipedia says Paris is the capital of France.',
    });

    const text = 'Paris is the capital of France. Berlin is the capital of France.';

    const result = await checkText(text);

    expect(result).toEqual({
      supported: [
        {
          claim: 'Paris is the capital of France.',
          sourceText: 'Paris is the capital of France',
          start: 0,
          end: 30,
          explanation: 'Confirmed by Wikipedia.',
        },
      ],
      refuted: [
        {
          claim: 'Berlin is the capital of France.',
          sourceText: 'Berlin is the capital of France',
          start: 32,
          end: 63,
          explanation: 'Wikipedia says Paris is the capital of France.',
        },
      ],
      notEnoughInfo: [],
    });
    expect(result).toEqual({
      supported: expect.any(Array),
      refuted: expect.any(Array),
      notEnoughInfo: expect.any(Array),
    });
    expect(checkFact).toHaveBeenNthCalledWith(1, 'Paris is the capital of France.');
    expect(checkFact).toHaveBeenNthCalledWith(2, 'Berlin is the capital of France.');
  });

  it('keeps unmatched sourceText claims in notEnoughInfo', async () => {
    extractClaimsFromText.mockResolvedValueOnce([
      {
        claim: 'Kyiv is the capital of Ukraine.',
        sourceText: 'Kyiv is the capital of Ukraine',
      },
    ]);

    const result = await checkText('Paris is the capital of France.');

    expect(result.supported).toEqual([]);
    expect(result.refuted).toEqual([]);
    expect(result.notEnoughInfo).toEqual([
      {
        claim: 'Kyiv is the capital of Ukraine.',
        sourceText: 'Kyiv is the capital of Ukraine',
        start: null,
        end: null,
        explanation: 'Could not match extracted source text back to the input text.',
      },
    ]);
    expect(checkFact).not.toHaveBeenCalled();
  });

  it('groups explicit not-enough-info verdicts without failing', async () => {
    extractClaimsFromText.mockResolvedValueOnce([
      {
        claim: 'The population of Atlantis is 1 million.',
        sourceText: 'The population of Atlantis is 1 million',
      },
    ]);
    checkFact.mockResolvedValueOnce({
      verdict: 'NOT_ENOUGH_INFO',
      explanation: 'The available evidence is inconclusive.',
    });

    const result = await checkText('The population of Atlantis is 1 million.');

    expect(result).toEqual({
      supported: [],
      refuted: [],
      notEnoughInfo: [
        {
          claim: 'The population of Atlantis is 1 million.',
          sourceText: 'The population of Atlantis is 1 million',
          start: 0,
          end: 39,
          explanation: 'The available evidence is inconclusive.',
        },
      ],
    });
    expect(checkFact).toHaveBeenCalledTimes(1);
  });

  it('degrades checker errors into notEnoughInfo instead of failing the whole text', async () => {
    extractClaimsFromText.mockResolvedValueOnce([
      {
        claim: 'Kyiv is the capital of Ukraine.',
        sourceText: 'Kyiv is the capital of Ukraine',
      },
    ]);
    checkFact.mockRejectedValueOnce(new Error('Verification failed'));

    await expect(checkText('Kyiv is the capital of Ukraine.')).resolves.toEqual({
      supported: [],
      refuted: [],
      notEnoughInfo: [
        {
          claim: 'Kyiv is the capital of Ukraine.',
          sourceText: 'Kyiv is the capital of Ukraine',
          start: 0,
          end: 30,
          explanation: 'Verification failed',
        },
      ],
    });
  });
});
