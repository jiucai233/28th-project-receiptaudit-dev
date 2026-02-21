import json
import os
from dotenv import load_dotenv
from langchain_upstage import ChatUpstage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
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

    def analyze(self, receipt_json, retrieved_rules=None):
        store_name = receipt_json.get('store_name', '')
        store_address = receipt_json.get('store_address', '')
        items = receipt_json.get('items', [])
        region_name = store_address.split()[0] if store_address else ""
        search_query = f"{region_name} {store_name}".strip()
        print(f"네이버 가맹점 검증 중: [{search_query}]")
        store_info = self.verifier.get_store_category(search_query)

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