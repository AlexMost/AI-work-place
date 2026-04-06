import 'dotenv/config';
import { checkFact } from './factCheck';

const main = async () => {
  const result = await checkFact("Ukraine territory is bigger than France");
  console.log(result);
};

main();
