import 'dotenv/config';
import { checkText } from './checkText';
import { checkFact } from './factCheck';

const DEFAULT_DEMO_TEXT = `
Карлос Рей Норріс-молодший з’явився на світ 10 березня 1941 року в невеликому містечку Раян в Оклахомі.
Його батько працював автомеханіком, мав військовий досвід часів Другої світової війни та водночас боровся з залежністю від азартних ігор.
Коли Чакові виповнилося 16, його родина перебралася до Торранса в Каліфорнії.
Уже в дорослому віці він у вільний час підробляв вантажником, хоча насправді хотів пов’язати життя з роботою в поліції.
Щоб наблизитися до цієї мети, відразу після завершення школи Норріс вступив до військово-повітряних сил.
На той момент він уже був одружений зі своєю шкільною знайомою Діаною Хол.
`;

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
