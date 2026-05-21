import 'dotenv/config';
import { createGraph } from './graph';

export const debugGraph = createGraph(process.env.OPENAI_API_KEY as string);
