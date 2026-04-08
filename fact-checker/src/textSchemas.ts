import { z } from 'zod';

export const ExtractedClaimSchema = z.object({
  claim: z.string().min(1),
  sourceText: z.string().min(1),
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
