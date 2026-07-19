import os
import requests

class SocialPoster:
    def __init__(self):
        # API Keys loaded from .env
        self.fb_page_id = os.getenv("FB_PAGE_ID")
        self.fb_access_token = os.getenv("FB_ACCESS_TOKEN")
        
        self.line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        
        # Twitter / TikTok / IG variables can go here
        
    def post_all(self, caption, image_url, link):
        """Helper to post to all configured platforms"""
        final_text = caption.replace("[LINK]", link)
        
        results = {}
        if self.fb_page_id and self.fb_access_token:
            results['facebook'] = self.post_to_facebook(final_text, image_url)
        else:
            results['facebook'] = "Skipped (Missing API Key)"
            
        if self.line_channel_access_token:
            results['line'] = self.post_to_line(final_text, image_url)
        else:
            results['line'] = "Skipped (Missing API Key)"
            
        # Add others here
        return results

    def post_to_facebook(self, message, image_url=None):
        """Posts to a Facebook Page using Graph API"""
        print("Posting to Facebook...")
        if image_url:
            url = f"https://graph.facebook.com/v19.0/{self.fb_page_id}/photos"
            payload = {
                "url": image_url,
                "caption": message,
                "access_token": self.fb_access_token
            }
        else:
            url = f"https://graph.facebook.com/v19.0/{self.fb_page_id}/feed"
            payload = {
                "message": message,
                "access_token": self.fb_access_token
            }
            
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            return f"Success: {response.json().get('id')}"
        except Exception as e:
            print("Facebook Post Error:", e)
            if hasattr(e, 'response') and e.response:
                print(e.response.text)
            return "Failed"

    def post_to_line(self, message, image_url=None):
        """Broadcasts a message to LINE Official Account"""
        print("Posting to LINE...")
        url = "https://api.line.me/v2/bot/message/broadcast"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.line_channel_access_token}"
        }
        
        messages = []
        if image_url:
            messages.append({
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url
            })
            
        messages.append({
            "type": "text",
            "text": message
        })
        
        payload = {"messages": messages}
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return "Success"
        except Exception as e:
            print("LINE Post Error:", e)
            return "Failed"
            
    # Stub for future implementations
    def post_to_twitter(self, message, image_url=None):
        pass
        
    def post_to_instagram(self, message, image_url=None):
        # Requires Facebook Graph API (Instagram Business account)
        pass
        
    def post_to_tiktok(self, message, video_url=None):
        # TikTok usually requires video, very strict API
        pass
