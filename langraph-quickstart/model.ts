import 'dotenv/config';
import { ChatOpenAI } from '@langchain/openai'
import { tools } from './tools';

const model = new ChatOpenAI({ model: 'gpt-4o', temperature: 0 });

export const modelWithTools = model.bindTools(tools);

