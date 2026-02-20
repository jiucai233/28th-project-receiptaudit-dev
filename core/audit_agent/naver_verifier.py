import requests
import re

class NaverStoreVerifier:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://openapi.naver.com/v1/search/local.json"

    def clean_html(self, text):
        # 네이버 검색 결과에 섞인 <b> 태그 등을 제거
        return re.sub('<.+?>', '', text)

    def get_store_category(self, store_name):
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        params = {
            "query": store_name,
            "display": 5,  # 가장 정확한 1개만 가져오기
            "sort": "sim" # 유사도순 정렬
        }

        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['items']:
                    item = data['items'][0]
                    category = self.clean_html(item['category']) # 예: "한식 > 육류,고기요리"
                    title = self.clean_html(item['title'])
                    return {
                        "store_name": title,
                        "category_full": category,
                        "category_main": category.split(">")[0].strip(),
                        "category_sub": category.split(">")[-1].strip(),
                        "source": "naver_local_api"
                    }
                else:
                    return "네이버 지도 검색 결과 없음 (폐업 또는 등록되지 않음)"
            else:
                return f"API 호출 오류: {response.status_code}"
        except Exception as e:
            return f"검색 중 에러 발생: {str(e)}"