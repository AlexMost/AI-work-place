import { ChatOpenAI } from '@langchain/openai';
import { StateGraph, MessagesAnnotation, END } from '@langchain/langgraph';
import { ToolNode } from '@langchain/langgraph/prebuilt';
import { AIMessage } from '@langchain/core/messages';
import { searchWikipedia, getPageSummary, getPageFullContent } from './tools';

const tools = [searchWikipedia, getPageSummary, getPageFullContent];
const llm = new ChatOpenAI({ model: 'gpt-5.4-mini' }).bindTools(tools);

const SYSTEM_PROMPT = `Ти — перевіряч фактів. Тебе подано твердження українською мовою.

Алгоритм:
1. Знайди релевантні статті у Wikipedia через search_wikipedia (шукай АНГЛІЙСЬКОЮ)
2. Отримай зміст через get_page_summary
3. Якщо summary недостатньо — використай get_full_content як fallback
4. Порівняй знайдене з твердженням
5. Винеси вердикт

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
