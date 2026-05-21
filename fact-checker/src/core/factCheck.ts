import { createGraph } from './graph';
import { debugLog } from './debug';
import { VerdictSchema, type FactCheckResult, type FactCheckVerdict } from './schemas';

export { VerdictSchema };
export type { FactCheckResult, FactCheckVerdict };

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

  debugLog('factCheck:start', { claim });

  const result = await graph.invoke({
    messages: [{ role: 'user', content: claim }],
  });

  debugLog('factCheck:graph_done', { claim, messages: result.messages.length });

  result.messages.forEach((msg, i) => {
    const text = extractTextFromContent(msg.content);
    const toolCalls = (msg as { tool_calls?: unknown[] }).tool_calls;
    const toolCallSummary = Array.isArray(toolCalls)
      ? toolCalls.map((tc) => {
          const t = tc as { name?: string; args?: unknown };
          return { name: t.name, args: t.args };
        })
      : undefined;
    debugLog(`factCheck:msg[${i}]`, {
      role: msg.constructor.name,
      toolCalls: toolCallSummary,
      text: text || undefined,
    });
  });

  if (!result.verdict) {
    throw new Error('Graph did not produce a verdict');
  }

  debugLog('factCheck:verdict', { claim, verdict: result.verdict });

  return result.verdict;
}
