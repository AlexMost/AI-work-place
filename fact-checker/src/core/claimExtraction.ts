import { ChatOpenAI } from '@langchain/openai';
import {
  ExtractClaimsResponseSchema,
  type ExtractedClaim,
} from './textSchemas';

const STRICT_SOURCE_TEXT_PROMPT = [
  'Extract the check-worthy claims from the input text.',
  'Return only an object with a `claims` array.',
  'Each item in `claims` must be an object with `claim` and `sourceText`.',
  'The `claim` value must be a fully self-contained, verifiable statement that can be understood without any surrounding context.',
  'Always include the explicit subject (named entity) in the claim, even if the original text implies it through context, pronouns, or sentence structure.',
  'Resolve all pronouns (he, she, him, його, нього, він, вона, etc.), references (this person, the actor, etc.), and implicit subjects to the actual named entity from the text.',
  'For example, if the text is about Daniel Radcliffe and says "Народився: 23 липня 1989 року", the claim should be "Деніел Редкліфф народився 23 липня 1989 року". If the text says "Відверто говорив про проблеми з алкоголем у молодості", the claim should be "Деніел Редкліфф відверто говорив про проблеми з алкоголем у молодості".',
  'The `sourceText` value must be an exact unchanged substring copied from the input text.',
  'Do not normalize quotes, punctuation, spacing, casing, or word order in `sourceText`.',
  'If you cannot copy an exact substring for a claim, omit that claim entirely.',
].join(' ');

function isExactSourceTextMatch(text: string, sourceText: string): boolean {
  return text.includes(sourceText);
}

export async function extractClaimsFromText(text: string, apiKey: string): Promise<ExtractedClaim[]> {
  const model = new ChatOpenAI({
    model: 'gpt-5.4',
    temperature: 0,
    apiKey,
  });

  const extractor = model.withStructuredOutput(ExtractClaimsResponseSchema);
  const response = ExtractClaimsResponseSchema.parse(
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

  return response.claims.filter(({ sourceText }) => isExactSourceTextMatch(text, sourceText));
}
