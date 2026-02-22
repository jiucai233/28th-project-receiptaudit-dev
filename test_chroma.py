from langchain_chroma import Chroma
from langchain_core.documents import Document
from core.rag_engine.embedder import RegulationEmbedder

embedder = RegulationEmbedder()
db = Chroma(persist_directory="./data/vector_store", embedding_function=embedder.get_embedding_model())
print(dir(db))
