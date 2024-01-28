
from langchain.document_loaders import TextLoader
from langchain.embeddings.gpt4all import GPT4AllEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores.chroma import Chroma

class LangChainEmbedding:
    def __init__(self) -> None:
        pass

    def load_document(self, document_path, stored_path):
        raw_documents = TextLoader(document_path).load()
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        documents = text_splitter.split_documents(raw_documents)
        self.stored = Chroma.from_documents(documents, GPT4AllEmbeddings(), persist_directory=stored_path)

    def find_document(self,input:str):
        embedding_vector = GPT4AllEmbeddings().embed_query(input)
        documents = self.stored.similarity_search_by_vector(embedding_vector, k=1)
        context = documents[0].page_content.replace("Question: ","").replace("Answer: ","")
        return {"context": context,"user_question":input}
