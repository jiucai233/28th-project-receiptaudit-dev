import requests
import re

class NaverStoreVerifier:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://openapi.naver.com/v1/search/local.json"

    def clean_html(self, text):
        return re.sub('<.+?>', '', text)

    def get_store_category(self, store_name, address=None):
        if not self.client_id or not self.client_secret:
            return {"error": "API 키 누락"}
            
        region_name = address.split()[0] if address else ""
        query = f"{region_name} {store_name}".strip()
            
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        params = {"query": query, "display": 1, "sort": "sim"}

        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['items']:
                    item = data['items'][0]
                    category = self.clean_html(item['category']) # 예: "음식점>주점>호프/요리주점"
                    title = self.clean_html(item['title'])
                    
                    return {
                        "store_name": title,
                        "category_full": category,
                        "category_main": category.split(">")[0].strip() if ">" in category else category,
                        "source": "naver_local_api"
                    }
                else:
                    return {"error": "검색 결과 없음"}
            else:
                return {"error": f"API 호출 오류: {response.status_code}"}
        except Exception as e:
            return {"error": f"검색 중 에러 발생: {str(e)}"}