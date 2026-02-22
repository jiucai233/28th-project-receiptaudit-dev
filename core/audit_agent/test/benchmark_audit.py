import json
import time
import matplotlib.pyplot as plt
from pathlib import Path
from dotenv import load_dotenv

from core.audit_agent.reasoning import AuditReasoning
from core.rag_engine.embedder import RegulationEmbedder
from core.rag_engine.vector_db import VectorDBManager

def run_audit_rag_benchmark():
    load_dotenv()
    agent = AuditReasoning()
    
    print("[1단계] 규정 PDF 파일을 Vector DB에 임베딩합니다...")
    pdf_path = Path("data/raw/organization_policy.pdf")

    embedder = RegulationEmbedder()
    db_manager = VectorDBManager()
    
    try:
        docs = embedder.split_documents(str(pdf_path))
        db_manager.add_documents(docs, embedder.get_embedding_model())
        print(f"총 {len(docs)}개의 규정 조항이 DB에 적재되었습니다.\n")
    except Exception as e:
        print(f"임베딩 실패: {e}")
        return

    answer_path = Path("core/audit_agent/test/test_answers_with_expected.json") 
    corrected_path = Path("core/audit_agent/test/test_corrected_ocr.json") 
    
    with open(answer_path, "r", encoding="utf-8") as f:
        answers = json.load(f)
    with open(corrected_path, "r", encoding="utf-8") as f:
        corrected_ocrs = json.load(f)

    TEST_COUNT = min(len(answers), len(corrected_ocrs))
    metrics = {"answer": {"correct": 0}, "corrected": {"correct": 0}}
    
    json_results_log = []

    print(f" [2단계] 풀 파이프라인(RAG + LLM) 감사 벤치마크 시작 (샘플 {TEST_COUNT}개)\n")

    for i in range(TEST_COUNT):
        ans_data = answers[i]
        corr_data = corrected_ocrs[i]
        
        expected = ans_data.get("expected", "Pass") 
        store_name = ans_data.get("store_name", f"영수증 {i+1}")
        
        print(f"[{i+1}/{TEST_COUNT}]  {store_name} (목표 정답: {expected})")
        
        # [A] 정답지 데이터 감사
        query_json_a = json.dumps(ans_data, ensure_ascii=False)
        retrieved_docs_a = db_manager.search_rules(query_json_a, embedder.get_embedding_model(), k=3)
        rules_a = "\n\n".join(doc.page_content for doc in retrieved_docs_a)
        
        res_a = agent.analyze(ans_data, retrieved_rules=rules_a)
        decision_a = res_a.get('audit_decision')
        if decision_a == expected:
            metrics["answer"]["correct"] += 1
            
        print(f"   [정답지 주입] 판정: {decision_a} | 점수: {res_a.get('violation_score')}")

        query_json_b = json.dumps(corr_data, ensure_ascii=False)
        retrieved_docs_b = db_manager.search_rules(query_json_b, embedder.get_embedding_model(), k=3)
        rules_b = "\n\n".join(doc.page_content for doc in retrieved_docs_b)
        
        res_b = agent.analyze(corr_data, retrieved_rules=rules_b)
        decision_b = res_b.get('audit_decision')
        if decision_b == expected:
            metrics["corrected"]["correct"] += 1
            
        print(f"   [수정본 주입] 판정: {decision_b} | 점수: {res_b.get('violation_score')}")
        print("-" * 50)
        
        json_results_log.append({
            "receipt_id": ans_data.get("receipt_id"),
            "store_name": store_name,
            "expected_decision": expected,
            "test_on_ground_truth": {
                "is_correct_match": decision_a == expected,
                "llm_raw_output": res_a
            },
            "test_on_corrected_ocr": {
                "is_correct_match": decision_b == expected,
                "llm_raw_output": res_b
            }
        })

    output_json_path = "core/audit_agent/test/benchmark_audit_results.json"
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(json_results_log, f, ensure_ascii=False, indent=2)
    print(f"\n상세 감사 결과가 '{output_json_path}'에 저장되었습니다.")

    acc_answer = (metrics["answer"]["correct"] / TEST_COUNT) * 100
    acc_corrected = (metrics["corrected"]["correct"] / TEST_COUNT) * 100

    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False
    fig, ax1 = plt.subplots(figsize=(8, 6))
    
    bars = ax1.bar(['정답지(Ground Truth)', '오타 수정본(Corrected OCR)'], 
                   [acc_answer, acc_corrected], 
                   color=['#3498db', '#e74c3c'], width=0.5)
    ax1.set_ylim(0, 110)
    ax1.set_ylabel('감사 정답률 (%)', fontsize=12)

    for bar in bars:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, yval + 2, f'{yval:.1f}%', ha='center', va='bottom', fontweight='bold')

    plt.title('RAG 기반 AI 감사관 파이프라인 정답률 비교', fontsize=15, pad=15)
    plt.tight_layout()
    plt.savefig("core/audit_agent/test/benchmark_rag_audit.png", dpi=300)
    print("비교 그래프가 저장되었습니다.")

if __name__ == "__main__":
    run_audit_rag_benchmark()