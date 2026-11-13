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
        
    def _normalize_image_url(self, url):
        """แปลง CDN Shopee ให้เป็น Tencent CDN (down-th.img.susercontent.com) เพื่อความเร็วและไม่โดนบล็อก"""
        if not url:
            return None
        # เปลี่ยน cf.shopee.co.th เป็น down-th.img.susercontent.com ที่โหลดเร็วกว่าและเสถียร 100%
        return url.replace("cf.shopee.co.th/file/", "down-th.img.susercontent.com/file/")

    def post_all(self, ai_result, image_url, link):
        """Helper to post to all configured platforms using specific captions"""
        cap_fb = ai_result.get('caption_facebook', '').replace("[LINK]", link)
        cap_tw = ai_result.get('caption_twitter', '').replace("[LINK]", link)
        cap_line = ai_result.get('caption_line', '').replace("[LINK]", link)
        
        results = {}
        if self.fb_page_id and self.fb_access_token and cap_fb:
            results['facebook'] = self.post_to_facebook(cap_fb, image_url=image_url, link=link)
        else:
            results['facebook'] = "Skipped (Missing API Key or Caption)"
            
        if self.line_channel_access_token and cap_line:
            results['line'] = self.post_to_line(cap_line, image_url=image_url)
        else:
            results['line'] = "Skipped (Missing API Key or Caption)"
            
        if self.twitter_api_key and self.twitter_access_token and cap_tw:
            results['twitter'] = self.post_to_twitter(cap_tw, image_url=image_url)
        else:
            results['twitter'] = "Skipped (Missing API Key or Caption)"
            
        return results

    def post_to_facebook(self, message, image_url=None, link=None):
        """Posts to a Facebook Page using Graph API with automatic Feed Link Fallback"""
        print("Posting to Facebook...")
        clean_img_url = self._normalize_image_url(image_url)
        
        # 1. พยายามดาวน์โหลดรูปและโพสต์แบบ Photo
        if clean_img_url:
            temp_img_path = "temp_fb_image.jpg"
            image_downloaded = False
            
            try:
                print(f"  -> Downloading image from fast CDN: {clean_img_url[:60]}...")
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://shopee.co.th/"
                }
                img_response = requests.get(clean_img_url, headers=headers, stream=True, timeout=12)
                img_response.raise_for_status()
                
                with open(temp_img_path, 'wb') as f:
                    for chunk in img_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                image_downloaded = True
                
            except Exception as e:
                print(f"  ⚠️ ไม่สามารถโหลดรูปภาพ Shopee ได้ ({e}) -> กำลังสลับไปโพสต์แบบ Feed Link อัตโนมัติ...")

            if image_downloaded and os.path.exists(temp_img_path):
                try:
                    print(f"  -> Uploading image to Facebook Page...")
                    photo_url = f"https://graph.facebook.com/v21.0/{self.fb_page_id}/photos"
                    with open(temp_img_path, 'rb') as img_file:
                        payload = {
                            "caption": message,
                            "access_token": self.fb_access_token
                        }
                        files = {
                            "source": ("image.jpg", img_file, "image/jpeg")
                        }
                        response = requests.post(photo_url, data=payload, files=files, timeout=25)
                    
                    if os.path.exists(temp_img_path):
                        os.remove(temp_img_path)
                        
                    response.raise_for_status()
                    post_id = response.json().get('id')
                    print(f"  ✅ Facebook Photo Post Success! ID: {post_id}")
                    return f"Success: {post_id}"
                except Exception as e:
                    if os.path.exists(temp_img_path):
                        os.remove(temp_img_path)
                    print("  ⚠️ Facebook Photo Upload Error:", e)
                    if hasattr(e, 'response') and e.response is not None:
                        try: print("  FB Error Details:", e.response.json())
                        except: print("  FB Error Details:", e.response.text)
                    print("  -> สลับไปใช้วิธีสำรอง: โพสต์แบบ Feed Link...")

        # 2. Fallback: โพสต์เข้า Page Feed ตรงๆ (Facebook จะดึง Rich Preview Card อัตโนมัติจากเว็บบล็อก)
        try:
            print("  -> Posting directly to Facebook Page Feed...")
            feed_url = f"https://graph.facebook.com/v21.0/{self.fb_page_id}/feed"
            payload = {
                "message": message,
                "access_token": self.fb_access_token
            }
            if link:
                payload["link"] = link
                
            response = requests.post(feed_url, data=payload, timeout=20)
            response.raise_for_status()
            post_id = response.json().get('id')
            print(f"  ✅ Facebook Feed Post Success! ID: {post_id}")
            return f"Success: {post_id}"
        except Exception as e:
            print("❌ Facebook Feed Post Error:", e)
            if hasattr(e, 'response') and e.response is not None:
                try: print("FB Error Details:", e.response.json())
                except: print("FB Error Details:", e.response.text)
            return "Failed"

    def post_to_line(self, message, image_url=None):
        """Broadcasts a message to LINE Official Account with text fallback"""
        print("Posting to LINE...")
        url = "https://api.line.me/v2/bot/message/broadcast"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.line_channel_access_token}"
        }
        
        clean_img_url = self._normalize_image_url(image_url)
        messages = []
        if clean_img_url:
            messages.append({
                "type": "image",
                "originalContentUrl": clean_img_url,
                "previewImageUrl": clean_img_url
            })
            
        messages.append({
            "type": "text",
            "text": message
        })
        
        payload = {"messages": messages}
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            print("  ✅ LINE Broadcast Success!")
            return "Success"
        except Exception as e:
            print("⚠️ LINE Post with image error:", e)
            if hasattr(e, 'response') and e.response is not None:
                try: print("LINE Error Details:", e.response.json())
                except: print("LINE Error Details:", e.response.text)
                
            # Fallback text only if image failed validation
            if clean_img_url:
                try:
                    print("  -> Retrying LINE with text-only message...")
                    fallback_payload = {"messages": [{"type": "text", "text": message}]}
                    res = requests.post(url, headers=headers, json=fallback_payload, timeout=15)
                    res.raise_for_status()
                    print("  ✅ LINE Text Broadcast Success!")
                    return "Success (Text only)"
                except Exception as e2:
                    print("❌ LINE Text Fallback Error:", e2)
                    
            return "Failed"
            
    def post_to_twitter(self, message, image_url=None):
        """Posts to Twitter using Tweepy API v2 (Free Tier)"""
        print("Posting to Twitter...")
        try:
            client = tweepy.Client(
                consumer_key=self.twitter_api_key,
                consumer_secret=self.twitter_api_secret,
                access_token=self.twitter_access_token,
                access_token_secret=self.twitter_access_token_secret
            )
            response = client.create_tweet(text=message)
            tweet_id = response.data['id']
            print(f"  ✅ Twitter Post Success! ID: {tweet_id}")
            return f"Success: {tweet_id}"
            
        except Exception as e:
            print("❌ Twitter Post Error:", e)
            return "Failed"
