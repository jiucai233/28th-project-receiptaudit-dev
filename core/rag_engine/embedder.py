from dotenv import load_dotenv
from langchain_upstage import UpstageEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

load_dotenv()

class RegulationEmbedder:
    def __init__(self):
        self.embeddings = UpstageEmbeddings(model="solar-embedding-1-large")
        # TODO 규정 끊는 단위를 우선 문단 단위로 설정했습니다! 이건 확인해보시고 우선순위를 어떻게 정할 지 함께 이야기해보면 좋을 것 같아요!
        '''
        chunk_size: 600자 내외로 규정을 자릅니다.
        chunk_overlap: 문맥 유지를 위해서 chunk 사이에 100자의 겹치는 구간을 설정했습니다.
        separators: 우선순위에 따라서 문단을 자릅니다.
            - 1순위: "\n\n"(문단 기준)
            - 2순위: "\n"(줄바꿈 기준)
            - 3순위: "제"(보통 규정집에서는 조항마다 '제1조'처럼 되어있는 경우가 많으므로, '제'라는 글자를 기준)
            - 4순위: "."(그래도 안되면 문장 끝마침표 기준)
        '''
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            separators=["\n\n", "\n", "제", "."]
        )

    def get_chunks(self, text_list):
        # text_list를 받아서, LangChain이 이해할 수 있는 Document 객체들의 리스트로 변환함
        return self.text_splitter.create_documents(text_list)

    def get_embedding_model(self):
        return self.embeddings
    
    def split_documents(self, file_path: str):
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        return self.text_splitter.split_documents(docs)