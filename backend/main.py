from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

class ChatRequest(BaseModel):
    query: str
    session_id: str

@app.post("/chat")
def chat(request: ChatRequest):
    return {
        "answer": f"You asked: {request.query}",
        "session_id": request.session_id
    }