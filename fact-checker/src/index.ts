import 'dotenv/config';
import { checkText } from './checkText';
import { checkFact } from './factCheck';

const DEFAULT_DEMO_TEXT = 'Курган Агрегат написали пісню Деган? Київ є столицею України.';

export { checkText, checkFact };
export type { CheckTextResult, CheckedTextItem } from './checkText';
export type { FactCheckResult, FactCheckVerdict } from './factCheck';

export const runDemo = async (text: string = DEFAULT_DEMO_TEXT) => {
  const result = await checkText(text);
  console.dir(result, { depth: null });
};

if (require.main === module) {
  runDemo().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
