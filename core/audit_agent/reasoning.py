import json
import os
from dotenv import load_dotenv
from langchain_upstage import ChatUpstage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser # [NEW] 문자열 파서 추가
from .prompt_templates import AUDIT_SYSTEM_PROMPT
from .naver_verifier import NaverStoreVerifier
from core.rag_engine.vector_db import VectorDBManager
from core.rag_engine.embedder import RegulationEmbedder

load_dotenv()

class AuditReasoning:
    def __init__(self):
        self.llm = ChatUpstage(model="solar-1-mini-chat")
        self.parser = JsonOutputParser()
        self.db_manager = VectorDBManager()
        self.embedder = RegulationEmbedder()
        self.verifier = NaverStoreVerifier(
            client_id=os.getenv("NAVER_CLIENT_ID", ""),
            client_secret=os.getenv("NAVER_CLIENT_SECRET", "")
        )

    def correct_receipt(self, receipt_data: dict) -> dict:
        try:
            parser = JsonOutputParser()
            prompt = ChatPromptTemplate.from_messages([
                ("system", """
                당신은 영수증 OCR 오타 교정 전문가입니다.
                다음 JSON 형태의 영수증 데이터에서 '상호명(store_name)'과 '품목명(items의 name)'의 OCR 오타임이 명백한 경우(글자 사이에 특수문자, 글자 오인식 등)에만 문맥에 맞게 교정하세요.
                오타를 확신할 수 없는 개인 가게 이름이나 품목명은 수정하지 마세요. 숫자(가격, 수량, 날짜 등)는 절대 건드리지 마세요.
                상호명이나 품목명에 아무 내용도 존재하지 않는 경우에는 절대 건드리지 마세요.
                """),
                ("human", "{receipt_json}")
            ])
            
            chain = prompt | self.llm | parser
            corrected_data = chain.invoke({"receipt_json": json.dumps(receipt_data, ensure_ascii=False)})
            
            # receipt_id 유실 방지
            corrected_data["receipt_id"] = receipt_data["receipt_id"]
            return corrected_data
        except Exception as e:
            print(f"교정 오류 (원본 반환): {e}")
            return receipt_data

    def analyze(self, receipt_json, retrieved_rules=None):
        store_name = receipt_json.get('store_name', '') # 원래는 store_name -> raw_store_name
        store_address = receipt_json.get('store_address', '')
        items = receipt_json.get('items', [])

        # print(f"1차 LLM: 상호명 오타 점검 중... 원본[{raw_store_name}]")
        # store_name = self.correct_receipt(raw_store_name)
        # if raw_store_name != store_name:
        #     print(f"교정 완료: [{raw_store_name}] ➡️ [{store_name}]")

        print(f"네이버 가맹점 검증 중: [{store_name}]")
        store_info = self.verifier.get_store_category(store_name, store_address)

        if retrieved_rules is None:
            all_relevant_docs = []
            unique_contents = set()

            for item in items:
                item_name = item.get('name', '')
                combined_query = f"가게: {store_name}, 품목: {item_name}"

                docs = self.db_manager.search_rules(
                    query=combined_query,
                    embedding_model=self.embedder.get_embedding_model(),
                    agent_llm=self.llm
                )

                for doc in docs:
                    if doc.page_content not in unique_contents:
                        all_relevant_docs.append(doc.page_content)
                        unique_contents.add(doc.page_content)

            retrieved_rules = "\n".join(all_relevant_docs)

        prompt = ChatPromptTemplate.from_messages([
            ("system", AUDIT_SYSTEM_PROMPT),
            ("human", "상호명: {store_name}\n가맹점 업종(네이버): {store_info}\n규정: {rules}\n\n영수증: {receipt}")
        ])
        
        chain = prompt | self.llm | self.parser
        
        return chain.invoke({
            "store_name": store_name,
            "store_info": json.dumps(store_info, ensure_ascii=False),
            "rules": retrieved_rules,
            "receipt": json.dumps(receipt_json, ensure_ascii=False)
        })