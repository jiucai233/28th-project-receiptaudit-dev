import json
import time
import matplotlib.pyplot as plt
from pathlib import Path
from difflib import SequenceMatcher
from dotenv import load_dotenv

from core.audit_agent.reasoning import AuditReasoning
from core.audit_agent.naver_verifier import NaverStoreVerifier
from core.ocr_engine.paddle_wrapper import PaddleOCRWrapper
from core.ocr_engine.processor import ReceiptProcessor
import os

def _normalize(text: str) -> str:
    return text.replace(" ", "")

def _score_store_name(result: str, answer: str) -> float:
    if not answer: return 1.0 if not result else 0.0
    if not result: return 0.0
    if result == answer: return 1.0
    r, a = _normalize(result), _normalize(answer)
    if r == a: return 1.0
    if a in r or r in a: return max(len(min(r, a, key=len)) / len(max(r, a, key=len)), 0.8)
    return SequenceMatcher(None, r, a).ratio()

def _score_item(r_item: dict, a_item: dict) -> float:
    r_name, a_name = _normalize(r_item.get("name", "")), _normalize(a_item.get("name", ""))
    name_sim = SequenceMatcher(None, r_name, a_name).ratio()
    if name_sim < 0.4: return 0.0
    price_match = 1.0 if r_item.get("price") == a_item.get("price") else 0.0
    return name_sim * 0.5 + price_match * 0.5

def get_overall_accuracy(receipt: dict, answer: dict) -> float:
    s_store = _score_store_name(receipt.get("store_name", ""), answer.get("store_name", ""))
    result_items = receipt.get("items", [])
    answer_items = answer.get("items", [])
    
    total_item_score = 0.0
    max_items = max(len(result_items), len(answer_items))
    
    if not answer_items and not result_items:
        total_item_score = 1.0
        max_items = 1
    elif not result_items or not answer_items:
        total_item_score = 0.0
    else:
        used = set()
        for a_item in answer_items:
            best_score, best_idx = 0.0, -1
            for i, r_item in enumerate(result_items):
                if i in used: continue
                score = _score_item(r_item, a_item)
                if score > best_score:
                    best_score, best_idx = score, i
            if best_idx >= 0 and best_score > 0:
                used.add(best_idx)
            total_item_score += best_score

    total_entities = 1 + max_items
    return (s_store + total_item_score) / total_entities

def run_ocr_similarity_benchmark():
    load_dotenv()
    agent = AuditReasoning()
    verifier = NaverStoreVerifier(
        client_id=os.getenv("NAVER_CLIENT_ID", ""),
        client_secret=os.getenv("NAVER_CLIENT_SECRET", "")
    )
    
    result_path = Path("core/audit_agent/test/result.json")
    answer_path = Path("core/audit_agent/test/answer.json")
    
    with open(result_path, "r", encoding="utf-8") as f:
        raw_ocrs = json.load(f)
    with open(answer_path, "r", encoding="utf-8") as f:
        answers = json.load(f)

    TEST_COUNT = min(len(raw_ocrs), len(answers))
    print(f"--- Starting OCR Similarity Benchmark (Samples: {TEST_COUNT}) ---")

    methods = [
        {"id": "M1", "name": "Pure OCR"},
        {"id": "M2", "name": "OCR + Naver"},
        {"id": "M3", "name": "OCR + LLM"},
        {"id": "M4", "name": "OCR + Naver + LLM"}
    ]

    scores = {m["id"]: 0.0 for m in methods}
    
    for i in range(TEST_COUNT):
        raw_receipt = raw_ocrs[i]
        answer = answers[i]
        
        print(f"[{i+1}/{TEST_COUNT}] Target: {answer.get('store_name')}")
        
        # M1: Pure OCR
        acc_m1 = get_overall_accuracy(raw_receipt, answer)
        scores["M1"] += acc_m1
        
        store_name = raw_receipt.get('store_name', '')
        store_address = raw_receipt.get('store_address', '')
        
        # M2: OCR + Naver API
        store_info = verifier.get_store_category(store_name, store_address)
        m2_receipt = raw_receipt.copy()
        if "store_name" in store_info and store_info["store_name"]:
            m2_receipt["store_name"] = store_info["store_name"]
            
        acc_m2 = get_overall_accuracy(m2_receipt, answer)
        scores["M2"] += acc_m2
        
        # M3: OCR + LLM
        m3_receipt = agent.correct_receipt(raw_receipt)
        acc_m3 = get_overall_accuracy(m3_receipt, answer)
        scores["M3"] += acc_m3
        
        # M4: OCR + Naver API + LLM
        m4_receipt = m3_receipt.copy()
        store_name_m4 = m4_receipt.get('store_name', '')
        store_address_m4 = m4_receipt.get('store_address', '')
        store_info_m4 = verifier.get_store_category(store_name_m4, store_address_m4)
        if "store_name" in store_info_m4 and store_info_m4["store_name"]:
            m4_receipt["store_name"] = store_info_m4["store_name"]
            
        acc_m4 = get_overall_accuracy(m4_receipt, answer)
        scores["M4"] += acc_m4
        
        print(f"  [M1] {acc_m1*100:.1f}% | [M2] {acc_m2*100:.1f}% | [M3] {acc_m3*100:.1f}% | [M4] {acc_m4*100:.1f}%")

    final_avg = [
        (scores["M1"] / TEST_COUNT) * 100,
        (scores["M2"] / TEST_COUNT) * 100,
        (scores["M3"] / TEST_COUNT) * 100,
        (scores["M4"] / TEST_COUNT) * 100
    ]

    # Visualization
    plt.rcParams['font.family'] = 'AppleGothic'  # Mac font
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    labels = [m["name"].replace(" + ", "\n") for m in methods]
    colors = ['#95a5a6', '#f39c12', '#3498db', '#e74c3c'] 
    
    bars = ax.bar(labels, final_avg, color=colors, width=0.5, alpha=0.9)
    ax.set_ylim(0, 110)
    ax.set_ylabel('Similarity to Ground Truth (%)', fontsize=12, fontweight='bold')
    
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 1, f'{yval:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')

    plt.title(f'OCR Similarity Benchmark by Method (Samples: {TEST_COUNT})', fontsize=15, pad=20)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    save_path = "core/audit_agent/test/ocr_similarity_benchmark.png"
    plt.savefig(save_path, dpi=300)
    print(f"\nBenchmark completed. Chart saved to: {save_path}")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    run_ocr_similarity_benchmark()
