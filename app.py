import os
from dotenv import load_dotenv
from db import get_todays_products, init_db, get_posted_product_ids, mark_as_posted
from ai import generate_social_content
from social import SocialPoster

# Load environment variables
load_dotenv()

def main():
    print("🚀 Starting Shopee AI Poster...")
    # Initialize DB (create tables if needed)
    init_db()
    
    # 1. Fetch data from Neon DB
    print("📥 Fetching today's top products from database...")
    all_products = get_todays_products(limit=50)
    
    if not all_products:
        print("❌ No products found for today. Make sure the scraper has run.")
        return
        
    print(f"✅ Found {len(all_products)} products.")
    
    # Check memory for already posted products
    posted_ids = get_posted_product_ids()
    products = [p for p in all_products if str(p['product_id']) not in posted_ids]
    
    if not products:
        print("✅ All high-commission products today have already been posted. Nothing to do!")
        return
        
    print(f"✅ Found {len(products)} unposted products. Proceeding to AI analysis.")
    
    # 2. Ask Gemini AI to analyze and generate content
    print("🧠 Sending data to Gemini AI for analysis...")
    ai_result = generate_social_content(products)
    
    if not ai_result:
        print("❌ Failed to get a response from AI.")
        return
        
    print(f"🎯 AI Selected Product ID: {ai_result.get('selected_product_id')}")
    print(f"💡 AI Reason: {ai_result.get('reason')}")
    print("📝 AI Captions Generated: [FB, Twitter, LINE]")
    
    # Find the actual product object to get the real link and image
    selected_prod = next((p for p in products if str(p['product_id']) == str(ai_result.get('selected_product_id'))), None)
    
    if not selected_prod:
        # Fallback if AI hallucinates an ID, just pick the first one
        print("⚠️ AI selected an ID that doesn't exist. Falling back to the highest commission product.")
        selected_prod = products[0]
        
    from publisher import BlogPublisher
    
    # 3. Publish to Blog First
    print("📝 Publishing article to review.bizxthai.com...")
    publisher = BlogPublisher()
    blog_url = publisher.publish_single_post(
        title=ai_result.get("blog_title"),
        content=ai_result.get("blog_content"),
        excerpt=ai_result.get("blog_excerpt"),
        image_url=selected_prod['image_url'],
        affiliate_link=selected_prod['aff_link']
    )
    
    if not blog_url:
        print("⚠️ Failed to publish blog. Falling back to direct affiliate link for social.")
        social_link = selected_prod['aff_link']
    else:
        print(f"✅ Blog published! URL: {blog_url}")
        social_link = blog_url
        
    # 4. Post to Social Media
    print("📢 Broadcasting to Social Media...")
    poster = SocialPoster()
    results = poster.post_all(
        ai_result=ai_result, 
        image_url=selected_prod['image_url'], 
        link=social_link
    )
    
    print("✅ Finished!")
    print("Results:", results)
    
    # If at least one platform succeeded (or if you want to consider any attempt as done)
    if 'Success' in results.values():
        print(f"📝 Saving product {selected_prod['product_id']} to memory to prevent duplicate posts.")
        mark_as_posted(str(selected_prod['product_id']))
    else:
        print("⚠️ All posts failed. Product memory not updated so we can retry later.")

if __name__ == "__main__":
    main()
