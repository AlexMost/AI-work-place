import { tool } from '@langchain/core/tools';
import { z } from 'zod';

const WIKI_HEADERS = {
  'User-Agent': 'fact-checker/1.0 (educational project)',
  Accept: 'application/json',
};

// 1. Пошук статей
export const searchWikipedia = tool(
  async ({ query }) => {
    const url = `https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(query)}&format=json&utf8=1`;
    const res = await fetch(url, { headers: WIKI_HEADERS });
    const data = await res.json();
    const titles = data.query.search.slice(0, 3).map((r: any) => r.title);
    return titles.join(', ');
  },
  {
    name: 'search_wikipedia',
    description: 'Search Wikipedia for articles related to the query. Returns article titles.',
    schema: z.object({
      query: z.string().describe('Search query'),
    }),
  }
);

// 2. Отримати зміст сторінки
export const getPageSummary = tool(
  async ({ title }) => {
    const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`;
    const res = await fetch(url, { headers: WIKI_HEADERS });
    const data = await res.json();
    return data.extract ?? 'Page not found';
  },
  {
    name: 'get_page_summary',
    description:
      'Get a short summary of a Wikipedia article. Use this FIRST before get_full_content.',
    schema: z.object({
      title: z.string().describe('Exact Wikipedia article title'),
    }),
  }
);

// 2. Отримати повну сторінку
export const getPageFullContent = tool(
  async ({ title }) => {
    const url = `https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&titles=${encodeURIComponent(title)}&format=json`;
    const res = await fetch(url, { headers: WIKI_HEADERS });
    const data = await res.json();
    const pages = data.query.pages;
    const page = Object.values(pages)[0] as any;
    return page.extract ?? 'Page not found';
  },
  {
    name: 'get_full_content',
    description:
      "Get the FULL text of a Wikipedia article. Use only as fallback when get_page_summary didn't contain enough information to verify the claim.",
    schema: z.object({
      title: z.string().describe('Exact Wikipedia article title'),
    }),
  }
);
