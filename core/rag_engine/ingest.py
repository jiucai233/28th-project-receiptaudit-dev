import os
from core.rag_engine.embedder import RegulationEmbedder
from core.rag_engine.vector_db import VectorDBManager
from langchain_community.document_loaders import PyPDFLoader

def run_ingestion(file_path):
    """
    [실시간 임베딩] 새로운 규정 PDF를 즉시 벡터화하여 DB에 추가함.
    백엔드의 POST /upload 엔드포인트에서 이 함수를 호출하면 됨.
    """
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return False

    embedder = RegulationEmbedder()
    db_manager = VectorDBManager()

    # 1. 문서 로드 및 청크 분할
    loader = PyPDFLoader(file_path)
    # embedder 내부에 정의된 text_splitter 사용
    docs = loader.load_and_split(embedder.text_splitter)

    # 2. 벡터 DB 생성 및 저장 (기존 DB에 병합됨)
    db_manager.create_db(docs, embedder.get_embedding_model())
    print(f"--- {os.path.basename(file_path)} 실시간 임베딩 완료! ---")
    return True

if __name__ == "__main__":
    # 규정 pdf 경로는 임의로 설정했습니다! 이후 실제 규정 pdf가 담기는 경로에 따라서 수정하면 됩니다.
    SAMPLE_POLICY_PATH = "./data/raw/organization_policy.pdf"
    
    if os.path.exists(SAMPLE_POLICY_PATH):
        run_ingestion(SAMPLE_POLICY_PATH)
    else:
        print(f"에러: {SAMPLE_POLICY_PATH} 파일을 찾을 수 없습니다.")