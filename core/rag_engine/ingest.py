import os
from .embedder import RegulationEmbedder
from .vector_db import VectorDBManager

def run_ingestion(pdf_path):
    embedder = RegulationEmbedder()
    db_manager = VectorDBManager()
    
    # 규정 문서는 일단 pdf 문서라고 가정하고 코드 작성하였습니다! 추후 규정 문서가 어떤 형식인지에 따라서 변경하면 될 것 같아요!
    print(f"--- '{pdf_path}' split 진행 중 ---")
    chunks = embedder.split_documents(pdf_path)
    
    # 규정 문서 벡터화
    print(f"--- 벡터화 및 벡터 DB 생성 중 (경로: ./data/vector_store) ---")
    db_manager.create_db(chunks, embedder.get_embedding_model())
    
    print("--- 규정 문서 벡터 DB 구축 완료 ---")

if __name__ == "__main__":
    # 규정 pdf 경로는 임의로 설정했습니다! 이후 실제 규정 pdf가 담기는 경로에 따라서 수정하면 됩니다.
    SAMPLE_POLICY_PATH = "./data/raw/organization_policy.pdf"
    
    if os.path.exists(SAMPLE_POLICY_PATH):
        run_ingestion(SAMPLE_POLICY_PATH)
    else:
        print(f"에러: {SAMPLE_POLICY_PATH} 파일을 찾을 수 없습니다.")