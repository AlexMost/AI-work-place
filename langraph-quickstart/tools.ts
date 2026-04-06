import { tool } from "@langchain/core/tools";
import { z } from "zod";
import {interrupt} from "@langchain/langgraph";

const addTool = tool(({ a, b }) => a + b, {
  name: "add",
  description: "Add two numbers",
  schema: z.object({
    a: z.number().describe("First number"),
    b: z.number().describe("Second number"),
  }),
});

const multiplyTool = tool(({ a, b }) => a * b, {
  name: "multiply",
  description: "Multiply two numbers",
  schema: z.object({
    a: z.number().describe("First number"),
    b: z.number().describe("Second number"),
  }),
});

const divideTool = tool(({ a, b }) => a / b, {
  name: "divide",
  description: "Divide two numbers",
  schema: z.object({
    a: z.number().describe("First number"),
    b: z.number().describe("Second number"),
  }),
});

const askClarificationTool = tool(
    ({ question }) => interrupt(question),
    {
        name: "ask_clarification",
        description: "Ask the user for clarification when the request is ambiguous or incomplete",
        schema: z.object({
            question: z.string().describe("The clarifying question to ask the user"),
        }),
    }
);

// Augment the LLM with tools
export const toolsByName = {
  [addTool.name]: addTool,
  [multiplyTool.name]: multiplyTool,
  [divideTool.name]: divideTool,
  [askClarificationTool.name]: askClarificationTool,
};

export const tools = Object.values(toolsByName);
