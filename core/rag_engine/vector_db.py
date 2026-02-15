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
            # 텍스트 사이의 의미적 연관성을 찾는 것이 목적이므로 코사인 유사도를 사용하도록 강제했습니다.
            # TODO 사용하고자 하는 유사도 측정 방식에 따라 세 개중에 하나 주석 해제해서 사용하면 됩니다! 기본값은 l2거리입니다.
            collection_metadata={"hnsw:space": "cosine"}
            # collection_metadata={"hnsw:space": "l2"} # l2거리(Euclidean Distance)
            # collection_metadata={"hnsw:space": "ip"} # 내적(inner product)
        )
        return db

    # query를 통해 영수증 JSON을 입력받고, embedding_model(규정집 벡터화 시 사용한 모델과 동일해야함!)을 통해 벡터화하고, 영수증과 유사한 규정 탐색
    # TODO k: 끌어올 유사 조항 개수(여러 번 해보면서 조정해보면 될 것 같아요!)
    def search_rules(self, query, embedding_model, k=3, agent_llm=None):
        db = Chroma(persist_directory=self.persist_path, embedding_function=embedding_model)
        initial_docs = db.similarity_search(query, k=k if agent_llm is None else k*3) # 리랭킹 시 후보를 더 많이 뽑음

        # Re-ranking 로직
        if agent_llm and initial_docs:
            try:
                context = "\n".join([f"[{i+1}] {doc.page_content}" for i, doc in enumerate(initial_docs)])
                rerank_prompt = f"""
                다음 '영수증 품목'과 가장 관련이 깊은 '규정 조항'을 번호로만 골라주세요.
                오타가 있어도 문맥상 관련 있다면 높은 순위를 부여하세요.

                영수증 품목: {query}
                후보 규정:
                {context}

                가장 관련 있는 번호를 쉼표로 구분해 상위 3개만 답변하세요 (예: 2, 1, 4).
                """
                response = agent_llm.invoke(rerank_prompt)
                indices = [int(idx.strip()) - 1 for idx in response.content.split(',') if idx.strip().isdigit()]
                return [initial_docs[i] for i in indices if i < len(initial_docs)][:k]
            except Exception as e:
                print(f"Reranking failed, returning base results: {e}")
                return initial_docs[:k]
        
        return initial_docs