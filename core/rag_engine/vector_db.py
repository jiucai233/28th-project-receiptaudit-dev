from langchain_chroma import Chroma
import os
import re

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

    def delete_document(self, doc_id, embedding_model):
        if not os.path.exists(self.persist_path) or not os.listdir(self.persist_path):
            return False
            
        db = Chroma(
            persist_directory=self.persist_path,
            embedding_function=embedding_model
        )
        db.delete(ids=[doc_id])
        return True

    def update_document(self, doc_id, document, embedding_model):
        if not os.path.exists(self.persist_path) or not os.listdir(self.persist_path):
            return False
            
        db = Chroma(
            persist_directory=self.persist_path,
            embedding_function=embedding_model
        )
        # Delete the old document and add the new one with the same ID
        db.delete(ids=[doc_id])
        db.add_documents([document], ids=[doc_id])
        return True

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
                당신은 감사 전문 리랭커(Re-ranker)입니다. 
                다음 [영수증 품목]과 [후보 규정]들의 연관성을 단계별로 생각하여 가장 적합한 규정 순서대로 나열하세요.

                [분석 단계]
                1. 영수증 품목의 잠재적 의미(오타, 동의어, 상위 카테고리 등)를 파악하세요.
                2. 각 규정 조항이 해당 품목을 금지하거나 제한하는지 논리적으로 따져보세요.
                3. 규정 조항에서 요구하는 영수증 사항이 모두 포함되어 있는지 확인하세요.(예시: 상호명, 품목명, 구매 시간, 가격 등 영수증에서 요구하는 사항들)
                4. 가장 직접적으로 연관된 규정부터 내림차순으로 정렬하세요.

                영수증 품목: {query}
                후보 규정:
                {context}

                최종 결과는 반드시 조항 번호만 쉼표로 구분하여 출력하세요 (예: 2, 1, 4).
                """
                response = agent_llm.invoke(rerank_prompt)
                numbers = re.findall(r'\d+', response.content)
                indices = [int(num) - 1 for num in numbers]

                valid_indices = []
                for i in indices:
                    if 0 <= i < len(initial_docs) and i is not valid_indices:
                        valid_indices.append(i)

                if valid_indices:
                    return [initial_docs[i] for i in valid_indices][:k]
                else:
                    return initial_docs[:k]
            
            except Exception as e:
                print(f"Reranking failed, returning base results: {e}")
                return initial_docs[:k]
        
        return initial_docs