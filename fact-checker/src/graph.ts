import 'dotenv/config';
import { ChatOpenAI } from '@langchain/openai';
import { StateGraph, MessagesAnnotation, END } from '@langchain/langgraph';
import { ToolNode } from '@langchain/langgraph/prebuilt';
import { AIMessage } from '@langchain/core/messages';
import { searchWikipedia, getPageSummary, getPageFullContent, searchWikipediaUk, getPageSummaryUk, getPageFullContentUk } from './tools';

const tools = [searchWikipedia, getPageSummary, getPageFullContent, searchWikipediaUk, getPageSummaryUk, getPageFullContentUk];
const llm = new ChatOpenAI({ model: 'gpt-5.4-mini' }).bindTools(tools);

const SYSTEM_PROMPT = `Ти — перевіряч фактів. Тебе подано твердження українською мовою.

Алгоритм:
1. Визнач тему твердження:
   - Якщо тема пов'язана з Україною, українськими людьми, містами, подіями, географією — використовуй ТІЛЬКИ українські тули: search_wikipedia_uk → get_page_summary_uk → get_full_content_uk (якщо потрібно більше)
   - Для всіх інших тем — використовуй англійські тули: search_wikipedia → get_page_summary → get_full_content (якщо потрібно більше)
2. Порівняй знайдене з твердженням
3. Винеси вердикт

Формат відповіді:
Вердикт: SUPPORTED / REFUTED / NOT ENOUGH INFO
Пояснення: (коротко чому, з посиланням на знайдений факт)`;

async function agent(state: typeof MessagesAnnotation.State) {
  const response = await llm.invoke([
    { role: 'system', content: SYSTEM_PROMPT },
    ...state.messages,
  ]);
  return { messages: [response] };
}

const toolNode = new ToolNode(tools);

function shouldContinue(state: typeof MessagesAnnotation.State) {
  const last = state.messages.at(-1) as AIMessage;
  return last.tool_calls?.length ? 'tools' : END;
}

export const graph = new StateGraph(MessagesAnnotation)
  .addNode('agent', agent)
  .addNode('tools', toolNode)
  .addEdge('__start__', 'agent')
  .addConditionalEdges('agent', shouldContinue)
  .addEdge('tools', 'agent')
  .compile();
