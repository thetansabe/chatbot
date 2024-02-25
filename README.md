### INTRODUCTION
This project working with LLM models using LangChain
### NOTICE
You should NOT commit chroma_db_stored, this is just a vector database
### RUN PROJECT WITH DOCKER
Please make sure to delete old container and image before rebuild:
- To start: `docker-compose up`
- To stop: `docker-compose down`
### RUN PROJECT LOCALLY
1. Use virtual env with python >= 3.8 (recommend 3.10.13)
2. Run:
`pip install -r req.txt`
3. Start in local:
`python ./index.py`