import { ChatOpenAI } from '@langchain/openai';
import { StateGraph, Annotation, MessagesAnnotation, END } from '@langchain/langgraph';
import { ToolNode } from '@langchain/langgraph/prebuilt';
import { AIMessage } from '@langchain/core/messages';
import {
  searchWikipedia,
  getPageSummary,
  getPageFullContent,
  searchWikipediaUk,
  getPageSummaryUk,
  getPageFullContentUk,
} from './tools';
import { VerdictSchema, type FactCheckResult } from './schemas';

const tools = [
  searchWikipedia,
  getPageSummary,
  getPageFullContent,
  searchWikipediaUk,
  getPageSummaryUk,
  getPageFullContentUk,
];

const AGENT_PROMPT = `Ти — пошуковий агент фактчекера. Тобі дають твердження українською або англійською, ти збираєш докази з Wikipedia.

Алгоритм:
1. Визнач тему. Якщо тема пов'язана з Україною, українськими людьми, містами, подіями, географією — використовуй ТІЛЬКИ українські тули (search_wikipedia_uk → get_page_summary_uk → get_full_content_uk).
   Для всіх інших тем — англомовні тули (search_wikipedia → get_page_summary → get_full_content).
2. Викликай тули, доки не маєш достатньо матеріалу для вердикту. Можна викликати кілька сторінок.
3. ВАЖЛИВО: щойно зібрав достатньо доказів — зупинись. НЕ пиши вердикт, НЕ обговорюй, НЕ підсумовуй. Просто заверши без виклику жодного тула — окремий суддя винесе фінальний вердикт по зібраних матеріалах. Можна повернути порожнє повідомлення.`;

const JUDGE_PROMPT = `Ти — суддя фактчекера. Тобі дано твердження користувача та матеріали Wikipedia, зібрані пошуковим агентом у попередніх повідомленнях.

Алгоритм:
1. Перефразуй твердження своїми словами. Особливо уважно стеж за деталями, які легко переплутати:
   - напрямок дії або стосунків (хто кого, кому, від кого);
   - числа, дати, порядкові й кількісні показники;
   - точність дієслова (наприклад, «спробував», «переконав», «здобув», «очолив» — мають різний сенс);
   - суб'єкт vs. об'єкт у посесивних конструкціях.
2. У знайдених матеріалах знайди фрагменти, дотичні до твердження. Якщо релевантного фрагмента нема — verdict=NOT_ENOUGH_INFO.
3. Винеси вердикт:
   - SUPPORTED — джерела явно підтверджують твердження (з урахуванням деталей з кроку 1).
   - REFUTED — джерела явно суперечать твердженню.
   - NOT_ENOUGH_INFO — джерела про щось дотичне, але не дають прямої відповіді на конкретне твердження.
4. У полі explanation напиши пояснення українською мовою, чітко і прямо. Уникай двозначних конструкцій («а не навпаки», «частково», «можливо»). Замість цього прямо констатуй: що каже твердження, що каже джерело, чи це збігається. Бажано процитувати ключову фразу з джерела.
5. Не суперечь сам собі: explanation має узгоджуватись із verdict.`;

const StateAnnotation = Annotation.Root({
  ...MessagesAnnotation.spec,
  verdict: Annotation<FactCheckResult | null>({
    reducer: (_prev, next) => next,
    default: () => null,
  }),
});

function shouldContinue(state: typeof StateAnnotation.State): 'tools' | 'judge' {
  const last = state.messages.at(-1) as AIMessage | undefined;
  return last?.tool_calls?.length ? 'tools' : 'judge';
}

export function createGraph(apiKey: string) {
  const agentLlm = new ChatOpenAI({ model: 'gpt-5.4-nano', apiKey }).bindTools(tools);
  const judgeLlm = new ChatOpenAI({ model: 'gpt-5.4-mini', apiKey }).withStructuredOutput(
    VerdictSchema
  );

  async function agent(state: typeof StateAnnotation.State) {
    const response = await agentLlm.invoke([
      { role: 'system', content: AGENT_PROMPT },
      ...state.messages,
    ]);
    return { messages: [response] };
  }

  async function judge(state: typeof StateAnnotation.State) {
    const verdict = await judgeLlm.invoke([
      { role: 'system', content: JUDGE_PROMPT },
      ...state.messages,
    ]);
    return { verdict };
  }

  const toolNode = new ToolNode(tools);

  return new StateGraph(StateAnnotation)
    .addNode('agent', agent)
    .addNode('tools', toolNode)
    .addNode('judge', judge)
    .addEdge('__start__', 'agent')
    .addConditionalEdges('agent', shouldContinue, {
      tools: 'tools',
      judge: 'judge',
    })
    .addEdge('tools', 'agent')
    .addEdge('judge', END)
    .compile();
}
