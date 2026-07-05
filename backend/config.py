from dotenv import load_dotenv
import os

load_dotenv()

#  LLM (Ollama) 
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

#  Embeddings 
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")

#  ChromaDB 
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "researchmind")

#  Retrieval 
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "6"))         # final docs returned
RETRIEVER_FETCH_K = int(os.getenv("RETRIEVER_FETCH_K", "20"))  # MMR candidate pool
BM25_K = int(os.getenv("BM25_K", "4"))                   # BM25 top results
DENSE_WEIGHT = float(os.getenv("DENSE_WEIGHT", "0.6"))   # hybrid blend
SPARSE_WEIGHT = float(os.getenv("SPARSE_WEIGHT", "0.4"))

#  Chunking 
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

#  arXiv 
ARXIV_MAX_RESULTS = int(os.getenv("ARXIV_MAX_RESULTS", "5"))

#  App 
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")