from pydantic import BaseModel

class ConversationRequest(BaseModel):
    sessionId: str
    text: str
    userId: str
