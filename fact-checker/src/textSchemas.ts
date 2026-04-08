import { z } from 'zod';

const MEANINGFUL_SOURCE_TEXT_RE = /[\p{L}\p{N}]/u;

export const ExtractedClaimSchema = z.object({
  claim: z
    .string()
    .min(1)
    .refine((value) => MEANINGFUL_SOURCE_TEXT_RE.test(value), {
      message: 'claim must contain at least one letter or number',
    }),
  sourceText: z
    .string()
    .min(1)
    .refine((value) => MEANINGFUL_SOURCE_TEXT_RE.test(value), {
      message: 'sourceText must contain at least one letter or number',
    }),
});

export const ExtractedClaimsSchema = z.array(ExtractedClaimSchema);

const NullLocatedClaimSchema = ExtractedClaimSchema.extend({
  start: z.null(),
  end: z.null(),
});

const RangedLocatedClaimSchema = ExtractedClaimSchema.extend({
  start: z.number().int().nonnegative(),
  end: z.number().int().nonnegative(),
}).refine((value) => value.end >= value.start, {
  message: 'end must be greater than or equal to start',
  path: ['end'],
});

export const LocatedClaimSchema = z.union([NullLocatedClaimSchema, RangedLocatedClaimSchema]);

export type ExtractedClaim = z.infer<typeof ExtractedClaimSchema>;
export type LocatedClaim = z.infer<typeof LocatedClaimSchema>;
