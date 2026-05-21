import { beforeEach, describe, expect, it, vi } from 'vitest';

const { extractClaimsFromText, checkFact } = vi.hoisted(() => ({
  extractClaimsFromText: vi.fn(),
  checkFact: vi.fn(),
}));

vi.mock('../src/core/claimExtraction', () => ({
  extractClaimsFromText,
}));

vi.mock('../src/core/factCheck', async () => {
  const actual =
    await vi.importActual<typeof import('../src/core/factCheck')>('../src/core/factCheck');

  return {
    ...actual,
    checkFact,
  };
});

import { checkText } from '../src/core/checkText';

const TEST_API_KEY = 'test-key';

describe('checkText', () => {
  const originalDebug = process.env.FACT_CHECKER_DEBUG;

  beforeEach(() => {
    vi.clearAllMocks();
    if (originalDebug === undefined) {
      delete process.env.FACT_CHECKER_DEBUG;
    } else {
      process.env.FACT_CHECKER_DEBUG = originalDebug;
    }
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

    const result = await checkText(text, TEST_API_KEY);

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
    expect(checkFact).toHaveBeenNthCalledWith(1, 'Paris is the capital of France.', TEST_API_KEY);
    expect(checkFact).toHaveBeenNthCalledWith(2, 'Berlin is the capital of France.', TEST_API_KEY);
  });

  it('keeps unmatched sourceText claims in notEnoughInfo', async () => {
    extractClaimsFromText.mockResolvedValueOnce([
      {
        claim: 'Kyiv is the capital of Ukraine.',
        sourceText: 'Kyiv is the capital of Ukraine',
      },
    ]);

    const result = await checkText('Paris is the capital of France.', TEST_API_KEY);

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

    const result = await checkText('The population of Atlantis is 1 million.', TEST_API_KEY);

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

    await expect(checkText('Kyiv is the capital of Ukraine.', TEST_API_KEY)).resolves.toEqual({
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

  it('checks matched claims in parallel', async () => {
    const resolvers: Array<(value: { verdict: 'SUPPORTED'; explanation: string }) => void> = [];

    extractClaimsFromText.mockResolvedValueOnce([
      {
        claim: 'Paris is the capital of France.',
        sourceText: 'Paris is the capital of France',
      },
      {
        claim: 'Kyiv is the capital of Ukraine.',
        sourceText: 'Kyiv is the capital of Ukraine',
      },
    ]);
    checkFact.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvers.push(resolve);
        })
    );

    const pendingResult = checkText(
      'Paris is the capital of France. Kyiv is the capital of Ukraine.',
      TEST_API_KEY
    );

    await Promise.resolve();

    expect(checkFact).toHaveBeenCalledTimes(2);

    resolvers[1]!({
      verdict: 'SUPPORTED',
      explanation: 'Confirmed for Kyiv.',
    });
    resolvers[0]!({
      verdict: 'SUPPORTED',
      explanation: 'Confirmed for Paris.',
    });

    await expect(pendingResult).resolves.toEqual({
      supported: [
        {
          claim: 'Paris is the capital of France.',
          sourceText: 'Paris is the capital of France',
          start: 0,
          end: 30,
          explanation: 'Confirmed for Paris.',
        },
        {
          claim: 'Kyiv is the capital of Ukraine.',
          sourceText: 'Kyiv is the capital of Ukraine',
          start: 32,
          end: 62,
          explanation: 'Confirmed for Kyiv.',
        },
      ],
      refuted: [],
      notEnoughInfo: [],
    });
  });

  it('emits stage logs in debug mode', async () => {
    process.env.FACT_CHECKER_DEBUG = '1';
    const debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});

    extractClaimsFromText.mockResolvedValueOnce([
      {
        claim: 'Paris is the capital of France.',
        sourceText: 'Paris is the capital of France',
      },
    ]);
    checkFact.mockResolvedValueOnce({
      verdict: 'SUPPORTED',
      explanation: 'Confirmed by Wikipedia.',
    });

    await checkText('Paris is the capital of France.', TEST_API_KEY);

    expect(debugSpy.mock.calls.every((args) => args.length === 1)).toBe(true);
    expect(
      debugSpy.mock.calls.some(
        ([message]) => typeof message === 'string' && message.includes('extract:start')
      )
    ).toBe(true);
    expect(
      debugSpy.mock.calls.some(
        ([message]) => typeof message === 'string' && message.includes('extract:done')
      )
    ).toBe(true);
    expect(
      debugSpy.mock.calls.some(
        ([message]) => typeof message === 'string' && message.includes('locate:done')
      )
    ).toBe(true);
    expect(
      debugSpy.mock.calls.some(
        ([message]) => typeof message === 'string' && message.includes('claim:check:start')
      )
    ).toBe(true);
    expect(
      debugSpy.mock.calls.some(
        ([message]) => typeof message === 'string' && message.includes('claim:check:done')
      )
    ).toBe(true);
    expect(
      debugSpy.mock.calls.some(
        ([message]) => typeof message === 'string' && message.includes('result:summary')
      )
    ).toBe(true);

    debugSpy.mockRestore();
  });

  it('does not emit stage logs when debug mode is disabled', async () => {
    delete process.env.FACT_CHECKER_DEBUG;
    const debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});

    extractClaimsFromText.mockResolvedValueOnce([
      {
        claim: 'Paris is the capital of France.',
        sourceText: 'Paris is the capital of France',
      },
    ]);
    checkFact.mockResolvedValueOnce({
      verdict: 'SUPPORTED',
      explanation: 'Confirmed by Wikipedia.',
    });

    await checkText('Paris is the capital of France.', TEST_API_KEY);

    expect(debugSpy).not.toHaveBeenCalled();
    debugSpy.mockRestore();
  });
});
