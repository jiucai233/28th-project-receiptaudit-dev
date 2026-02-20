from __future__ import annotations
import re
import uuid
from datetime import datetime


class ReceiptProcessor:
    """OCR 추출 텍스트를 정규화하고 구조화된 JSON으로 변환"""

    # 날짜+시간 패턴 (시간 포함 패턴을 먼저 매칭)
    DATE_PATTERNS = [
        # "2026/01/12(월) 12:44" — 요일 괄호 사이에 시간
        r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\([월화수목금토일]+\)\s*(\d{1,2}:\d{2})",
        # "2024/11/17/17:23" — 슬래시로 날짜+시간 연결
        r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})/(\d{1,2}:\d{2})",
        # "2025-10-03 16:47" — 4자리 연도 + 시간 (공백)
        r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\s+(\d{1,2}:\d{2})",
        # "2025-10-0316:47" — 4자리 연도 + 시간 (붙어있음)
        r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})(\d{2}:\d{2})",
        # "25/09/21 15:47" — 2자리 연도 + 시간
        r"(\d{2}[-/.]\d{1,2}[-/.]\d{1,2})\s+(\d{1,2}:\d{2})",
        # "25/09/2115:47" — 2자리 연도 + 시간 (붙어있음)
        r"(\d{2}[-/.]\d{1,2}[-/.]\d{1,2})(\d{2}:\d{2})",
        # 4자리 연도 날짜만 (시간 없음)
        r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})()",
        # 2자리 연도 날짜만
        r"(\d{2}[-/.]\d{1,2}[-/.]\d{1,2})()",
    ]

    # 날짜 컨텍스트 키워드 (우선순위순)
    DATE_CONTEXT_KEYWORDS = [
        "거래일시", "거래일", "계산일자", "발행일시", "승인일시", "결제일시",
        "판매일자", "판매시간", "일시", "일자", "날짜",
    ]

    TOTAL_KEYWORDS = [
        "합계", "합제", "총액", "총합", "결제금액", "총결제",
        "카드결제", "total", "Total", "TOTAL",
    ]

    # 품목이 아닌 줄을 걸러내기 위한 키워드
    SKIP_KEYWORDS = [
        # 영수증 메타 정보
        "사업자", "대표", "전화", "주소", "승인번호", "카드번호",
        "거래일시", "거래번호", "단말기", "가맹점", "캐셔",
        "직원:", "POS", "BILL",
        # 세금/소계 관련
        "소계", "부가세", "가세", "가액",
        "매출", "세액", "판매계", "판매금",
        "과세물품", "면세물품", "포함됨", "포함된",
        "상품가격",
        # 결제 관련
        "결제액", "결제금", "잔여", "거스름", "할인액", "할인일",
        "신용카드", "카드결제", "DV(", "비씨", "BeV",
        "결제수단", "결제내역", "결제대상",
        # 포인트/회원
        "회원", "포인트", "적립", "마일리지",
        # 기타 비품목 줄
        "승인VAN", "일시불", "환불", "교환", "지참",
        "담당", "계산담당", "수량", "금액", "단가", "상품명", "상품코드",
        "주문번호",
        "봉사료", "CATID", "캐셔No", "승인",
        "영수증", "바코드", "SCO:",
        "여신", "금융", "협회",
        "일회용", "비널봉투",
        # 할인/배달 관련
        "할인 내역", "배달비", "주문금액",
        # 구매수량 표시줄
        "구매수량",
        # 부가세율 테이블
        "부가세율",
        # 제휴/할인 관련
        "제휴할인", "제휴카드", "매출전표",
        "행사할인",
        # 결제방식/원산지/기타
        "결제방식", "원산지",
        # 영수증 번호 (OCR 가비지 포함)
        "영수",
        # OCR 가비지 (합계/금액 계열 오인식)
        "글액", "급액",
        # 받은돈/거스름/공급대가/VAN사
        "받은돈", "거스름돈", "공급대가",
        "KOCES", "KSNET",
        # 공급가 계열 (OCR 가비지 포함)
        "공급가", "급가",
        # 메뉴 옵션/선택 (품목이 아닌 수식어)
        "선택안함",
        # OCR 가비지 (소계/부가세/총구매액 오인식)
        "손계", "구매액", "부가",
    ]

    # 가게명이 아닌 줄을 걸러내기 위한 키워드
    STORE_SKIP_KEYWORDS = [
        "사업자", "등록번호", "대표", "전화", "주소", "TEL",
        "픽업번호", "주문번호", "주문변호", "거래",
        "영수", "고객", "재발행", "대기번호", "매장식사",
        "소비자중심경영", "인증기업", "CCM",
        "제품명", "교환", "환불",
        "판매시간", "POS", "P0S",
    ]

    # 주소 레이블 패턴 (OCR 오류 포함, 콜론 없는 경우 포함)
    ADDRESS_LABEL_PATTERNS = [
        r"주\s*소\s*[:：]\s*(.+)",           # "주소:", "주 소:"
        r"\[주\s*소\]\s*(.+)",               # "[주소]서울..." (대괄호 포맷)
        r"주[\s\-]+소\s*[:：\s]\s*(.+)",     # "[주-소" 하이픈/공백 포함 패턴
        r"추\s*도?\s*소\s*[:：]\s*(.+)",      # OCR 오류: "추 도소:"
        r"주\s*조\s*[:：]\s*(.+)",            # OCR 오류: "주 조:"
        r"주\s*소\s+([가-힣\d].{3,})",        # "주소 서울..." (콜론 없음)
        r"(?<![가-힣])소\s*[:：]\s*([가-힣][가-힣\d\s,\-]{4,})",  # "소:경기..." (앞줄에 주 잘림)
    ]

    # 시도명 (주소 탐색용)
    SIDO_NAMES = [
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
        "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
        "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원도",
        "충청북도", "충청남도", "전라북도", "전라남도", "경상북도", "경상남도",
        "제주특별자치도",
    ]

    def process(self, ocr_lines: list[dict]) -> dict:
        """OCR 줄 목록을 구조화된 영수증 JSON으로 변환

        Args:
            ocr_lines: paddle_wrapper.extract()의 반환값
                [{"text": str, "confidence": float, "bbox": list}, ...]

        Returns:
            구조화된 영수증 딕셔너리
        """
        texts = [line["text"] for line in ocr_lines]

        store_name = self._extract_store_name(texts)
        store_address = self._extract_address(texts)
        date = self._extract_date(texts)
        items = self._extract_items(texts)
        total_price = self._extract_total(texts)

        if total_price is None and items:
            total_price = sum(item["price"] for item in items)

        return {
            "receipt_id": str(uuid.uuid4()),
            "store_name": store_name or "",
            "store_address": store_address or "",
            "date": date or "",
            "items": items,
            "total_price": total_price or 0,
        }

    def _extract_store_name(self, texts: list[str]) -> str | None:
        """영수증에서 가게명 추출

        우선순위:
        1) '매장:', '상호:', '주문매장:' 등 명시적 레이블이 있는 줄
        2) 상단 10줄 중 가게명으로 적합한 첫 번째 줄
        """
        def _clean_store(name):
            """가게명 후처리 (괄호/접두사 정리)"""
            name = name.strip("[]")
            name = re.sub(r'^#\d+\s*', '', name)
            name = re.sub(r'^직영\s*', '', name)
            name = name.strip('"\'\\')
            # 사업자등록번호 패턴 제거 (예: /238-85-00709, /748-14-00040/허지은)
            name = re.sub(r'\s*/?\d{3}-\d{2}-\d{5}(?:/.*)?$', '', name)
            # 영수증번호 접미사 제거 (예: "영수증번호:251004-0103-0051-01")
            name = re.sub(r'\s*영수증\s*번호\s*[:：].*$', '', name)
            # 슬래시 이후 사업자번호/대표자명 제거 (예: "/6055800636/허지은")
            name = re.sub(r'/\d{8,}(?:/.*)?$', '', name)
            return name.strip()

        # 1단계: 전체 텍스트에서 명시적 레이블 패턴 검색
        store_label_patterns = [
            r"매\s*장\s*명?\s*[:：\[\]]\s*(.+)",    # "매장명:", "매 장 명:"
            r"\[매장명\]\s*(.+)",
            r"상\s*호\s*명?\s*[:：]\s*(.+)",
            r"주문\s*매장\s*[:：]\s*(.+)",
            r"점\s*포\s*['\"]?\s*명?\s*[:：]\s*(.+)",  # "점포명:", "점포'명:"
        ]
        for text in texts:
            for pattern in store_label_patterns:
                match = re.search(pattern, text)
                if match:
                    name = match.group(1).strip()
                    # 레이블 값에서 추가 메타 정보 제거
                    name = re.split(r"\s+TEL|전화|T\.|TID", name)[0].strip()
                    name = _clean_store(name)
                    if len(name) >= 2:
                        return name

        # 2단계: 상단 10줄에서 가게명 추출
        for text in texts[:10]:
            text = text.strip()
            # 숫자/기호로만 된 줄 스킵
            if re.match(r"^[\d\s:/.,()\-]+$", text):
                continue
            if len(text) < 2:
                continue
            # collapse_spaces 후 영수증 관련 키워드 체크 (예: "영 수 증", "영 수층")
            collapsed = self._collapse_spaces(text)
            if "영수" in collapsed:
                continue
            if any(kw in collapsed for kw in ["합계", "총합", "부가세"]):
                continue
            if any(kw in text for kw in self.STORE_SKIP_KEYWORDS):
                continue
            # 전화번호 패턴 스킵 (02-xxx, 0xx-xxx-xxxx, 070-xxxx, 1xxx-xxxx)
            if re.match(r"^[\d\-()]{7,}$", text.replace(" ", "")):
                continue
            if re.match(r"^0\d{1,2}[-\s]\d{3,4}[-\s]\d{4}", text):
                continue
            # 사업자번호로 시작하는 줄 스킵 (xxx-xx-xxxxx)
            if re.match(r"^\d{3}-\d{2}-\d{5}", text.replace(" ", "")):
                continue
            # 대표번호 패턴 스킵 (1577-xxxx, 1588-xxxx 등)
            if re.match(r"^1\d{3}[-\s]?\d{4}", text.replace(" ", "")):
                continue
            # 주소 패턴 포함 줄 스킵 ([시구군] + [로길동])
            if re.search(r"[시구군]\s+\S+[로길동]|[시구군]\s+\d+[로길동]", text):
                continue
            # 주소 패턴 (시도명으로 시작 + 구/군/동/로/길, 공백 없는 경우)
            collapsed_text = text.replace(" ", "")
            if any(collapsed_text.startswith(sido) for sido in self.SIDO_NAMES):
                if re.search(r"[구군]\S*[로길동읍면]|[동로길]\d", collapsed_text):
                    continue
            # 층수만 있는 줄 스킵 (예: "3층", "B1층")
            if re.match(r"^[B]?\d+층\s*$", text.strip()):
                continue
            # 가격 패턴으로 끝나는 줄 스킵 (품목+가격, 예: "우삼겹 폴케볼 1 9,400")
            if re.search(r"\d+,\d{3}\s*$", text):
                continue
            # POS/레지스터 관련 줄 스킵 (POS, PoS, P0S 등)
            if re.search(r"P[oO0][sS]", text):
                continue
            # 영수증/카드전표/기타 메타 키워드 스킵
            if any(kw in text for kw in [
                "신용", "전표", "카드", "FOOD", "MARKET",
                "유형", "여신", "금융", "협회", "KOCES",
                "메뉴", "수량",
            ]):
                continue
            # 후처리: TID, 전화번호 등 접미사 제거
            cleaned = re.split(r"\s+TID|TID:|전화|TEL|T\.", text)[0].strip()
            cleaned = _clean_store(cleaned)
            if len(cleaned) >= 2:
                return cleaned
        return None

    def _extract_address(self, texts: list[str]) -> str | None:
        """영수증에서 가게 주소 추출

        우선순위:
        1) '주소:' 레이블이 있는 줄에서 추출 (OCR 오류 패턴 포함)
        2) 시도명으로 시작하는 주소 패턴 탐색
        3) 시/구/군이 포함된 주소 패턴 탐색 (선행 가비지 제거)
        4) 동/로/길로 시작하는 주소 패턴 탐색
        """

        def is_valid_address(addr: str) -> bool:
            """주소 유효성 검증"""
            if len(addr) < 5:
                return False
            # 주소 구성요소 확인 (시/구/군/동/로/길 중 하나 이상)
            if not re.search(r"[시구군]|[동로길읍면리]|번지", addr):
                return False
            # 너무 짧은 주소 제외 (공백 제거 기준, 5자 미만)
            if len(addr.replace(" ", "")) < 5:
                return False
            # 전화번호만 있는 경우 제외
            if re.match(r"^[\d\-\s()]+$", addr):
                return False
            return True

        def clean_and_merge(addr: str, next_lines: list[str]) -> str:
            """주소 정리 및 다음 줄과 병합"""
            # TEL/전화 이후 제거
            addr = re.split(r"\s*(?:TEL|Tel|tel|전화|T\.|대표)", addr)[0].strip()

            # 다음 줄들을 확인하여 주소 연장 부분 병합
            for next_line in next_lines[:2]:
                next_line = next_line.strip()
                # 날짜/POS/주문 정보 포함 줄은 병합 중단
                if re.search(
                    r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|P0S|POS|BILL|테이블번호|주문담당자|레이블번호",
                    next_line, re.IGNORECASE
                ):
                    break
                # 주소 구성요소가 있고, 메타정보가 아닌 경우 병합
                if re.search(r"[동로길읍면리층호]|번지|\d+층|[\(,]\w+[\)]", next_line):
                    if not any(kw in next_line for kw in [
                        "TEL", "전화", "대표", "사업자", "등록", "TID"
                    ]):
                        next_cleaned = re.split(
                            r"\s*(?:TEL|Tel|tel|전화|T\.|대표)", next_line
                        )[0].strip()
                        addr = addr + " " + next_cleaned
                else:
                    break

            return self._clean_address(addr)

        # 1단계: 주소 레이블 패턴 (콜론 없는 경우, OCR 오류 포함)
        for i, text in enumerate(texts):
            for pattern in self.ADDRESS_LABEL_PATTERNS:
                match = re.search(pattern, text)
                if match:
                    addr = match.group(1).strip()
                    addr = clean_and_merge(addr, texts[i+1:])
                    if is_valid_address(addr):
                        return addr

        # 2단계: 상단 25줄에서 시도명으로 시작하는 주소 탐색
        for i, text in enumerate(texts[:25]):
            text_stripped = text.strip()
            for sido in self.SIDO_NAMES:
                if text_stripped.startswith(sido):
                    if re.search(r"[시구군]|[동로길읍면리]|번지", text_stripped):
                        addr = clean_and_merge(text_stripped, texts[i+1:])
                        if is_valid_address(addr):
                            return addr

        # 3단계: 시/구/군이 포함된 주소 패턴 탐색 (매칭 시작 위치부터 추출)
        for i, text in enumerate(texts[:25]):
            text_stripped = text.strip()
            match = re.search(
                r"[가-힣]+[시]\s+[가-힣]+[구군]|[가-힣]+[구]\s+[가-힣\d]+[동로길]",
                text_stripped
            )
            if match:
                # 선행 가비지(사업자번호 등) 제거: 매칭 시작 위치부터 추출
                addr = text_stripped[match.start():]
                addr = clean_and_merge(addr, texts[i+1:])
                if is_valid_address(addr):
                    if not any(kw in addr for kw in ["사업자", "등록번호", "대표자", "TEL"]):
                        return addr

        # 4단계: 동/로/길로 시작하는 주소 (덜 엄격한 매칭)
        for i, text in enumerate(texts[:25]):
            text_stripped = text.strip()
            if re.match(r"[가-힣]+[동로길]\s+[\d가-힣]", text_stripped):
                addr = clean_and_merge(text_stripped, texts[i+1:])
                if is_valid_address(addr) and len(addr) >= 10:
                    if re.search(r"\d+", addr):
                        return addr

        return None

    def _clean_address(self, addr: str) -> str:
        """주소 정리"""
        # 날짜 패턴 이후 내용 제거 (예: "2025-10-01 18:58", "2017년12월16일")
        addr = re.sub(r"\s+\d{4}[-/.]\d{1,2}[-/.]\d{1,2}.*", "", addr)
        addr = re.sub(r"\s+\d{4}년\s*\d{1,2}월.*", "", addr)

        # POS/BILL 이후 내용 제거 (예: "P0S:01BILL:000005", "POS:02 BILL:000024")
        addr = re.sub(r"\s+(?:P0S|POS|BILL)[:：]?.*", "", addr, flags=re.IGNORECASE)

        # 주문/테이블/판매/카드 관련 키워드 이후 내용 제거
        addr = re.sub(
            r"\s+(?:테이블번호|주문담당자|레이블번호|영수번호|판매시간|주문번호|호출기|계산일자|카드종|개월할부|할부).*",
            "", addr
        )

        # 방향 수식어 이후 내용 제거 (예: "1층왼쪽 (망원동)" → "1층")
        addr = re.sub(r"\s+(?:왼쪽|오른쪽|앞|뒤)\b.*$", "", addr)

        # 대표자명, 사업자번호 등 접미사 제거
        addr = re.sub(r"\s+(?:대표|사업자번호|TEL|Tel|전화|T\.).*$", "", addr).strip()

        # 끝의 특수문자 정리
        addr = addr.rstrip(".,;:(")

        # 열린 괄호가 닫히지 않은 경우: 내용이 너무 짧으면 제거, 길면 닫기
        if addr.count("(") > addr.count(")"):
            last_open = addr.rfind("(")
            content_after = addr[last_open + 1:]
            if len(content_after) <= 3:
                addr = addr[:last_open].rstrip(" ,")
            else:
                addr = addr + ")"

        # 괄호 뒤에 번지 없이 텍스트가 이어지면 제거 (반복 텍스트 패턴)
        # 예: "(행신동) 세신웨미리타" → "(행신동)"
        addr = re.sub(r"(\([가-힣]+(?:동|구|읍|면|리)\))\s+[가-힣]+$", r"\1", addr)

        # 연속 공백 정리
        addr = re.sub(r"\s+", " ", addr)

        # OCR 오류 보정
        addr = addr.replace("서올", "서울")
        addr = addr.replace("서을", "서울")    # "서을강남구" → "서울강남구"
        addr = addr.replace("서물", "서울")    # "서물특별시" → "서울특별시"
        addr = addr.replace("감남구", "강남구")  # "서울감남구" → "서울강남구"
        addr = addr.replace("선름로", "선릉로")
        addr = addr.replace("선롱로", "선릉로")
        addr = addr.replace("테혜란로", "테헤란로")
        addr = addr.replace("발천구덕", "금천구")
        addr = addr.replace("금천구덕", "금천구")

        # 구두점/특수문자 정리
        addr = addr.replace("'", " ").replace("`", " ").replace("_", " ")
        addr = re.sub(r"\s+", " ", addr)

        return addr.strip()

    def _is_valid_date(self, date_str: str) -> bool:
        """날짜 문자열이 유효한지 검증 (사업자번호 등 제외)"""
        parts = re.split(r"[-/.]", date_str)
        if len(parts) != 3:
            return False
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            return False

        # 4자리 연도
        if nums[0] >= 1900:
            year, month, day = nums
        # 2자리 연도
        elif nums[0] <= 99:
            year, month, day = nums[0] + 2000, nums[1], nums[2]
        else:
            return False

        # 월, 일 범위 검증
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return False
        # 2000~2030 범위의 연도만 허용
        if not (2000 <= year <= 2030):
            return False
        return True

    def _extract_date(self, texts: list[str]) -> str | None:
        """날짜/시간 추출 및 정규화

        처리 순서:
        0) YYYYMMDD.HH:MM 형식 처리 (구분자 없는 8자리 날짜)
        1) 날짜 컨텍스트 키워드가 있는 줄 우선 탐색
        2) 같은 줄에 날짜+시간이 있는 경우
        3) '계산일자:', '시간:' 등으로 분리된 경우 병합
        4) 한국어 오전/오후 시간 처리
        """
        # 0단계: YYYYMMDD.HH:MM 형식 (예: "20251001.18:49:58")
        for text in texts:
            m = re.search(r"(\d{4})(\d{2})(\d{2})[.](\d{1,2}:\d{2})", text)
            if m:
                date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                time_str = m.group(4)
                if self._is_valid_date(date_str):
                    return self._normalize_date(date_str, time_str)

        found_date = None
        found_time = None
        found_date_line_idx = None

        # 1단계: 날짜 컨텍스트 키워드가 있는 줄에서 우선 탐색
        for i, text in enumerate(texts):
            collapsed = self._collapse_spaces(text)
            if any(kw in collapsed for kw in self.DATE_CONTEXT_KEYWORDS):
                # 같은 줄에서 날짜+시간 추출 시도
                for pattern in self.DATE_PATTERNS:
                    match = re.search(pattern, text)
                    if match:
                        date_part = match.group(1)
                        time_part = match.group(2) if match.group(2) else ""
                        if self._is_valid_date(date_part):
                            if time_part:
                                return self._normalize_date(date_part, time_part)
                            found_date = date_part
                            found_date_line_idx = i
                            break

                # 한국어 오전/오후 시간이 같은 줄에 있는 경우
                if found_date and not found_time:
                    ampm_match = re.search(
                        r"(오전|오후)\s*(\d{1,2}):(\d{2})", text
                    )
                    if ampm_match:
                        found_time = self._parse_ampm_time(ampm_match)

                # 날짜를 찾았으면 시간 탐색 후 반환
                if found_date:
                    if not found_time:
                        # 같은 줄에 "시간: HH:MM" 패턴이 있는 경우 (예: "계산일자:2024-11-10 시간:13:49")
                        same_line_time = re.search(
                            r"시간\s*[:：]\s*(\d{1,2}:\d{2})", texts[found_date_line_idx]
                        )
                        if same_line_time:
                            found_time = same_line_time.group(1)
                    if not found_time:
                        found_time = self._search_time_nearby(
                            texts, found_date_line_idx
                        )
                    return self._normalize_date(found_date, found_time or "")

        # 2단계: 전체 텍스트에서 날짜 패턴 탐색
        for i, text in enumerate(texts):
            # 사업자번호 줄은 건너뛰기
            if any(kw in text for kw in ["사업자", "등록번호"]):
                continue

            for pattern in self.DATE_PATTERNS:
                match = re.search(pattern, text)
                if match:
                    date_part = match.group(1)
                    time_part = match.group(2) if match.group(2) else ""

                    if not self._is_valid_date(date_part):
                        continue

                    if time_part:
                        return self._normalize_date(date_part, time_part)

                    if found_date is None:
                        found_date = date_part
                        found_date_line_idx = i

                        # 같은 줄에 "시간: HH:MM" 패턴이 있는 경우
                        same_line_time = re.search(
                            r"시간\s*[:：]\s*(\d{1,2}:\d{2})", text
                        )
                        if same_line_time:
                            found_time = same_line_time.group(1)
                        else:
                            # 인접 줄에서 시간 탐색
                            found_time = self._search_time_nearby(texts, i)

                    break  # 이미 이 줄에서 날짜 패턴 찾음

            # 오전/오후 시간이 별도 줄에 있는 경우
            if found_date and not found_time:
                ampm_match = re.search(
                    r"(오전|오후)\s*(\d{1,2}):(\d{2})", text
                )
                if ampm_match:
                    found_time = self._parse_ampm_time(ampm_match)

        if found_date:
            return self._normalize_date(found_date, found_time or "")
        return None

    def _search_time_nearby(
        self, texts: list[str], date_idx: int
    ) -> str | None:
        """날짜 줄 인접(전후 4줄)에서 시간 패턴 탐색"""
        search_range = list(range(
            max(0, date_idx - 2), min(len(texts), date_idx + 5)
        ))
        # 날짜 줄 자체는 제외 (이미 처리됨)
        if date_idx in search_range:
            search_range.remove(date_idx)

        for j in search_range:
            line = texts[j]

            # "시간: HH:MM" 패턴
            time_match = re.search(
                r"시간\s*[:：]\s*(\d{1,2}:\d{2})", line
            )
            if time_match:
                return time_match.group(1)

            # 한국어 오전/오후 시간
            ampm_match = re.search(
                r"시간\s*[:：]\s*(오전|오후)\s*(\d{1,2}):(\d{2})", line
            )
            if ampm_match:
                return self._parse_ampm_time(ampm_match)

            # 대괄호/꺽쇠 안의 시간: [16:47], <16:47>
            bracket_match = re.search(
                r"[\[<]\s*(\d{1,2}:\d{2})\s*[\]>]", line
            )
            if bracket_match:
                time_str = bracket_match.group(1)
                h, m = time_str.split(":")
                if 0 <= int(h) <= 23 and 0 <= int(m) <= 59:
                    return time_str

            # 독립된 시간 패턴 (HH:MM:SS 또는 HH:MM)
            standalone = re.match(
                r"^\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*$", line
            )
            if standalone:
                time_str = standalone.group(1)[:5]  # HH:MM만
                h, m = time_str.split(":")
                if 0 <= int(h) <= 23 and 0 <= int(m) <= 59:
                    return time_str

        return None

    def _parse_ampm_time(self, match) -> str:
        """오전/오후 시간 매치를 24시간제 문자열로 변환"""
        period = match.group(1)
        hour = int(match.group(2))
        minute = match.group(3)
        if period == "오후" and hour < 12:
            hour += 12
        elif period == "오전" and hour == 12:
            hour = 0
        return f"{hour}:{minute}"

    def _normalize_date(self, date_str: str, time_str: str = "") -> str:
        """날짜를 'YYYY-MM-DD HH:MM' 형식으로 정규화"""
        date_str = date_str.replace("/", "-").replace(".", "-")
        time_str = time_str.strip()

        # 시간에서 초 제거 (HH:MM:SS → HH:MM)
        if time_str and len(time_str) > 5:
            time_str = time_str[:5]

        if time_str:
            combined = f"{date_str} {time_str}"
        else:
            combined = date_str

        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%y-%m-%d %H:%M",
            "%y-%m-%d",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(combined.strip(), fmt)
                if dt.year < 100:
                    dt = dt.replace(year=dt.year + 2000)
                return dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                continue

        return combined.strip()

    def _parse_price(self, text: str) -> int | None:
        """가격 문자열 -> 정수 변환 (콤마/마침표 천단위, '원' 제거, 음수 지원)

        음수는 독립된 '-숫자' 패턴만 인식 (전화번호 02-201-0700 등 무시)
        """
        text = text.replace(" ", "")
        # 후행 T/A 등 세금 표시 제거
        text = re.sub(r"[TtAa]$", "", text)
        # 선행 # W 등 통화 기호 제거
        text = text.replace("#", "").replace("W", "").replace("\\", "")
        # 마침표가 천단위 구분자인 경우 처리 (예: 15.800 → 15800)
        text = re.sub(r"\.(\d{3})(?!\d)", r"\1", text)
        text = text.replace(",", "").replace("원", "")
        # 음수 가격: 문자열 시작 또는 비숫자 뒤에 오는 -숫자 패턴
        # 전화번호(02-201-0700)는 숫자-숫자-숫자 형태이므로 제외
        match = re.search(r"(?<!\d)-(\d+)$", text)
        if match:
            return -int(match.group(1))
        # 양수 가격: 가장 큰 숫자 그룹 추출
        match = re.search(r"(\d+)", text)
        if match:
            return int(match.group(1))
        return None

    def _collapse_spaces(self, text: str) -> str:
        """OCR이 글자 사이에 넣은 불필요한 공백 제거 (한글 단어 기준)"""
        # "부 가 세" -> "부가세", "소 계" -> "소계", "합 계" -> "합계"
        # 한글 한 글자 + 공백 + 한글 한 글자 패턴을 반복적으로 합침
        return re.sub(r"(?<=[\uac00-\ud7af])[\s'\"]+(?=[\uac00-\ud7af])", "", text)

    def _is_item_line(self, text: str) -> bool:
        """품목 줄인지 판별 (총액/메타 정보 줄 제외)"""
        collapsed = self._collapse_spaces(text)

        if any(kw in collapsed for kw in self.TOTAL_KEYWORDS):
            return False
        if any(kw in collapsed for kw in self.SKIP_KEYWORDS):
            return False
        # "N개" 형태만 있는 줄 (예: "6,000 1개 0 6,000") → 가격줄
        if re.match(r"^[\d,.\s]+\d+개", text.strip()):
            return False
        # 콜론으로 끝나는 줄은 레이블 (예: "카 드:", "공급가::")
        if re.search(r":+\s*$", text.strip()):
            return False
        # 승인/거래번호 (예: "인번호79875041")
        if re.search(r"번호\d", collapsed):
            return False
        # 결제 수단 (예: "스타벅스카드", "삼성카드")
        if re.search(r"카드$", collapsed):
            return False
        return True

    def _is_price_quantity_line(self, text: str) -> bool:
        """가격+수량 정보만 있는 줄인지 판별 (예: "6,000 1개 0 6,000")"""
        text = text.strip()
        # "가격 N개 할인 금액" 패턴
        if re.match(r"^[\d,.]+\s+\d+개\s", text):
            return True
        # "가격 N 금액" 패턴 (숫자로만 구성)
        if re.match(r"^[\d,.\s]+$", text):
            return True
        return False

    def _parse_quantity_price_line(
        self, text: str
    ) -> tuple[int, int, int] | None:
        """'가격 N개 할인 금액' 형태의 줄 파싱 → (단가, 수량, 금액)"""
        text = text.strip()

        # "6,000 1개 0 6,000" → unit=6000, count=1, total=6000
        match = re.match(
            r"([\d,.]+)\s+(\d+)개\s+([\d,.]+)\s+([\d,.]+)", text
        )
        if match:
            unit_price = self._parse_price(match.group(1))
            count = int(match.group(2))
            total = self._parse_price(match.group(4))
            if unit_price is not None and total is not None:
                return (unit_price, count, total)

        # "6,000 1개 6,000" → (할인 없는 형태)
        match = re.match(
            r"([\d,.]+)\s+(\d+)개\s+([\d,.]+)\s*$", text
        )
        if match:
            unit_price = self._parse_price(match.group(1))
            count = int(match.group(2))
            total = self._parse_price(match.group(3))
            if unit_price is not None and total is not None:
                return (unit_price, count, total)

        # "3,700 1 3,700" → unit=3700, count=1, price=3700 ("개" 없는 형태)
        match = re.match(
            r"([\d,.]+)\s+(\d+)\s+([\d,.]+)\s*$", text
        )
        if match:
            unit_price = self._parse_price(match.group(1))
            count = int(match.group(2))
            price = self._parse_price(match.group(3))
            if unit_price is not None and price is not None and count <= 50:
                return (unit_price, count, price)

        # "3,700 1" → unit=3700, count=1 ("개"도 총액도 없는 형태)
        match = re.match(
            r"([\d,.]+)\s+(\d+)\s*$", text
        )
        if match:
            unit_price = self._parse_price(match.group(1))
            count = int(match.group(2))
            if unit_price is not None and count <= 50:
                return (unit_price, count, unit_price * count)

        return None

    def _is_barcode_price_line(self, text: str) -> bool:
        """바코드 + 가격 형태의 줄인지 판별

        예: '8801104306928 2,000 5 10,000'
            '*8809074396277 1,300 2 2,600'
        """
        return bool(re.match(r"^\*?\d{8,}\s+[\d,]+", text))

    def _is_garbled_text(self, text: str) -> bool:
        """OCR 가비지 텍스트 판별 (의미 없는 문자 조합)"""
        cleaned = text.strip()
        if len(cleaned) < 2:
            return True
        # 한글 없이 기호+영문 1~2글자만 있는 경우
        korean_chars = re.findall(r"[\uac00-\ud7af]", cleaned)
        if not korean_chars and len(cleaned) <= 3:
            return True
        # 가격 부분 제거 후 이름만 추출
        name_part = re.sub(r"\s*-?[\d,.]+\s*$", "", cleaned)
        if not name_part:
            return False
        name_stripped = name_part.replace(" ", "")
        korean_in_name = re.findall(r"[\uac00-\ud7af]", name_part)
        # 한글 1글자 이하 + 전체 3글자 이하 → 가비지
        if len(name_stripped) <= 3 and len(korean_in_name) <= 1:
            return True
        # 퍼센트로 시작하는 세율 요약 줄 (예: "10% 14,326 143,274")
        if re.match(r"^\d+%\s", cleaned):
            return True
        # 특수문자 2개 이상 포함 (예: "마패패명* & 라이 Ⅱ")
        if len(re.findall(r"[*&°@#$%^{}|<>~\u2160-\u216F]", cleaned)) >= 2:
            return True
        # 주소 패턴 (예: "서울 강남구 선릉로 431")
        if re.search(r"[구군]\s+\S+[로길동]\s+\d", cleaned):
            return True
        # 한글이 고립되어 있는 경우 (연속 2글자 미만, 예: "J이J r0 액")
        if not re.search(r"[\uac00-\ud7af]{2,}", name_stripped):
            if not re.search(r"[a-zA-Z]{3,}", name_stripped):
                return True
        return False

    def _extract_items(self, texts: list[str]) -> list[dict]:
        """품목 리스트 추출

        지원 패턴:
            1) 품목명 수량 단가 금액   (예: 참이슬 2 1,800 3,600)
            2) 품목명 단가 X 수량      (예: 참이슬 1,800 X 2)
            3) 품목명 수량 금액         (예: 버터 1 3,120)
            4) 품목명 금액             (예: 삼각김밥 1,200 → count=1)
            5) 다중 라인: 품목명 줄 + 다음 줄에 (바코드) 가격 정보
            6) 다중 라인: 품목명 줄 + "가격 N개 할인 금액" 줄
            7) 할인 품목: 품목명 -금액  (예: >>할인 -3,100)
        """
        items = []
        item_id = 1
        pending_name = None  # 가격 없이 이름만 있는 줄 임시 저장
        past_total = False   # 합계/결제 섹션 경과 여부

        for idx, text in enumerate(texts):
            text = text.strip()
            if not text:
                continue

            # 합계/결제 섹션 이후 항목 추출 중단
            if not past_total and items:
                check_text = self._collapse_spaces(text)
                is_total_line = False
                if any(kw in check_text for kw in self.TOTAL_PRIORITY_KEYWORDS):
                    is_total_line = True
                elif any(kw in check_text for kw in self.TOTAL_KEYWORDS):
                    if not any(kw in check_text for kw in ["과세", "면세"]):
                        is_total_line = True
                # 단독 "계" + 가격 패턴 (예: "계 16,000")
                elif re.match(r"^\s*계\s+[\d,]+", check_text):
                    is_total_line = True
                if is_total_line:
                    past_total = True
            if past_total:
                pending_name = None
                continue

            # 바코드+가격 줄: 앞에 대기 중인 품목명이 있으면 연결
            if self._is_barcode_price_line(text):
                if pending_name is not None:
                    price_part = re.sub(r"^\*?\d{8,}\s+", "", text).strip()
                    parsed = self._parse_price_line(price_part)
                    if parsed:
                        unit_price, count, price = parsed
                        items.append({
                            "id": item_id,
                            "name": self._clean_item_name(pending_name),
                            "unit_price": unit_price,
                            "count": count,
                            "price": price,
                        })
                        item_id += 1
                    pending_name = None
                continue

            # "가격 N개 할인 금액" 줄: 앞에 대기 중인 품목명이 있으면 연결
            if pending_name is not None and self._is_price_quantity_line(text):
                parsed = self._parse_quantity_price_line(text)
                if parsed:
                    unit_price, count, price = parsed
                    items.append({
                        "id": item_id,
                        "name": self._clean_item_name(pending_name),
                        "unit_price": unit_price,
                        "count": count,
                        "price": price,
                    })
                    item_id += 1
                    pending_name = None
                    continue

            if not self._is_item_line(text):
                pending_name = None
                continue

            # 가비지 텍스트 필터링
            if self._is_garbled_text(text):
                pending_name = None
                continue

            # "+" 접두사 옵션/추가 라인 필터링 (0원 추가 옵션)
            if re.match(r"^\+", text):
                continue

            # 후행 T (세금 표시) 제거 후 패턴 매칭에 사용
            tc = re.sub(r"(\d)[Tt]\s*$", r"\1", text)
            # OCR이 콤마 뒤에 공백을 넣는 경우 보정: "6, 100" → "6,100"
            tc = re.sub(r"(\d),\s+(\d)", r"\1,\2", tc)

            # 패턴 D: 할인 줄 "할인 30% 30% -40,500 94,500"
            #   → 할인금액과 소계가 분리되어 있는 패턴
            discount_match = re.match(
                r"(.+?)\s+(-[\d,.]+)\s+([\d,.]+)\s*$", tc
            )
            if discount_match:
                name = discount_match.group(1).strip()
                neg_price = self._parse_price(discount_match.group(2))
                # 세 번째 그룹(소계)은 무시, 할인액만 사용
                if neg_price is not None and neg_price < 0:
                    pending_name = None
                    items.append({
                        "id": item_id,
                        "name": self._clean_item_name(name),
                        "unit_price": neg_price,
                        "count": 1,
                        "price": neg_price,
                    })
                    item_id += 1
                    continue

            # 패턴 1: 품목명 수량 단가 금액
            match = re.match(
                r"(.+?)\s+(\d+)\s+([\d,.]+)\s+([\d,.]+)\s*$", tc
            )
            if match:
                name = match.group(1).strip()
                count = int(match.group(2))
                unit_price = self._parse_price(match.group(3))
                price = self._parse_price(match.group(4))

                if unit_price and price and len(name) >= 1:
                    # 수량이 비정상적으로 크면 패턴 1 건너뛰기
                    if count <= 100:
                        pending_name = None
                        items.append({
                            "id": item_id,
                            "name": self._clean_item_name(name),
                            "unit_price": unit_price,
                            "count": count,
                            "price": price,
                        })
                        item_id += 1
                        continue

            # 패턴 2: 품목명 단가 X 수량 (금액)
            match = re.match(
                r"(.+?)\s+([\d,.]+)\s*[xX×]\s*(\d+)\s*([\d,.]*)s*$", tc
            )
            if match:
                name = match.group(1).strip()
                unit_price = self._parse_price(match.group(2))
                count = int(match.group(3))
                price_str = match.group(4).strip()
                price = self._parse_price(price_str) if price_str else None

                if unit_price and count:
                    if price is None:
                        price = unit_price * count
                    pending_name = None
                    items.append({
                        "id": item_id,
                        "name": self._clean_item_name(name),
                        "unit_price": unit_price,
                        "count": count,
                        "price": price,
                    })
                    item_id += 1
                    continue

            # 패턴 3: 품목명 수량 금액 (예: "버터 1 3,120")
            match = re.match(
                r"(.+?)\s+(\d+)\s+([\d,.]+)\s*$", tc
            )
            if match:
                name = match.group(1).strip()
                count = int(match.group(2))
                price = self._parse_price(match.group(3))

                if price is not None and count <= 50 and len(name) >= 1:
                    if not re.match(r"^[\d\s:/.,()\-*]+$", name):
                        pending_name = None
                        items.append({
                            "id": item_id,
                            "name": self._clean_item_name(name),
                            "unit_price": price // count if count > 0 and price != 0 else price,
                            "count": count,
                            "price": price,
                        })
                        item_id += 1
                        continue

            # 패턴 4: 품목명 금액 (수량 1개) — 음수 가격 포함
            match = re.match(r"(.+?)\s+(-?[\d,.]+)\s*$", tc)
            if match:
                name = match.group(1).strip()
                price = self._parse_price(match.group(2))

                if price is not None and len(name) >= 2:
                    if not re.match(r"^[\d\s:/.,()\-*]+$", name):
                        abs_price = abs(price)
                        if abs_price >= 100:
                            # 다음 줄이 바코드 줄이면 이 패턴 건너뛰기
                            # (바코드 줄에서 올바른 가격을 파싱할 수 있음)
                            next_idx = idx + 1
                            if next_idx < len(texts) and self._is_barcode_price_line(texts[next_idx].strip()):
                                pending_name = name
                                continue

                            pending_name = None
                            items.append({
                                "id": item_id,
                                "name": self._clean_item_name(name),
                                "unit_price": price,
                                "count": 1,
                                "price": price,
                            })
                            item_id += 1
                            continue

            # 가격 없이 품목명만 있는 줄 → 다음 줄에 가격이 올 수 있음
            if len(text) >= 2 and not re.match(r"^[\d\s:/.,()\-*]+$", text):
                # 번호 접두사 제거 (예: "001)", "01", "001 ")
                cleaned = re.sub(r"^\d{1,3}[)]\s*", "", text).strip()
                cleaned = re.sub(r"^\d{1,3}\s+", "", cleaned).strip()
                cleaned = re.sub(r"^\*\s*", "", cleaned).strip()
                if len(cleaned) >= 2:
                    pending_name = cleaned
                else:
                    pending_name = None
            else:
                pending_name = None

        # 레이블 이름 필터링 (콜론으로 끝나는 품목명, 예: "인 액:", "급가:")
        items = [item for item in items
                 if not re.search(r":+\s*$", item["name"])]
        # 0원 태그 필터링 (콜론이 포함된 0원 항목, 예: "초강추:오리지널")
        items = [item for item in items
                 if not (item["price"] == 0 and ":" in item["name"])]
        # 비정상 가격 필터링 (카드번호 등이 가격으로 인식된 경우)
        items = [item for item in items if abs(item["price"]) <= 10_000_000]
        for i, item in enumerate(items):
            item["id"] = i + 1
            if item["count"] < 1:
                item["count"] = 1
        return items

    def _parse_price_line(self, text: str) -> tuple[int, int, int] | None:
        """가격 줄 파싱 → (단가, 수량, 금액) 또는 None

        지원: '단가 수량 금액', '수량 금액', '금액' 등
        """
        text = text.strip()
        # 후행 'T' 등 제거 (세금 표시)
        text = re.sub(r"[TtA-Za-z]+\s*$", "", text).strip()

        # 단가 수량 금액
        match = re.match(r"([\d,.]+)\s+(\d+)\s+([\d,.]+)\s*$", text)
        if match:
            unit_price = self._parse_price(match.group(1))
            count = int(match.group(2))
            price = self._parse_price(match.group(3))
            if unit_price is not None and price is not None:
                return (unit_price, count, price)

        # 수량 금액 (예: "1 3,500")
        match = re.match(r"(\d+)\s+([\d,.]+)\s*$", text)
        if match:
            count = int(match.group(1))
            price = self._parse_price(match.group(2))
            if price is not None and count <= 50:
                unit_price = price // count if count > 0 else price
                return (unit_price, count, price)

        # 금액만
        match = re.match(r"([\d,.]+)\s*$", text)
        if match:
            price = self._parse_price(match.group(1))
            if price is not None:
                return (price, 1, price)

        return None

    def _clean_item_name(self, name: str) -> str:
        """품목명 정리 (특수 접두사 제거 등)"""
        # *표시, >>접두사, 선행 대시, 괄호 태그 등 제거
        name = re.sub(r"^[*\s]+", "", name)
        name = re.sub(r"^>{1,2}\s*", "", name)
        name = re.sub(r"^-\s*", "", name)
        name = re.sub(r"^\(면세\)\s*", "", name)
        name = re.sub(r"^\(과세\)\s*", "", name)
        # 품목명 뒤의 (과세), (면세) 태그 제거
        name = re.sub(r"\(과세\)\s*$", "", name)
        name = re.sub(r"\(면세\)\s*$", "", name)
        # 숫자 접두사 제거 (예: "01 ", "02 ")
        name = re.sub(r"^\d{1,3}\s+", "", name)
        # 품목명 뒤에 붙은 가격 패턴 제거 (예: "얼큰칼국수 10,000", "왕만루반반 6,000 -")
        name = re.sub(r"\s+\d{1,3}(,\d{3})+\s*-?\s*$", "", name)
        # 끝의 OCR 잔류 괄호 제거 (예: "사이다335m]" → "사이다335m")
        name = re.sub(r"[\[\]]$", "", name)
        return name.strip()

    # 총액 키워드 우선순위 (높은 순)
    TOTAL_PRIORITY_KEYWORDS = [
        "카드결제", "결제금액", "총결제", "총결제금액",
    ]

    def _extract_total(self, texts: list[str]) -> int | None:
        """총액 추출 (합계/결제금액 키워드 기반)

        우선순위:
        1) '카드결제', '결제금액' 등 최종 결제 키워드
        2) '합계', '총합' 등 일반 합계 키워드
        """
        MAX_TOTAL = 10_000_000  # 총액 상한 (카드번호 오인식 방지)

        # 1단계: 최종 결제 키워드로 탐색 (가장 정확)
        for i, text in enumerate(texts):
            collapsed = self._collapse_spaces(text)
            if any(kw in collapsed for kw in self.TOTAL_PRIORITY_KEYWORDS):
                price = self._extract_price_from_context(texts, i)
                if price is not None and 100 <= abs(price) <= MAX_TOTAL:
                    return price

        # 2단계: 일반 합계 키워드로 탐색
        for i, text in enumerate(texts):
            collapsed = self._collapse_spaces(text)
            if any(kw in collapsed for kw in self.TOTAL_KEYWORDS):
                # 세금 소계 건너뛰기 ("과세 합계", "면세 합계" 등)
                if any(kw in collapsed for kw in ["과세", "면세"]):
                    continue
                price = self._extract_price_from_context(texts, i)
                if price is not None and 100 <= abs(price) <= MAX_TOTAL:
                    return price

        # 3단계: "계 = 금액" 특수 패턴 (예: 공차 스타일 "계 = 12,000")
        for text in texts:
            collapsed = self._collapse_spaces(text)
            m = re.match(r"^\s*계\s*=\s*([\d,]+)", collapsed)
            if m:
                price = self._parse_price(m.group(1))
                if price is not None and 100 <= price <= MAX_TOTAL:
                    return price

        return None

    def _extract_price_from_context(
        self, texts: list[str], idx: int
    ) -> int | None:
        """해당 줄 또는 인접 줄에서 가격 추출"""
        # 같은 줄에서 추출
        price = self._parse_price(texts[idx])
        if price is not None and abs(price) >= 100:
            return price

        # 다음 줄에서 추출
        if idx + 1 < len(texts):
            price = self._parse_price(texts[idx + 1])
            if price is not None and abs(price) >= 100:
                return price

        return None
