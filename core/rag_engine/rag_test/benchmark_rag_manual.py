import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

import json
import os
from dotenv import load_dotenv

from langchain_upstage import ChatUpstage 

from core.rag_engine.embedder import RegulationEmbedder
from core.rag_engine.vector_db import VectorDBManager

def run_rag_export_benchmark():
    load_dotenv()
    
    embedder = RegulationEmbedder()
    db_manager = VectorDBManager(persist_path="./data/vector_store")
    
    pdf_path = Path("data/raw/organization_policy.pdf")
    if pdf_path.exists() and not os.path.exists("./data/vector_store"):
        print("PDF를 먼저 임베딩합니다")
        docs = embedder.split_documents(str(pdf_path))
        db_manager.create_db(docs, embedder.get_embedding_model())
        print("임베딩 완료\n")
        
    agent_llm = ChatUpstage() 

    answer_path = Path("core/rag_engine/rag_test/test_answers_with_expected.json")
    if not answer_path.exists():
        print(f"{answer_path} 파일이 없습니다")
        return

    with open(answer_path, "r", encoding="utf-8") as f:
        answers = json.load(f)

    output_md_file = "core/rag_engine/rag_test/rag_search_results.md"
    output_json_file = "core/rag_engine/rag_test/rag_search_results.json"
    json_results_log = []
    
    print(f"총 {len(answers)}개 영수증 검색 시작!")
    print(f"   (결과를 '{output_md_file}'와 '{output_json_file}'에 저장합니다)\n")

    with open(output_md_file, "w", encoding="utf-8") as out_f:
        out_f.write("# RAG 검색 및 리랭킹 결과 리포트\n\n")
        
        for i, ans_data in enumerate(answers):
            store_name = ans_data.get("store_name", "이름없음")
            items = ans_data.get("items", [])
            expected_rule = ans_data.get("expected_rule_keyword", "")
            
            out_f.write(f"## [{i+1}/{len(answers)}] 상호명: {store_name}\n")
            out_f.write(f"- **구매 품목**: `{items}`\n\n")
            
            query_json = json.dumps({"store_name": store_name, "items": items}, ensure_ascii=False)
            
            retrieved_docs = db_manager.search_rules(
                query=query_json, 
                embedding_model=embedder.get_embedding_model(), 
                k=3, 
                agent_llm=agent_llm
            )
            
            out_f.write("### [검색 및 리랭킹된 규정 Top 3]\n")
            
            retrieved_texts = []
            
            for rank, doc in enumerate(retrieved_docs, 1):
                content_preview = doc.page_content.replace('\n', ' ').strip()
                out_f.write(f"**{rank}위**: {content_preview}\n\n")
                retrieved_texts.append(doc.page_content)
            
            out_f.write("---\n\n")

            json_results_log.append({
                "receipt_id": ans_data.get("receipt_id", f"receipt_{i+1}"),
                "store_name": store_name,
                "items": items,
                "expected_rule_keyword": expected_rule,
                "retrieved_documents": retrieved_texts
            })
            
            print(f"[{i+1}/{len(answers)}] {store_name} 검색 완료")

    with open(output_json_file, "w", encoding="utf-8") as jf:
        json.dump(json_results_log, jf, ensure_ascii=False, indent=2)

    print(f"\n마크다운 파일과 JSON 파일이 모두 저장되었습니다")

if __name__ == "__main__":
    run_rag_export_benchmark()