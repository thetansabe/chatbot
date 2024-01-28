from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.utilities.searchapi import SearchApiAPIWrapper

app = FastAPI(
  title="LangChain Server",
  version="1.0",
  description="A simple api server using Langchain's Runnable interfaces",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)