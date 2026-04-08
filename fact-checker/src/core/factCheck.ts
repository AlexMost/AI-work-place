import { z } from 'zod';
import { createGraph } from './graph';
import { ChatOpenAI } from '@langchain/openai';

export const VerdictSchema = z.object({
  verdict: z.enum(['SUPPORTED', 'REFUTED', 'NOT_ENOUGH_INFO']),
  explanation: z.string(),
});

export type FactCheckVerdict = z.infer<typeof VerdictSchema>['verdict'];
export type FactCheckResult = z.infer<typeof VerdictSchema>;

function extractTextFromContent(content: unknown): string {
  if (typeof content === 'string') {
    return content;
  }

  if (Array.isArray(content)) {
    const parts = content
      .map((item) => extractTextFromContent(item))
      .filter((value) => value.length > 0);

    if (parts.length > 0) {
      return parts.join('\n');
    }
  }

  if (content && typeof content === 'object') {
    if ('text' in content && typeof content.text === 'string') {
      return content.text;
    }

    if ('content' in content) {
      const nestedContent = extractTextFromContent(content.content);
      if (nestedContent.length > 0) {
        return nestedContent;
      }
    }
  }

  return '';
}

export async function checkFact(claim: string, apiKey: string): Promise<FactCheckResult> {
  const graph = createGraph(apiKey);

  const result = await graph.invoke({
    messages: [{ role: 'user', content: claim }],
  });

  const lastMessage = result.messages.at(-1);
  if (!lastMessage) {
    throw new Error('No result');
  }
  const finalMessage = extractTextFromContent(lastMessage.content);

  const structuredLlm = new ChatOpenAI({ model: 'gpt-5.4-mini', apiKey }).withStructuredOutput(VerdictSchema);
  return structuredLlm.invoke(`Extract the fact-check verdict from this text:\n\n${finalMessage}`);
}
