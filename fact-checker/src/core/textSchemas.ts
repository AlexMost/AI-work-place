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

export const ExtractClaimsResponseSchema = z.object({
  claims: ExtractedClaimsSchema,
});

export const LocatedClaimSchema = ExtractedClaimSchema.extend({
  start: z.number().int().nonnegative().nullable(),
  end: z.number().int().nonnegative().nullable(),
})
  .refine((value) => (value.start === null) === (value.end === null), {
    message: 'start and end must both be null or both be numbers',
    path: ['end'],
  })
  .refine((value) => value.start === null || value.end === null || value.end >= value.start, {
    message: 'end must be greater than or equal to start',
    path: ['end'],
  });

export type ExtractedClaim = z.infer<typeof ExtractedClaimSchema>;
export type LocatedClaim = z.infer<typeof LocatedClaimSchema>;
