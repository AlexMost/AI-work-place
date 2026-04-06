import { z } from 'zod';
import { graph } from './graph';
import { ChatOpenAI } from '@langchain/openai';

const VerdictSchema = z.object({
  verdict: z.enum(['SUPPORTED', 'REFUTED', 'NOT_ENOUGH_INFO']),
  explanation: z.string(),
});

type FactCheckResult = z.infer<typeof VerdictSchema>;

const structuredLlm = new ChatOpenAI({ model: 'gpt-5.4-mini' }).withStructuredOutput(VerdictSchema);

export async function checkFact(claim: string): Promise<FactCheckResult> {
  const result = await graph.invoke({
    messages: [{ role: 'user', content: claim }],
  });

  const lastMessage = result.messages.at(-1);
  if (!lastMessage) {
    throw new Error('No result');
  }
  const finalMessage = lastMessage.content as string;

  return structuredLlm.invoke(`Extract the fact-check verdict from this text:\n\n${finalMessage}`);
}
