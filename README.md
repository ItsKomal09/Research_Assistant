
# ResearchMind — AI Research Assistant

An intelligent research assistant that combines a production-grade RAG pipeline with an agentic AI layer. Instead of just answering questions, ResearchMind reasons over your documents, fetches live research papers, identifies knowledge gaps, and shows you every step of its thinking.


# What it does

- Upload PDFs, paste URLs, or search arXiv/Wikipedia — all become queryable knowledge
- A LangGraph ReAct agent decides at runtime whether to search your knowledge base, fetch a live paper, or flag missing context
- Every answer comes with cited sources and a visible reasoning trace
- Conversation memory lets you ask follow-up questions naturally
- RAGAS evaluation gives quantified performance scores (faithfulness, relevancy)

# Tech Stack

1. LLM  :  Ollama (Llama 3.2)
2. Embeddings  :  BAAI/bge-base-en-v1.5
3. Vector Store : ChromaDB
4. RAG Framework : LangChain (LCEL)
5. Agentic AI : LangGraph (ReAct agent)
6. Backend : FastAPI + Uvicorn
7. Frontend :  React + Vite
8. Evaluation : RAGAS
