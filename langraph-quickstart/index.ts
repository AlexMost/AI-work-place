import {SystemMessage, AIMessage, ToolMessage, HumanMessage} from "@langchain/core/messages";
import {modelWithTools} from "./model";
import {GraphNode, StateGraph, START, interrupt, MemorySaver, END} from "@langchain/langgraph";
import {MessagesState} from "./state";
import {toolsByName} from "./tools";

const llmCall: GraphNode<typeof MessagesState> = async (state) => {
    const response = await modelWithTools.invoke([
        new SystemMessage(
            "You are a helpful assistant for arithmetic. " +
            "If the request is ambiguous or missing numbers, use ask_clarification tool. " +
            "Otherwise compute the result directly."
        ),
        ...state.messages,
    ]);
    return {
        messages: [response],
        llmCalls: 1,
    };
};

const toolNode: GraphNode<typeof MessagesState> = async (state) => {
    const lastMessage = state.messages.at(-1);

    if (lastMessage == null || !AIMessage.isInstance(lastMessage)) {
        return {messages: []};
    }

    const result: ToolMessage[] = [];
    for (const toolCall of lastMessage.tool_calls ?? []) {
        const tool = toolsByName[toolCall.name];
        const observation = await tool.invoke(toolCall);
        result.push(observation);
    }

    return {messages: result};
};


const shouldContinue = (state: (typeof MessagesState)['State']): "toolNode" | typeof END => {
    const lastMessage = state.messages.at(-1);

    // Check if it's an AIMessage before accessing tool_calls
    if (!lastMessage || !AIMessage.isInstance(lastMessage)) {
        return END;
    }

    // If the LLM makes a tool call, then perform an action
    if (lastMessage.tool_calls?.length) {
        return "toolNode";
    }

    // Otherwise, we stop (reply to the user)
    return END;
};

const workflow = new StateGraph(MessagesState)
    .addNode("llmCall", llmCall)
    .addNode("toolNode", toolNode)
    .addEdge(START, "llmCall")
    .addConditionalEdges("llmCall", shouldContinue, ["toolNode", END])
    .addEdge("toolNode", "llmCall")


const checkpointer = new MemorySaver();
export const agent = workflow.compile({checkpointer});

// Invoke
// const result = await agent.invoke({
//   messages: [new HumanMessage("Add 3 and 4.")],
// });
//
// for (const message of result.messages) {
//   console.log(`[${message.type}]: ${message.text}`);
// }
