### INTRODUCTION
This project working with LLM models using LangChain
### NOTICE
- You should NOT commit chroma_db_stored, this is just a vector database
- Get your own:
    - GG_API_KEY at https://aistudio.google.com/app/apikey
    - SEARCH_API_KEY at https://www.searchapi.io/
    - AWS_ACCESS_KEY, AWS_SECRET_KEY, S3_BUCKET_NAME in this tutorial https://www.youtube.com/watch?v=39X5WdZbEwQ
- Provide above ENV vars when you build docker
    - Option 1: Right before build, add those vars in docker-compose.yml
    - Option 2: 
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