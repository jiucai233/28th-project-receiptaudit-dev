import json
from langchain_upstage import ChatUpstage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from .prompt_templates import AUDIT_SYSTEM_PROMPT

class AuditReasoning:
    def __init__(self):
        # 모델은 우선 solar-1-mini-chat으로 설정했습니다. 추후에 변경하면 될 것 같습니다.
        # JsonOutputParser를 통해 LLM의 출력문 중에서 JSON 형식의 텍스트만 골라내서 딕셔너리 객체로 변환합니다.
        self.llm = ChatUpstage(model="solar-1-mini-chat")
        self.parser = JsonOutputParser()

    def analyze(self, receipt_json, retrieved_rules):
        
        # "system"이랑 "human"으로 구분하였습니다. system은 사전에 작성한 프롬프트 양식을 입력하고, human은 유사 규정과 영수증 json을 입력하게 됩니다.
        prompt = ChatPromptTemplate.from_messages([
            ("system", AUDIT_SYSTEM_PROMPT),
            ("human", "규정: {rules}\n\n영수증: {receipt}")
        ])
        
        # langchain 구성입니다.
        chain = prompt | self.llm | self.parser
        
        # 입력받은 영수증 데이터와 유사 규정들을 llm에게 주고 규정 위반 여부를 판단하게 합니다.
        return chain.invoke({
            "rules": retrieved_rules,
            "receipt": json.dumps(receipt_json, ensure_ascii=False)
        })
    

# 테스트용 코드입니다.
# data/raw 경로에 organization_policy.pdf 만들어두고 아래 주석 해제 하여 터미널에 '''python -m core.rag_engine.ingest''' 실행 후 '''python -m core.audit_agent.reasoning''' 실행하시면 됩니다.

# if __name__ == "__main__":
#     from core.rag_engine.vector_db import VectorDBManager
#     from core.rag_engine.embedder import RegulationEmbedder
#     import json

#     db_manager = VectorDBManager()
#     embedder = RegulationEmbedder()
#     agent = AuditReasoning()

#     # 테스트용 가짜 영수증 (명세서 예시 데이터)
#     mock_receipt = {
#         "receipt_id": "uuid-1234",
#         "store_name": "GS25 연세점",
#         "items": [
#             {"id": 1, "name": "참이슬", "unit_price": 1800, "count": 2, "price": 3600},
#             {"id": 2, "name": "삼각김밥", "unit_price": 1200, "count": 1, "price": 1200}
#         ]
#     }

#     print("--- 관련 규정 검색 중... ---")
#     related_docs = db_manager.search_rules("주류 및 음식물 구매 제한 규정", embedder.get_embedding_model())
#     rules_text = "\n".join([doc.page_content for doc in related_docs])
    
#     print("--- AI 감사 분석 시작 ---")
#     result = agent.analyze(mock_receipt, rules_text)
    
#     print("\n[최종 감사 결과 리포트]")
#     print(json.dumps(result, indent=4, ensure_ascii=False))