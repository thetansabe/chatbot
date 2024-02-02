import time, os
from fastapi import FastAPI,HTTPException
from data_type.conversation_request import ConversationRequest
from langchain_community.utilities.searchapi import SearchApiAPIWrapper
from data_type.conversation_request import ConversationRequest
from embedding.embedding import LangChainEmbedding
from infrastructure.defination import LangChainDefination, ModelType
from langchain.memory import MongoDBChatMessageHistory, ConversationBufferMemory
from config.constants import *
from tools.tool import *
from app import app
from helper.helper import convert_message_format

from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import json
from datetime import datetime, timedelta,date

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "AIzaSyBTiUCRKEn7jPQqTn2Ok1jWTCXhjMEiHT0"
if "SEARCHAPI_API_KEY" not in os.environ:
    os.environ["SEARCHAPI_API_KEY"] = "T61bzfFQuTuC5wRYxRsJj83A"

#default defination
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


#Connect to MongoDB
client = AsyncIOMotorClient(MEMORY_CONNECTION_STRING)
database = client[DATABASE_NAME]
collection = database[COLLECTION_NAME]
session_collection = database[SESSSION_COLLECTION_NAME]
userId  = 'U0123'

#Custom JSON Encoder
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


#api 1: TESTED DONE method get, endpoint: /all/{sessionId}
@app.get("/messages/{sessionId}")
async def messages(sessionId: str):
    messages = await collection.find({"SessionId": sessionId}).to_list(length=None)
    converted_messages = [convert_message_format(message) for message in messages]

    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for the given sessionId")
    serialized_messages = json.dumps(converted_messages, cls=CustomEncoder)
    return JSONResponse(content=json.loads(serialized_messages), status_code=200)
#api 2 method get, endpoint: /history/{userId}: get all the sessions from the session collection
@app.get("/messages/history/{userId}")
async def all_sessions(userId:str):
    today = datetime.utcnow() - timedelta(days=1)
    thisWeek = datetime.utcnow() - timedelta(days=7)
    thisMonth = datetime.utcnow() - timedelta(days=30)
    thisYear = datetime.utcnow() - timedelta(days=365)
    today_sessions = await session_collection.find({"userId":userId, "date": {"$gte": today} }).to_list(length=None)
    this_week_sessions = await session_collection.find({"userId":userId, "date": {"$gte": thisWeek} }).to_list(length=None)
    this_month_sessions = await session_collection.find({"userId": userId, "date": {"$gte": thisMonth}}).to_list(length=None)
    this_year_sessions = await session_collection.find({"userId": userId, "date": {"$gte": thisYear}}).to_list(length=None)
    this_week_sessions = [session for session in this_week_sessions if session not in today_sessions]
    this_month_sessions = [session for session in this_month_sessions if session not in today_sessions and session not in this_week_sessions]
    this_year_sessions = [session for session in this_month_sessions if session not in today_sessions and session not in this_week_sessions and session not in this_month_sessions]
    
    merged_sessions = {
        'today': json.dumps(today_sessions, cls=CustomEncoder),
        'thisWeek': json.dumps(this_week_sessions, cls=CustomEncoder),
        'thisMonth': json.dumps(this_month_sessions, cls=CustomEncoder),
        'thisYear': json.dumps(this_year_sessions, cls=CustomEncoder),
    }
    if not merged_sessions:
        raise HTTPException(status_code=404, detail="No sessions found")
    # serialized_sessions = json.dumps(merged_sessions, cls=CustomEncoder)
    return JSONResponse(content=merged_sessions, status_code=200)

#api 3 - TESTED DONE, method get, endpoint: /starred/{userId}: get all the starred sessions from the session collection
@app.get("/session/likes/{userId}")
async def starred_sessions(userId:str):
    recent_sessions = await session_collection.find({"userId":userId, "isLiked":True}).to_list(length=None)
    if not recent_sessions:
        raise HTTPException(status_code=404, detail="No recent sessions found")
    serialized_sessions = json.dumps(recent_sessions, cls=CustomEncoder)
    return JSONResponse(content=json.loads(serialized_sessions), status_code=200)
    
#api 4 - TESTED DONE method put, endpoint: /star/{sessionId}
@app.put("/session/like/{sessionId}")
async def likeChatSession(sessionId: str):
    existing_message = await session_collection.find_one({"sessionId": sessionId})
    if existing_message:
        await session_collection.update_one(
            {"sessionId": sessionId},
            {"$set": {"isLiked": not existing_message["isLiked"]}}
        )
        return JSONResponse(content={"message": "isLiked updated"}, status_code=200)
    else:
        return JSONResponse(content={"message": "Session is not found"}, status_code=404)

#api 6 - TESTED DONE  method delete, endpoint: /conversation/{sessionId}, để xóa data ở bảng conversation
@app.delete("/session/{sessionId}")
async def delete_session(sessionId: str):
    result = await session_collection.delete_one({"sessionId": sessionId})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"No session found for sessionId: {sessionId}")
    return {"message": f"Session with sessionId: {sessionId} deleted successfully"}

#api 7 - TESTED DONE method put, endpoint: /session/rename
@app.put("/session/rename")
async def rename_session(req: ConversationRequest):
    existing_message = await session_collection.find_one({"sessionId": req.sessionId})
    if existing_message:
        await session_collection.update_one(
            {"sessionId": req.sessionId},
            {"$set": {"content": req.text}}
        )
        return JSONResponse(content={"message": "session name updated"}, status_code=200)
    else:
        return JSONResponse(content={"message": "Session is not found"}, status_code=404)
#api 8 - TESTED DONE method post completion (ask the gemini chatbot)
@app.post("/completion")
async def completion(req: ConversationRequest):
    text = req.text
    start = time.perf_counter()
    mongo_history = MongoDBChatMessageHistory(connection_string= MEMORY_CONNECTION_STRING,session_id= req.sessionId)
    memory = ConversationBufferMemory(
        input_key="user_input",
        chat_memory=mongo_history,
        memory_key='chat_history'
    )
    
    result = llm_chain_tool({"context":tool_context, "user_query": text})
    if result["text"] != "None":
        cur_tool = next((tool for tool in tools if tool["name"] == result["text"]), None)
        result_of_tool = await cur_tool["func"](query = text,chain= llm_chain_detect,rewrite_chain=llm_chain_rewrite)
        end = time.perf_counter()
        return {
            "response" : result_of_tool,
            "type": "This result from tool",
            "sessionId": req.sessionId
        }
    else:
        document = embedding.find_document(text)
        result = llm_chain_embedding(document)
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
            existing_message = await session_collection.find_one({"sessionId": req.sessionId})
            if existing_message is None:
                current_date = datetime.utcnow()
                new_message = {"sessionId": req.sessionId, "content":req.text,"isLiked": False, "date": current_date, "userId": req.userId}
                await session_collection.insert_one(new_message)
            return {
                "response" : {
                    "text": result["text"]
                },
                "type": "This result from conversation",
                "sessionId": req.sessionId
            }
#api 9 get the recent sessions by type
@app.get("/recent_sessions/{type}")
async def recent_sessions(dayLimit: int):
    daysAgo = datetime.utcnow() - timedelta(days=dayLimit)
    recent_sessions = await session_collection.find({"date": {"$gte": daysAgo}}).to_list(length=None)
    if not recent_sessions:
        raise HTTPException(status_code=404, detail="No recent sessions found")
    serialized_sessions = json.dumps(recent_sessions, cls=CustomEncoder)
    return JSONResponse(content=json.loads(serialized_sessions), status_code=200)
if __name__ == "__main__":
    
    import uvicorn
    uvicorn.run(app, host=HOST, port=8000)
