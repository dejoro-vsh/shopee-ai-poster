import os
import requests
import tweepy
class SocialPoster:
    def __init__(self):
        # API Keys loaded from .env
        self.fb_page_id = os.getenv("FB_PAGE_ID")
        self.fb_access_token = os.getenv("FB_ACCESS_TOKEN")
        
        self.line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        
        # Twitter API Keys loaded from .env
        self.twitter_api_key = os.getenv("TWITTER_API_KEY")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.twitter_access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        
    def post_all(self, ai_result, image_url, link):
        """Helper to post to all configured platforms using specific captions"""
        cap_fb = ai_result.get('caption_facebook', '').replace("[LINK]", link)
        cap_tw = ai_result.get('caption_twitter', '').replace("[LINK]", link)
        cap_line = ai_result.get('caption_line', '').replace("[LINK]", link)
        
        results = {}
        if self.fb_page_id and self.fb_access_token and cap_fb:
            results['facebook'] = self.post_to_facebook(cap_fb, image_url)
        else:
            results['facebook'] = "Skipped (Missing API Key)"
            
        if self.line_channel_access_token and cap_line:
            results['line'] = self.post_to_line(cap_line, image_url)
        else:
            results['line'] = "Skipped (Missing API Key or Caption)"
            
        if self.twitter_api_key and self.twitter_access_token and cap_tw:
            results['twitter'] = self.post_to_twitter(cap_tw, image_url)
        else:
            results['twitter'] = "Skipped (Missing API Key or Caption)"
            
        return results

    def post_to_facebook(self, message, image_url=None):
        """Posts to a Facebook Page using Graph API"""
        print("Posting to Facebook...")
        if image_url:
            # Removed hardcoded v25.0 version to avoid version mismatch errors
            url = f"https://graph.facebook.com/{self.fb_page_id}/photos"
            
            # WORKAROUND: Facebook Graph API cannot download images from Shopee's CDN directly.
            # We must download it locally first, then upload it as multipart/form-data.
            try:
                print(f"  -> Downloading image locally from Shopee...")
                img_response = requests.get(image_url, stream=True)
                img_response.raise_for_status()
                
                temp_img_path = "temp_fb_image.jpg"
                with open(temp_img_path, 'wb') as f:
                    for chunk in img_response.iter_content(1024):
                        f.write(chunk)
                
                print(f"  -> Uploading image to Facebook...")
                with open(temp_img_path, 'rb') as img_file:
                    payload = {
                        "caption": message,
                        "access_token": self.fb_access_token
                    }
                    files = {
                        # Explicitly specify filename and mimetype for requests
                        "source": ("image.jpg", img_file, "image/jpeg")
                    }
                    response = requests.post(url, data=payload, files=files)
                
                # Clean up temp file
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
                    
                response.raise_for_status()
                return f"Success: {response.json().get('id')}"
                
            except Exception as e:
                print("Facebook Post Error:", e)
                # Fix response truthiness check (requests response is falsy if status >= 400)
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        print("FB Error Details:", e.response.json())
                    except:
                        print("FB Error Details:", e.response.text)
                return "Failed"
        else:
            url = f"https://graph.facebook.com/{self.fb_page_id}/feed"
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
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        print("FB Error Details:", e.response.json())
                    except:
                        print("FB Error Details:", e.response.text)
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
            
    def post_to_twitter(self, message, image_url=None):
        """Posts to Twitter using Tweepy API v2 (Free Tier)"""
        print("Posting to Twitter...")
        try:
            # V2 authentication for tweeting
            client = tweepy.Client(
                consumer_key=self.twitter_api_key,
                consumer_secret=self.twitter_api_secret,
                access_token=self.twitter_access_token,
                access_token_secret=self.twitter_access_token_secret
            )
            
            # We skip image_upload (v1.1) because X now charges 402 Payment Required for it.
            # Twitter will automatically pull the product image from the Shopee Link (Twitter Card)!
            response = client.create_tweet(text=message)
                
            return f"Success: {response.data['id']}"
            
        except Exception as e:
            print("Twitter Post Error:", e)
            return "Failed"
        
    def post_to_instagram(self, message, image_url=None):
        # Requires Facebook Graph API (Instagram Business account)
        pass
        
    def post_to_tiktok(self, message, video_url=None):
        # TikTok usually requires video, very strict API
        pass
