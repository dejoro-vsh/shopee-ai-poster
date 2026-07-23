import requests

VERCEL_API_URL = "https://shopee-scraper-vercel.vercel.app/api/blog"

class BlogPublisher:
    def __init__(self):
        self.api_url = VERCEL_API_URL

    def publish_single_post(self, slug, category, title, content, excerpt, image_url, affiliate_link):
        payload = {
            "slug": slug,
            "category": category,
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "image_url": image_url,
            "affiliate_link": affiliate_link,
            "type": "single"
        }
        
        print("DEBUG PAYLOAD:")
        print(payload)
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            if response.status_code == 201:
                data = response.json()
                return data.get("url")
            else:
                print(f"❌ Failed to publish blog. Status code: {response.status_code}")
                print(response.text)
                return None
        except Exception as e:
            print(f"❌ Error publishing blog: {e}")
            return None

    def publish_trend_post(self, title, content, excerpt):
        payload = {
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "image_url": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80",
            "affiliate_link": "",
            "type": "trend"
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            if response.status_code == 201:
                data = response.json()
                return data.get("url")
            else:
                print(f"❌ Failed to publish trend blog. Status code: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error publishing trend blog: {e}")
            return None
