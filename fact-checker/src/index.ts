import 'dotenv/config';
import { checkFact } from './factCheck';
import { ChatOpenAI } from '@langchain/openai';

const main = async (fact: string) => {
  console.log('----- gpt-5.4');
  const llm = new ChatOpenAI({ model: 'gpt-5.4' });
  const resultSimpleModel = await llm.invoke(fact);
  console.log(resultSimpleModel.content);
  console.log('----- wiki fact checker ----');
  const result = await checkFact(fact);

  console.log(result);

};

main('Іран заблокував Ормузьку протоку');
