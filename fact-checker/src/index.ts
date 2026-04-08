import 'dotenv/config';
import { checkText } from './checkText';

const main = async (text: string) => {
  const result = await checkText(text);
  console.dir(result, { depth: null });
};

main('Курган Агрегат написали пісню Деган? Київ є столицею України.').catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
