# Text Claim Fact-Checking Design

## Overview

This document describes how to evolve the current `fact-checker` from checking a single claim into processing a full input text. The new flow should:

1. accept a raw text input;
2. extract only factual claims worth checking;
3. map each extracted claim back to its exact source span in the original text;
4. verify each claim with the existing fact-checking graph;
5. return grouped results for future UI highlighting.

The design preserves the current single-claim verification pipeline and adds a new orchestration layer for full-text processing.

## Current Project Context

The repository currently contains:

- `src/factCheck.ts` with `checkFact(claim)` for checking one claim;
- `src/graph.ts` with a LangGraph agent that verifies a claim using Wikipedia tools;
- `src/tools.ts` with English and Ukrainian Wikipedia search and retrieval tools;
- `src/index.ts` as a simple entry point for local experimentation.

Today the system expects one claim string. It does not extract claims from longer text and does not return source positions.

## Goals

- Add a top-level text-processing API for full input passages.
- Extract only factual claims that are worth verification.
- Return exact `start` and `end` offsets for each extracted item whenever possible.
- Preserve `SUPPORTED`, `REFUTED`, and `NOT_ENOUGH_INFO` outcomes.
- Shape the result so a future UI can highlight exact fragments in the original text.

## Non-Goals

- Building the UI itself.
- Introducing non-Wikipedia sources in this iteration.
- Solving fuzzy paraphrase alignment beyond a minimal fallback.
- Replacing the existing single-claim verification graph.

## Recommended Approach

Use a two-stage pipeline:

1. an extraction step asks an LLM to identify check-worthy claims from the input text;
2. an orchestration step maps those claims back to the original text and verifies them one by one with the existing graph.

This is preferred over sentence-based checking because one sentence may contain multiple claims or no factual claim at all. It is also preferred over LLM-generated offsets because symbol indices from the model are brittle.

## Claim Extraction Contract

The extraction step must return structured items in this shape:

```ts
type ExtractedClaim = {
  claim: string;
  sourceText: string;
};
```

### Contract Requirements

- `claim` is a short, checkable factual statement suitable for verification.
- `sourceText` is the exact fragment from the original input text from which the claim was derived.
- `sourceText` must be a literal, unchanged substring of the original text.
- `sourceText` must not be paraphrased, cleaned up, normalized, spell-corrected, re-punctuated, re-cased, or otherwise modified.
- If the model cannot provide an exact `sourceText` span from the original input, it must omit that claim entirely.

### What Counts As A Claim

The extractor should include statements that assert facts about:

- people, organizations, places, works, events, dates, roles, authorship, ownership, counts, locations, or historical relationships;
- assertions that can plausibly be supported or refuted using encyclopedia-style sources.

The extractor should exclude:

- opinions, emotional statements, or rhetorical language;
- vague value judgments without a factual core;
- calls to action, jokes, greetings, or filler text;
- fragments that are too ambiguous to verify.

## Extraction Prompt Guidance

The extractor prompt should strongly enforce the contract above. It should explicitly say:

- extract only factual claims worth checking;
- return a structured array;
- for every result, `sourceText` must be copied exactly from the input text;
- do not alter quotes, punctuation, spaces, casing, or word order in `sourceText`;
- if an exact fragment cannot be copied from the input text, do not include the item.

The extraction model may normalize `claim` slightly for clarity, but it must preserve meaning.

## Text Location Strategy

After extraction, the code should locate each `sourceText` in the original input text and compute offsets.

```ts
type LocatedClaim = {
  claim: string;
  sourceText: string;
  start: number | null;
  end: number | null;
};
```

### Matching Rules

1. Attempt an exact substring match for `sourceText` in the original input.
2. If there is a single match, use it.
3. If there are multiple matches, use the first match that has not already been assigned to another extracted claim with the same source fragment.
4. If no exact match exists, mark `start` and `end` as `null`.

This design intentionally relies on `sourceText`, not `claim`, because `claim` may be slightly normalized while `sourceText` is expected to remain exact.

## Verification Flow

The current `checkFact(claim)` logic should remain the single-claim verifier. A new top-level function should orchestrate text processing.

```ts
type FactCheckItem = {
  claim: string;
  sourceText: string;
  start: number | null;
  end: number | null;
  explanation: string;
};

type TextFactCheckResult = {
  supported: FactCheckItem[];
  refuted: FactCheckItem[];
  notEnoughInfo: FactCheckItem[];
};
```

### Processing Steps

1. `extractClaimsFromText(text)` returns `ExtractedClaim[]`.
2. `locateExtractedClaims(text, claims)` returns `LocatedClaim[]`.
3. For each located claim, call `checkFact(claim)`.
4. Merge the verification result with `sourceText`, `start`, and `end`.
5. Group each item into:
   - `supported`
   - `refuted`
   - `notEnoughInfo`

## Error Handling

The text-level flow should be resilient and should not fail the entire request because one item cannot be processed.

### Expected Cases

- If extraction returns no claims, return empty arrays.
- If `sourceText` cannot be located, still keep the item and place it into `notEnoughInfo` if verification cannot proceed safely or if the UI contract allows unresolved offsets.
- If the single-claim checker fails for one item because of a model or tool error, convert that item into `notEnoughInfo` with a technical explanation instead of throwing for the entire text.
- If the same `sourceText` appears multiple times, assign matches deterministically in input order.

## LangGraph Impact

The existing verification graph can remain focused on one claim. The new extraction and orchestration logic does not need to replace it.

The recommended architecture is:

- keep `src/graph.ts` as the single-claim reasoning graph;
- keep `src/factCheck.ts` or split it so one module owns single-claim checking;
- add a new extraction module for structured claim extraction;
- add a new text-level orchestration module for `checkText(text)`.

This separation keeps responsibilities clear:

- extraction decides what to verify;
- location computes offsets;
- verification decides the verdict;
- orchestration groups the final response.

## Testing Strategy

This change should be implemented with tests first.

### Unit Tests

- extraction schema parsing;
- filtering and handling of invalid extractor output;
- exact `sourceText` location to `start/end`;
- duplicate `sourceText` assignment behavior;
- grouping of verified items into `supported`, `refuted`, and `notEnoughInfo`.

### Integration Tests

- one end-to-end text flow with mocked extraction output and mocked verdicts;
- one case where `sourceText` is not found and offsets become `null`;
- one case where verification for a single claim fails and the item is downgraded to `notEnoughInfo`.

## Example Result Shape

```ts
{
  supported: [
    {
      claim: "Paris is the capital of France.",
      sourceText: "Paris is the capital of France",
      start: 0,
      end: 31,
      explanation: "Wikipedia confirms that Paris is the capital city of France."
    }
  ],
  refuted: [],
  notEnoughInfo: []
}
```

## Implementation Notes

- The public API should expose a text-level entry point distinct from single-claim checking.
- Offsets should be based on JavaScript string indices so they are predictable for a TypeScript UI.
- The result format should stay stable and explicit, even if the internal verification graph evolves later.

## Risks

- Claim extraction quality depends on the model following the `sourceText` contract.
- Long inputs may increase latency because each extracted claim triggers a separate verification run.
- Wikipedia-only verification may produce `NOT_ENOUGH_INFO` for niche or recent claims.

## Decision Summary

The agreed design is:

- use an LLM to extract only factual, check-worthy claims;
- require the extractor to return an exact original `sourceText` fragment for every claim;
- compute offsets in code by matching `sourceText` back into the original text;
- verify each claim with the existing single-claim LangGraph pipeline;
- return grouped `supported`, `refuted`, and `notEnoughInfo` arrays for future UI integration.
