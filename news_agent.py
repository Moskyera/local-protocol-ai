from tavily import TavilyClient
from config import config

client = TavilyClient(api_key=config.TAVILY_API_KEY)

def get_market_news(query: str):
    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=5
        )
        return response["results"]
    except Exception as e:
        print(f"❌ Tavily error: {e}")
        return []