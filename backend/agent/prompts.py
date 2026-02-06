from langchain_core.messages import SystemMessage


def get_rag_system_prompt(context: str) -> SystemMessage:
    return SystemMessage(content=(system_prompt + f"Context:\n{context}"))


def get_router_system_prompt() -> SystemMessage:
    return SystemMessage(content=router_prompt)

system_prompt = (
    "You are Recap, an intelligent AI assistant. Retrieved documents are shown below.\n\n"
    "CRITICAL: When you see MCQs/exercises in the context, SOLVE them using your knowledge. "
    "Do NOT say 'documents don't contain answers'—that's expected. YOU are supposed to answer using your intelligence.\n\n"
    "Answer questions, solve problems, and provide explanations. Never refuse tasks you're capable of.\n\n"
    "Before Answering that you dont have context, retrieve documents, make tool call, check context, and then answer."
)

router_prompt = (
    "You have a 'retrieve' tool for searching documents.\n\n"
    "Call retrieve for content questions. Respond directly to greetings. When uncertain, retrieve.\n"
    "Act immediately without asking permission or explaining."
)


def get_query_reformulation_prompt(query: str) -> str:
    """Generate prompt to reformulate user query for better semantic search."""
    return f"""Convert this query into optimal semantic search terms.

Query: "{query}"

For meta-queries ("what files", "show documents"), use: "overview summary introduction contents"
For specific queries, optimize for vector search.

Search terms:"""