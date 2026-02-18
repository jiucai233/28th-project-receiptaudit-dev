from langchain_chroma import Chroma
import os

class VectorDBManager:
    def __init__(self, persist_path="./data/vector_store"):
        self.persist_path = persist_path

    # documents로 입력받은 chunk들을 embedding_model(solar-embedding-1-large(임시))을 사용하여 벡터화
    def create_db(self, documents, embedding_model):
        db = Chroma.from_documents(
            documents=documents,
            embedding=embedding_model,
            persist_directory=self.persist_path,
            collection_metadata={"hnsw:space": "cosine"}
        )
        return db

    def add_documents(self, documents, embedding_model):
        if not os.path.exists(self.persist_path) or not os.listdir(self.persist_path):
            return self.create_db(documents, embedding_model)
        
        db = Chroma(
            persist_directory=self.persist_path,
            embedding_function=embedding_model
        )
        db.add_documents(documents)
        return db

    # query를 통해 영수증 JSON을 입력받고, embedding_model(규정집 벡터화 시 사용한 모델과 동일해야함!)을 통해 벡터화하고, 영수증과 유사한 규정 탐색
    def search_rules(self, query, embedding_model, k=3):
        if not os.path.exists(self.persist_path) or not os.listdir(self.persist_path):
            return []
            
        db = Chroma(
            persist_directory=self.persist_path,
            embedding_function=embedding_model
        )
        # Chroma 내장함수. 유사도 검색 함수입니다.
        return db.similarity_search(query, k=k)
