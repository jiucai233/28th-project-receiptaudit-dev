"""
Upload Component - Receipt image upload interface
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import SUPPORTED_IMAGE_FORMATS, MAX_UPLOAD_SIZE


def render_upload_section():
    """
    Render the file upload section

    Returns:
        Uploaded file object or None
    """

    st.markdown("""
    ### 📸 영수증 이미지 업로드

    다음 형식의 이미지를 업로드할 수 있습니다:
    - JPG, JPEG, PNG, BMP
    - 최대 파일 크기: 10MB
    """)

    # File uploader
    uploaded_files = st.file_uploader(
        "영수증 이미지를 선택하세요",
        type=SUPPORTED_IMAGE_FORMATS,
        help="지원 형식: JPG, JPEG, PNG, BMP (최대 10MB)",
        accept_multiple_files=True
    )

    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)}개의 이미지가 선택되었습니다.")
        
        # Display a small preview of the first few
        cols = st.columns(min(len(uploaded_files), 4))
        for i, file in enumerate(uploaded_files[:4]):
            with cols[i]:
                st.image(file, caption=f"File {i+1}", use_container_width=True)
        
        if len(uploaded_files) > 4:
            st.write(f"...외 {len(uploaded_files)-4}개")

        return uploaded_files

    else:
        # Show sample instructions
        st.info("""
        💡 **팁:**
        - 영수증이 잘 보이도록 촬영해주세요
        - 조명이 밝은 곳에서 찍으면 인식률이 높아집니다
        - 영수증이 구겨지지 않도록 펼쳐서 촬영하세요
        """)

        # Show sample image (placeholder)
        with st.expander("📋 샘플 영수증 예시 보기"):
            st.markdown("""
            **좋은 예:**
            - ✅ 텍스트가 선명하게 보임
            - ✅ 그림자나 반사가 없음
            - ✅ 영수증 전체가 프레임 안에 들어옴

            **나쁜 예:**
            - ❌ 흐릿하거나 초점이 맞지 않음
            - ❌ 빛 반사로 일부가 안 보임
            - ❌ 영수증이 잘림
            """)

        return None


def render_upload_history():
    """
    Render upload history (optional feature)
    Can be used to show previously uploaded receipts
    """
    if 'upload_history' not in st.session_state:
        st.session_state.upload_history = []

    if st.session_state.upload_history:
        st.markdown("### 📜 최근 업로드 기록")

        for idx, history_item in enumerate(st.session_state.upload_history[-5:]):  # Show last 5
            with st.expander(f"{history_item['date']} - {history_item['store_name']}"):
                st.write(f"Receipt ID: {history_item['receipt_id']}")
                st.write(f"Total: {history_item['total_price']:,}원")
                if st.button(f"다시 불러오기", key=f"reload_{idx}"):
                    st.session_state.receipt_data = history_item
                    st.rerun()
