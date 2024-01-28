import os
MODEL_PATH = "./models/gpt4all-falcon-newbpe-q4_0.gguf"
EMBEDDING_MODEL_PATH = "./models/all-MiniLM-L6-v2-f16.gguf"
EMBEDDING_DOCUMENT_PATH = "./embedding/QnA.txt"
EMBEDDING_STORED_PATH = "./chroma_db_stored"
EMBEDDING_TEMPLATE = """You are a chatbot for e-commerce. Answer the question based on the context. Make the answer more natural to fit the question.
If the user's question is not true for the current field, answer will be None

{context}

Question: {user_question}
Answer:"""
TOOL_TEMPLATE = """Find a tool name if the user query matched with tool description in the context.
If the user query not match with any tool description in the context, tool name will be None

{context}

Query: {user_query}
Tool Name:"""
DETECT_ENTITY_TEMPLATE = """Detect entity from user input to entities in the context with template:
[entity name:entity value|entity name:entity value|...]
If can not detect any entities from user input. the result will be None

{context}

Query: {user_input}
Tool Name:"""
REWRITE_TEMPLATE = """Rewrite the context.
With start resutl is "Here is a result of"

{context}

Result:"""
DEFAULT_TEMPLATE = """You are a chatbot having a conversation with a human.

Chat history:
{chat_history}

Human: {user_input}
Chatbot:"""

MEMORY_CONNECTION_STRING= os.getenv('DOCKER_MONGO_CONN', 'mongodb://localhost:27017') 
DATABASE_NAME = "chat_history"
COLLECTION_NAME = "message_store"
NEW_COLLECTION_NAME = "new_message_store"
HOST = os.getenv('DOCKER_HOST','localhost')
print("Memory connection string: ", MEMORY_CONNECTION_STRING)
print("Host: ", HOST)