import 'dotenv/config';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import * as readline from 'node:readline/promises';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';
import { tool } from '@langchain/core/tools';
import { ChatOpenAI } from '@langchain/openai';
import { HumanMessage, AIMessage, type BaseMessage } from '@langchain/core/messages';
import { StateGraph, MessagesAnnotation, START, END } from '@langchain/langgraph';
import { ToolNode } from '@langchain/langgraph/prebuilt';

const readFile = tool(
  async ({ path: p }) => fs.readFile(p, 'utf8'),
  {
    name: 'read_file',
    description:
      'Read the contents of a given relative file path. Use this when you want to see what is inside a file. Do not use it with directory names.',
    schema: z.object({
      path: z.string().describe('The relative path of a file in the working directory.'),
    }),
  },
);

const listFiles = tool(
  async ({ path: p }) => {
    const dir = p && p.length > 0 ? p : '.';
    const entries = await fs.readdir(dir, { withFileTypes: true });
    return JSON.stringify(entries.map((e) => (e.isDirectory() ? `${e.name}/` : e.name)));
  },
  {
    name: 'list_files',
    description:
      'List files and directories at a given path. If no path is provided, lists files in the current directory.',
    schema: z.object({
      path: z.string().optional().describe('Optional relative path. Defaults to current directory.'),
    }),
  },
);

const editFile = tool(
  async ({ path: p, old_str, new_str }) => {
    if (old_str === new_str) return 'Error: old_str and new_str are identical';

    let existing: string | null = null;
    try {
      existing = await fs.readFile(p, 'utf8');
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== 'ENOENT') throw err;
    }

    if (existing === null) {
      if (old_str !== '') return `Error: file ${p} does not exist`;
      await fs.mkdir(path.dirname(p), { recursive: true });
      await fs.writeFile(p, new_str, 'utf8');
      return 'OK';
    }

    if (old_str === '') return `Error: file ${p} already exists; old_str must be non-empty`;
    if (!existing.includes(old_str)) return `Error: old_str not found in ${p}`;

    await fs.writeFile(p, existing.replace(old_str, new_str), 'utf8');
    return 'OK';
  },
  {
    name: 'edit_file',
    description:
      'Make edits to a text file. Replaces the first occurrence of old_str with new_str. If the file does not exist and old_str is empty, creates a new file with new_str as contents.',
    schema: z.object({
      path: z.string().describe('The path of the file to edit.'),
      old_str: z.string().describe('Text to search for. Empty string means create a new file.'),
      new_str: z.string().describe('Text to replace old_str with.'),
    }),
  },
);

const tools = [readFile, listFiles, editFile];

const llm = new ChatOpenAI({
  model: process.env.OPENAI_MODEL ?? 'gpt-5.4-mini',
  apiKey: process.env.OPENAI_API_KEY,
}).bindTools(tools);

const callModel = async (state: typeof MessagesAnnotation.State) => ({
  messages: [await llm.invoke(state.messages)],
});

const shouldContinue = (state: typeof MessagesAnnotation.State): 'tools' | typeof END => {
  const last = state.messages.at(-1) as AIMessage | undefined;
  return last?.tool_calls?.length ? 'tools' : END;
};

export const agent = new StateGraph(MessagesAnnotation)
  .addNode('agent', callModel)
  .addNode('tools', new ToolNode(tools))
  .addEdge(START, 'agent')
  .addConditionalEdges('agent', shouldContinue)
  .addEdge('tools', 'agent')
  .compile();

async function repl() {
  if (!process.env.OPENAI_API_KEY) {
    console.error('OPENAI_API_KEY is required');
    process.exit(1);
  }

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  let messages: BaseMessage[] = [];
  console.log('Chat with the code agent (Ctrl+C to quit).');

  while (true) {
    const line = (await rl.question('\x1b[94mYou\x1b[0m: ')).trim();
    if (!line) continue;
    messages = [...messages, new HumanMessage(line)];
    const result = await agent.invoke({ messages });
    messages = result.messages;
    const reply = messages.at(-1) as AIMessage;
    const text = typeof reply.content === 'string' ? reply.content : JSON.stringify(reply.content);
    console.log(`\x1b[93mAgent\x1b[0m: ${text}`);
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  repl().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
