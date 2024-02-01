import time, os
from fastapi import FastAPI,HTTPException
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


# Connect to MongoDB
client = AsyncIOMotorClient(MEMORY_CONNECTION_STRING)
database = client[DATABASE_NAME]
collection = database[COLLECTION_NAME]
session_collection = database[SESSSION_COLLECTION_NAME]

# Custom JSON Encoder
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
@app.put("/likeChatSession")
async def likeChatSession(req: ConvesationLikeRequest):
    session_id  = req.sessionId
    is_liked = req.isLiked
    existing_message = await session_collection.find_one({"session_id": session_id})
    if existing_message:
        await session_collection.update_one(
            {"session_id": session_id},
            {"$set": {"isLiked": is_liked}}
        )
        return JSONResponse(content={"message": "isLiked updated"}, status_code=200)
    else:
        return JSONResponse(content={"message": "Session is not found"}, status_code=404)


@app.get("/get_messages/{session_id}")
async def get_messages(session_id: str):
    messages = await collection.find({"SessionId": session_id}).to_list(length=None)
    converted_messages = [convert_message_format(message) for message in messages]

    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for the given session_id")
    serialized_messages = json.dumps(converted_messages, cls=CustomEncoder)
    return JSONResponse(content=json.loads(serialized_messages), status_code=200)

def convert_message_format(message):
    history_data = json.loads(message["History"])
    converted_message = {
        "_id": message["_id"],
        "SessionId": message["SessionId"],
        "type": history_data["type"],
        "content": history_data["data"]["content"]
    }
    return converted_message

@app.get("/get_all_messages")
async def get_all_messages():
    messages = await collection.find({}).to_list(length=None)
    converted_messages = [convert_message_format(message) for message in messages]
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")
    serialized_messages = json.dumps(converted_messages, cls=CustomEncoder)
    return JSONResponse(content=json.loads(serialized_messages), status_code=200)

@app.get("/get_recent_sessions/{type}")
async def get_recent_sessions(type:str):
    if type == 'today':
        dayLimit = 1
    if type == 'thisweek':
        dayLimit = 7
    if type == 'thismonth':
        dayLimit = 30
    if type == 'previous':
        dayLimit = -1
    daysAgo = datetime.utcnow() - timedelta(days=dayLimit)
    recent_sessions = await session_collection.find({"date": {"$gte": daysAgo}}).to_list(length=None)
    if not recent_sessions:
        raise HTTPException(status_code=404, detail="No recent sessions found")
    serialized_sessions = json.dumps(recent_sessions, cls=CustomEncoder)
    return JSONResponse(content=json.loads(serialized_sessions), status_code=200)

@app.get("/get_starred_sessions/{userId}")
async def get_recent_sessions(userId:str):
    recent_sessions = await session_collection.find({"isLiked":True}).to_list(length=None)
    if not recent_sessions:
        raise HTTPException(status_code=404, detail="No recent sessions found")
    serialized_sessions = json.dumps(recent_sessions, cls=CustomEncoder)
    return JSONResponse(content=json.loads(serialized_sessions), status_code=200)
@app.get("/get_sessions")
async def get_recent_sessions():
    recent_sessions = await session_collection.find({}).to_list(length=None)
    if not recent_sessions:
        raise HTTPException(status_code=404, detail="No sessions found")
    serialized_sessions = json.dumps(recent_sessions, cls=CustomEncoder)
    return JSONResponse(content=json.loads(serialized_sessions), status_code=200)

@app.delete("/delete_session/{session_id}")
async def delete_session(session_id: str):
    result = await session_collection.delete_one({"session_id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"No session found for session_id: {session_id}")
    return {"message": f"Session with session_id: {session_id} deleted successfully"}
    
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
            existing_message = await session_collection.find_one({"session_id": req.sessionId})
            
            if existing_message is None:
                current_date = datetime.utcnow()
                new_message = {"session_id": req.sessionId, "content":result["text"],"isLiked": False, "date": current_date}
                await session_collection.insert_one(new_message)
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
