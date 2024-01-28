import time, os
from fastapi import FastAPI
from data_type.conversation_request import ConvesationRequest, ConvesationLikeRequest,ConvesationRequestInput, dayLimitBySessionRequest
from langchain_community.utilities.searchapi import SearchApiAPIWrapper
from data_type.conversation_request import ConvesationRequest
from embedding.embedding import LangChainEmbedding
from infrastructure.defination import LangChainDefination, ModelType
from langchain.memory import MongoDBChatMessageHistory, ConversationBufferMemory
from config.constants import *
from tools.tool import *
from app import app

from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import json
from datetime import datetime, timedelta,date

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "AIzaSyBTiUCRKEn7jPQqTn2Ok1jWTCXhjMEiHT0"
if "SEARCHAPI_API_KEY" not in os.environ:
    os.environ["SEARCHAPI_API_KEY"] = "T61bzfFQuTuC5wRYxRsJj83A"

# default defination
apiVersion = "1"
defination = LangChainDefination(type= ModelType.GEMINI)
defination_local = LangChainDefination(type= ModelType.GEMINI)
embedding = LangChainEmbedding()

llm = defination.llm(MODEL_PATH)
llm_chain_embedding = defination.llm_chain(prompt=defination.prompt(EMBEDDING_TEMPLATE),llm=llm)
llm_local = defination.llm(MODEL_PATH,0)
llm_chain_tool = defination.llm_chain(prompt=defination.prompt(TOOL_TEMPLATE),llm=llm_local)
llm_chain_detect = defination.llm_chain(prompt=defination.prompt(DETECT_ENTITY_TEMPLATE),llm=llm_local)
llm_chain_rewrite = defination.llm_chain(prompt=defination.prompt(REWRITE_TEMPLATE),llm=llm)

embedding.load_document(EMBEDDING_DOCUMENT_PATH,EMBEDDING_STORED_PATH)


# MongoDB configuration
MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "chat_history"
COLLECTION_NAME = "message_store"
NEW_COLLECTION_NAME = "new_message_store"

# Connect to MongoDB
client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]
collection = database[COLLECTION_NAME]
new_collection = database[NEW_COLLECTION_NAME]

# Custom JSON Encoder
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
@app.post("/likeChatSession")
async def likeChatSession(req: ConvesationLikeRequest):
    session_id  = req.sessionId
    is_liked = req.isLiked

    # Kiểm tra xem đã tồn tại một bản ghi với session_id và is_liked=True hay không
    existing_message = await new_collection.find_one({"session_id": session_id, "isLiked": True})

    if existing_message:
        # Nếu đã tồn tại, chỉ cần update, không cần thêm
        await new_collection.update_one(
            {"session_id": session_id, "isLiked": True},
            {"$set": {"isLiked": is_liked}}
        )
        return JSONResponse(content={"message": "isLiked updated"}, status_code=200)
    else:
        # Nếu không có, thêm một bản ghi mới
        current_date = datetime.utcnow()
        new_message = {"session_id": session_id, "isLiked": is_liked, "date": current_date}
        
        # Insert document into the new collection
        result = await new_collection.insert_one(new_message)

        if result.inserted_id:
            return JSONResponse(content={"message": "Message added successfully"}, status_code=200)
        else:
            raise HTTPException(status_code=500, detail="Failed to add message")


@app.get("/get_messages/{session_id}")
async def get_messages(session_id: str):
    # Query MongoDB for messages with the specified session_id
    messages = await collection.find({"SessionId": session_id}).to_list(length=None)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for the given session_id")
    # Serialize messages using the custom JSON encoder
    serialized_messages = json.dumps(messages, cls=CustomEncoder)

    return JSONResponse(content=json.loads(serialized_messages), status_code=200)
@app.get("/get_recent_sessions/{days}")
async def get_recent_sessions(dayLimit: int):
    # Tính ngày 7 ngày trước
    seven_days_ago = datetime.utcnow() - timedelta(days=dayLimit)
    # Truy vấn các session được tạo trong khoảng thời gian 7 ngày trước
    recent_sessions = await new_collection.find({"date": {"$gte": seven_days_ago}}).to_list(length=None)
    if not recent_sessions:
        raise HTTPException(status_code=404, detail="No recent sessions found")
    # Serialize sessions using the custom JSON encoder
    serialized_sessions = json.dumps(recent_sessions, cls=CustomEncoder)
    return JSONResponse(content=json.loads(serialized_sessions), status_code=200)
@app.post("/completion")
async def completion(req: ConvesationRequest):
    text = req.text
    start = time.perf_counter()
    mongo_history = MongoDBChatMessageHistory(connection_string= MEMORY_CONNECTION_STRING,session_id= str(req.sessionId))
    memory = ConversationBufferMemory(
        input_key="user_input",
        chat_memory=mongo_history,
        memory_key='chat_history'
    )
    
    result = llm_chain_tool({"context":tool_context, "user_query": text})
    print("Tool:" , result["text"])
    if result["text"] != "None":
        cur_tool = next((tool for tool in tools if tool["name"] == result["text"]), None)
        result_of_tool = await cur_tool["func"](query = text,chain= llm_chain_detect,rewrite_chain=llm_chain_rewrite)
        end = time.perf_counter()
        print(f"Time elapsed: {end - start:.2f} seconds")
        return {
            "response" : result_of_tool,
            "type": "This result from tool",
            "sessionId": req.sessionId
        }
    else:
        document = embedding.find_document(text)
        result = llm_chain_embedding(document)
        print("Embedding:" , result["text"])
        if result["text"] != "None":
            mongo_history.add_user_message(text)
            mongo_history.add_ai_message(result["text"])
            return {
                "response" : {
                    "text": result["text"]
                },
                "type": "This result from embedding",
                "sessionId": req.sessionId
            }
        else:
            conversation = defination.conversation_chain(prompt=defination.conversation_prompt(DEFAULT_TEMPLATE), llm=llm, memory= memory)
            result = conversation({"user_input": text})
            end = time.perf_counter()
            print(f"Time elapsed: {end - start:.2f} seconds")
            existing_message = await new_collection.find_one({"session_id": req.sessionId})
            
            if existing_message is None:
                current_date = datetime.utcnow()
                new_message = {"session_id": str(req.sessionId), "isLiked": False, "date": current_date}
                await new_collection.insert_one(new_message)
                print(f"New message inserted: {new_message}")

            return {
                "response" : {
                    "text": result["text"]
                },
                "type": "This result from conversation",
                "sessionId": req.sessionId
            }
if __name__ == "__main__":
    
    import uvicorn
    uvicorn.run(app, host=HOST, port=8000)
