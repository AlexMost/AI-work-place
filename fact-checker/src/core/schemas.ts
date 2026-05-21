import { z } from 'zod';

export const VerdictSchema = z.object({
  verdict: z.enum(['SUPPORTED', 'REFUTED', 'NOT_ENOUGH_INFO']),
  explanation: z.string(),
});

export type FactCheckVerdict = z.infer<typeof VerdictSchema>['verdict'];
export type FactCheckResult = z.infer<typeof VerdictSchema>;
