from dotenv import load_dotenv
import os
from langchain_upstage import UpstageEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader

load_dotenv()

class RegulationEmbedder:
    def __init__(self):
        self.embeddings = UpstageEmbeddings(model="solar-embedding-1-large")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            separators=[
                r"\n(?=제\s*[0-9]+\s*(?:조|장))",
                r"(?=제\s*[0-9]+\s*(?:조|장))",
                r"\n\n",                     
                r"\n",                       
                r"(?<=\.) "
            ],
            is_separator_regex=True
        )

    def get_chunks(self, text: str):
        # text를 받아서, LangChain이 이해할 수 있는 Document 객체들의 리스트로 변환함
        return self.text_splitter.create_documents([text])

    def get_embedding_model(self):
        return self.embeddings
    
    def split_documents(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            loader = PyPDFLoader(file_path)
        elif ext == '.docx' or ext == '.doc':
            loader = Docx2txtLoader(file_path)
        elif ext == '.txt':
            loader = TextLoader(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")
            
        docs = loader.load()
        return self.text_splitter.split_documents(docs)
