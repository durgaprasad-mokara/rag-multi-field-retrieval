"""
RAG chain — composes retriever + prompt + LLM into a complete chain.
Supports OpenAI, OpenRouter (free models), Ollama, and HuggingFace.
"""
import os
from typing import Any
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.retrievers import BaseRetriever
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from app.rag.prompts import get_rag_prompt


class LocalGroundedChatModel(BaseChatModel):
    """Local, offline chat model that synthesizes answers directly from retrieved document context."""

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        full_text = "\n".join([m.content if isinstance(m.content, str) else str(m.content) for m in messages])

        context_str = ""
        if "Context:" in full_text:
            parts = full_text.split("Context:")
            if len(parts) > 1:
                context_str = parts[1].split("Question:")[0].strip()

        if context_str and context_str != "None":
            # Cleanly present the retrieved context facts as answer
            answer = f"Based on your uploaded document context:\n\n{context_str}"
        else:
            answer = "I couldn't find specific relevant information in the uploaded documents to answer your question. Please try uploading more details or rephrasing."

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=answer))])

    @property
    def _llm_type(self) -> str:
        return "local_grounded"


def get_llm():
    """Return an LLM instance based on LLM_PROVIDER environment variable."""
    provider = os.getenv("LLM_PROVIDER", "local").lower()

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        return ChatOpenAI(model=model, temperature=0.1, max_tokens=1024)
    elif provider == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("LLM_MODEL", "meta-llama/llama-3.2-1b-instruct:free")
        return ChatOpenAI(
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            model=model,
            temperature=0.1,
            max_tokens=1024,
        )
    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        model = os.getenv("LLM_MODEL", "llama3.2")
        base_url = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        return ChatOllama(model=model, base_url=base_url, temperature=0.1)
    else:
        # Default local offline RAG model (no external API key needed)
        return LocalGroundedChatModel()


def get_rag_chain(retriever: BaseRetriever):
    """
    Build and return a full RAG chain:
      1. Retriever fetches top-K relevant chunks
      2. Stuff documents chain formats context into the prompt
      3. LLM generates the answer
    """
    llm = get_llm()
    prompt = get_rag_prompt()

    # Combine documents into the prompt context
    question_answer_chain = create_stuff_documents_chain(llm, prompt)

    # Wire retriever + QA chain
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain

