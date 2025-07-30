# Google Serper Web Search Tool 래퍼
import requests
import os


class WebSearchTool:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GOOGLE_SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"

    def search(self, query):
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": query}
        resp = requests.post(self.base_url, headers=headers, json=payload)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": resp.text}


# 사용 예시:
# tool = WebSearchTool()
# tool.search('삼성전자 주가')
