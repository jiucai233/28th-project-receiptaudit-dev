"""
Data Editor Component - Editable table for receipt data
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any


def render_data_editor(receipt_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Render editable table for receipt data

    Args:
        receipt_data: Dictionary containing receipt information

    Returns:
        Updated receipt data dictionary
    """

    st.markdown("### 📝 영수증 정보")

    # Basic information (non-editable display)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("영수증 ID", receipt_data.get('receipt_id', 'N/A'))

    with col2:
        store_name = st.text_input(
            "가게명",
            value=receipt_data.get('store_name', ''),
            key="store_name_input"
        )
        receipt_data['store_name'] = store_name

    with col3:
        date = st.text_input(
            "날짜 및 시간",
            value=receipt_data.get('date', ''),
            key="date_input"
        )
        receipt_data['date'] = date

    st.markdown("---")

    # Items table (editable)
    st.markdown("### 🛒 구매 품목 (편집 가능)")

    items = receipt_data.get('items', [])

    if items:
        # Convert items to DataFrame
        df = pd.DataFrame(items)

        # Reorder columns for better UX
        column_order = ['id', 'name', 'unit_price', 'count', 'price']
        df = df[column_order]

        # Column configuration for better display
        column_config = {
            'id': st.column_config.NumberColumn(
                'ID',
                help='품목 ID (자동 생성)',
                disabled=True,
                width='small'
            ),
            'name': st.column_config.TextColumn(
                '품목명',
                help='구매한 상품의 이름',
                max_chars=50,
                width='medium'
            ),
            'unit_price': st.column_config.NumberColumn(
                '단가',
                help='개당 가격',
                min_value=0,
                format='₩%d',
                width='small'
            ),
            'count': st.column_config.NumberColumn(
                '수량',
                help='구매 개수',
                min_value=1,
                max_value=999,
                width='small'
            ),
            'price': st.column_config.NumberColumn(
                '금액',
                help='총 금액 (단가 × 수량)',
                min_value=0,
                format='₩%d',
                width='small'
            ),
        }

        # Editable data editor
        edited_df = st.data_editor(
            df,
            column_config=column_config,
            num_rows="dynamic",  # Allow adding/deleting rows
            use_container_width=True,
            key="items_editor"
        )

        # Update price based on unit_price and count
        edited_df['price'] = edited_df['unit_price'] * edited_df['count']

        # Convert back to list of dicts
        receipt_data['items'] = edited_df.to_dict('records')

        # Calculate total
        total_price = edited_df['price'].sum()
        receipt_data['total_price'] = total_price

        st.markdown("---")

        # Display total
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            st.markdown("### 총합계")
        with col3:
            st.markdown(f"### ₩{total_price:,}")

        # Tips
        with st.expander("💡 편집 방법"):
            st.markdown("""
            - **수정**: 셀을 더블클릭하여 값을 변경할 수 있습니다
            - **행 추가**: 테이블 하단의 '+' 버튼을 클릭합니다
            - **행 삭제**: 왼쪽 체크박스를 선택한 후 Delete 키를 누릅니다
            - **자동 계산**: 단가와 수량을 수정하면 금액이 자동으로 계산됩니다
            """)

    else:
        st.warning("⚠️ 추출된 품목이 없습니다. 직접 추가할 수 있습니다.")

        # Manual input form
        with st.form("manual_item_form"):
            st.markdown("#### 품목 수동 추가")

            col1, col2, col3 = st.columns(3)

            with col1:
                item_name = st.text_input("품목명")
            with col2:
                unit_price = st.number_input("단가", min_value=0, step=100)
            with col3:
                count = st.number_input("수량", min_value=1, max_value=999, step=1)

            submitted = st.form_submit_button("품목 추가")

            if submitted and item_name:
                new_item = {
                    'id': len(receipt_data.get('items', [])) + 1,
                    'name': item_name,
                    'unit_price': unit_price,
                    'count': count,
                    'price': unit_price * count
                }

                if 'items' not in receipt_data:
                    receipt_data['items'] = []

                receipt_data['items'].append(new_item)
                st.success(f"✅ '{item_name}' 추가 완료!")
                st.rerun()

    return receipt_data


def render_summary_card(receipt_data: Dict[str, Any]):
    """
    Render a summary card for receipt data

    Args:
        receipt_data: Dictionary containing receipt information
    """

    with st.container():
        st.markdown("""
        <style>
        .summary-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="summary-card">', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**가게명:** {receipt_data.get('store_name', 'N/A')}")
            st.markdown(f"**날짜:** {receipt_data.get('date', 'N/A')}")

        with col2:
            st.markdown(f"**품목 수:** {len(receipt_data.get('items', []))}개")
            st.markdown(f"**총액:** ₩{receipt_data.get('total_price', 0):,}")

        st.markdown('</div>', unsafe_allow_html=True)
