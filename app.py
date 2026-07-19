import os
from dotenv import load_dotenv
from db import get_todays_products
from ai import generate_social_content
from social import SocialPoster

# Load environment variables
load_dotenv()

def main():
    print("🚀 Starting Shopee AI Poster...")
    
    # 1. Fetch data from Neon DB
    print("📥 Fetching today's top products from database...")
    products = get_todays_products(limit=50)
    
    if not products:
        print("❌ No products found for today. Make sure the scraper has run.")
        return
        
    print(f"✅ Found {len(products)} products.")
    
    # 2. Ask Gemini AI to analyze and generate content
    print("🧠 Sending data to Gemini AI for analysis...")
    ai_result = generate_social_content(products)
    
    if not ai_result:
        print("❌ Failed to get a response from AI.")
        return
        
    print(f"🎯 AI Selected Product ID: {ai_result.get('selected_product_id')}")
    print(f"💡 AI Reason: {ai_result.get('reason')}")
    print(f"📝 AI Caption: \n{ai_result.get('caption')}")
    
    # Find the actual product object to get the real link and image
    selected_prod = next((p for p in products if str(p['product_id']) == str(ai_result.get('selected_product_id'))), None)
    
    if not selected_prod:
        # Fallback if AI hallucinates an ID, just pick the first one
        print("⚠️ AI selected an ID that doesn't exist. Falling back to the highest commission product.")
        selected_prod = products[0]
        
    # 3. Post to Social Media
    print("📢 Broadcasting to Social Media...")
    poster = SocialPoster()
    results = poster.post_all(
        caption=ai_result.get('caption'), 
        image_url=selected_prod['image_url'], 
        link=selected_prod['aff_link']
    )
    
    print("✅ Finished!")
    print("Results:", results)

if __name__ == "__main__":
    main()
