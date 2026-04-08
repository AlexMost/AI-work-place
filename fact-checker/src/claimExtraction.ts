import { ChatOpenAI } from '@langchain/openai';
import { ExtractedClaimsSchema, type ExtractedClaim } from './textSchemas';

const STRICT_SOURCE_TEXT_PROMPT = [
  'Extract the check-worthy claims from the input text.',
  'Return only an array of objects with `claim` and `sourceText`.',
  'The `sourceText` value must be an exact unchanged substring copied from the input text.',
  'Do not normalize quotes, punctuation, spacing, casing, or word order.',
  'If you cannot copy an exact substring for a claim, omit that claim entirely.',
].join(' ');

function isExactSourceTextMatch(text: string, sourceText: string): boolean {
  return text.includes(sourceText);
}

export async function extractClaimsFromText(text: string): Promise<ExtractedClaim[]> {
  const model = new ChatOpenAI({
    model: 'gpt-5.4',
    temperature: 0,
  });

  const extractor = model.withStructuredOutput(ExtractedClaimsSchema);
  const extractedClaims = ExtractedClaimsSchema.parse(
    await extractor.invoke([
      {
        role: 'system',
        content: STRICT_SOURCE_TEXT_PROMPT,
      },
      {
        role: 'user',
        content: text,
      },
    ])
  );

  return extractedClaims.filter(({ sourceText }) => isExactSourceTextMatch(text, sourceText));
}
