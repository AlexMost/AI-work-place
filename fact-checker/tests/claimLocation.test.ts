import { describe, expect, it } from 'vitest';
import { locateExtractedClaims } from '../src/core/claimLocation';
import { LocatedClaimSchema } from '../src/core/textSchemas';

describe('locateExtractedClaims', () => {
  it('maps exact sourceText to start and end offsets', () => {
    const text = 'Paris is the capital of France.';
    const result = locateExtractedClaims(text, [
      {
        claim: 'Paris is the capital of France.',
        sourceText: 'Paris is the capital of France',
      },
    ]);

    expect(result).toEqual([
      {
        claim: 'Paris is the capital of France.',
        sourceText: 'Paris is the capital of France',
        start: 0,
        end: 30,
      },
    ]);
  });

  it('uses the first unassigned match when sourceText repeats', () => {
    const text = 'Kyiv is in Ukraine. Kyiv is the capital of Ukraine.';
    const result = locateExtractedClaims(text, [
      { claim: 'Kyiv is in Ukraine.', sourceText: 'Kyiv is' },
      { claim: 'Kyiv is the capital of Ukraine.', sourceText: 'Kyiv is' },
    ]);

    expect(result[0]).toMatchObject({ start: 0, end: 7 });
    expect(result[1]).toMatchObject({ start: 20, end: 27 });
  });

  it('allows nested claims that share the same start offset', () => {
    const text = 'Paris is the capital of France.';
    const result = locateExtractedClaims(text, [
      { claim: 'Paris is the capital.', sourceText: 'Paris is the capital' },
      {
        claim: 'Paris is the capital of France.',
        sourceText: 'Paris is the capital of France',
      },
    ]);

    expect(result[0]).toMatchObject({ start: 0, end: 20 });
    expect(result[1]).toMatchObject({ start: 0, end: 30 });
  });

  it('returns null offsets when sourceText is not found in text', () => {
    const text = 'Paris is the capital of France.';
    const result = locateExtractedClaims(text, [
      {
        claim: 'Kyiv is the capital of Ukraine.',
        sourceText: 'Kyiv is the capital of Ukraine.',
      },
    ]);

    expect(result).toEqual([
      {
        claim: 'Kyiv is the capital of Ukraine.',
        sourceText: 'Kyiv is the capital of Ukraine.',
        start: null,
        end: null,
      },
    ]);
  });

  it('returns null for claims beyond the available identical matches', () => {
    const text = 'Kyiv is in Ukraine. Kyiv is in Ukraine.';
    const result = locateExtractedClaims(text, [
      { claim: 'Kyiv is in Ukraine.', sourceText: 'Kyiv is in Ukraine.' },
      { claim: 'Kyiv is in Ukraine.', sourceText: 'Kyiv is in Ukraine.' },
      { claim: 'Kyiv is in Ukraine.', sourceText: 'Kyiv is in Ukraine.' },
    ]);

    expect(result).toEqual([
      {
        claim: 'Kyiv is in Ukraine.',
        sourceText: 'Kyiv is in Ukraine.',
        start: 0,
        end: 19,
      },
      {
        claim: 'Kyiv is in Ukraine.',
        sourceText: 'Kyiv is in Ukraine.',
        start: 20,
        end: 39,
      },
      {
        claim: 'Kyiv is in Ukraine.',
        sourceText: 'Kyiv is in Ukraine.',
        start: null,
        end: null,
      },
    ]);
  });

  it('rejects impossible located claim states', () => {
    expect(
      LocatedClaimSchema.safeParse({
        claim: 'Paris is the capital of France.',
        sourceText: 'Paris is the capital of France',
        start: null,
        end: 5,
      }).success
    ).toBe(false);

    expect(
      LocatedClaimSchema.safeParse({
        claim: 'Paris is the capital of France.',
        sourceText: 'Paris is the capital of France',
        start: 10,
        end: 5,
      }).success
    ).toBe(false);
  });
});
