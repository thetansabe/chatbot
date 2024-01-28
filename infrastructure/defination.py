
from langchain.chains import LLMChain, ConversationChain
from langchain.llms.gpt4all import GPT4All
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import MongoDBChatMessageHistory
from langchain.prompts import PromptTemplate
from enum import Enum

class ModelType(Enum):
    LOCAL = 1
    OPENAI = 2
    PAML = 3
    GEMINI = 4

safety_settings = [
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

class LangChainDefination:
    def __init__(self, type:ModelType) -> None:
        self.type = type

    def llm(self, model_path:str,temperature=1) -> GPT4All:
        if self.type == ModelType.LOCAL:
            return GPT4All(model=model_path, verbose=True,temp=temperature)
        elif self.type == ModelType.GEMINI:
            return ChatGoogleGenerativeAI(model="gemini-pro", temperature=temperature, safety_settings=safety_settings)

    def prompt(self, template):
        return PromptTemplate.from_template(template)

    def conversation_prompt(self, template):
        return PromptTemplate(
            template= template,
            input_variables=["chat_history", "user_input"],
        )

    def llm_chain(self, prompt, llm) -> LLMChain:
        return LLMChain(prompt=prompt, llm=llm,verbose=False)
    
    def conversation_chain(self, prompt, llm, memory: MongoDBChatMessageHistory):
        return LLMChain(
            prompt=prompt, 
            llm=llm,
            memory=memory,
            verbose=False
        )
