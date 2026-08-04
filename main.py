from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from chat_session import ChatSession

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = {}


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    destination: str | None = None
    possible_emergency: bool = False


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = ChatSession()

    session = sessions[session_id]
    result = session.send(request.message)

    return ChatResponse(
        session_id=session_id,
        reply=result["reply"],
        destination=result["destination"],
        possible_emergency=result["possible_emergency"],
    )


@app.get("/")
def root():
    return {"status": "NHS Signposting Assistant API is running"}