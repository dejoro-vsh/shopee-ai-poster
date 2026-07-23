import os
from datetime import datetime
from dotenv import load_dotenv
from db import get_todays_products, init_db, get_posted_product_ids, mark_as_posted
from ai import generate_social_content, generate_trend_content
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
        
    print(f"✅ Found {len(products)} unposted products.")
    
    current_hour = datetime.now().hour
    # Strategy: 
    # 10:00 - 16:59 -> Knowledge/Tips/Trends
    # Other times -> Normal Product Review
    is_knowledge_time = 10 <= current_hour < 17
    
    if is_knowledge_time:
        print(f"⏰ Current hour is {current_hour}. Proceeding to AI KNOWLEDGE/TREND analysis.")
        ai_result = generate_trend_content(products)
    else:
        print(f"⏰ Current hour is {current_hour}. Proceeding to AI PRODUCT REVIEW analysis.")
        ai_result = generate_social_content(products)
    
    if not ai_result:
        print("❌ Failed to get a response from AI.")
        return
        
    if is_knowledge_time:
        print(f"🎯 AI Generated Trend Article: {ai_result.get('blog_title')}")
        selected_prod = None
    else:
        print(f"🎯 AI Selected Product ID: {ai_result.get('selected_product_id')}")
        print(f"💡 AI Reason: {ai_result.get('reason')}")
        selected_prod = next((p for p in products if str(p['product_id']) == str(ai_result.get('selected_product_id'))), None)
        if not selected_prod:
            print("⚠️ AI selected an ID that doesn't exist. Falling back to the highest commission product.")
            selected_prod = products[0]
            
    print("📝 AI Captions Generated: [FB, Twitter, LINE]")
    
    from publisher import BlogPublisher
    
    # 3. Publish to Blog First
    print("📝 Publishing article to review.bizxthai.com...")
    publisher = BlogPublisher()
    
    import re
    if is_knowledge_time:
        fallback_slug = "trend-" + datetime.now().strftime("%Y%m%d%H%M")
    else:
        fallback_slug = "review-" + re.sub(r'[^a-zA-Z0-9]', '-', str(selected_prod['item_name'])).lower()[:30]
    
    final_slug = ai_result.get("blog_slug")
    if not final_slug:
        final_slug = fallback_slug
        
    if is_knowledge_time:
        final_title = ai_result.get("blog_title")
        final_content = ai_result.get("blog_content")
        # Ensure we pass an empty affiliate link for trends
        blog_url = publisher.publish_single_post(
            slug=final_slug,
            category=ai_result.get("category", "อื่นๆ"),
            title=final_title,
            content=final_content,
            excerpt=ai_result.get("blog_excerpt", ""),
            image_url="https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80",
            affiliate_link=""
        )
        social_image = "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80"
    else:
        final_title = ai_result.get("blog_title") or selected_prod['item_name']
        final_content = ai_result.get("blog_content") or f"<p>รีวิวสินค้า {selected_prod['item_name']}</p>"
        
        blog_url = publisher.publish_single_post(
            slug=final_slug,
            category=ai_result.get("category", "อื่นๆ"),
            title=final_title,
            content=final_content,
            excerpt=ai_result.get("blog_excerpt", ""),
            image_url=selected_prod['image_url'],
            affiliate_link=selected_prod['aff_link']
        )
        social_image = selected_prod['image_url']
    
    if not blog_url:
        print("⚠️ Failed to publish blog.")
        if not is_knowledge_time:
            print("Falling back to direct affiliate link for social.")
            social_link = selected_prod['aff_link']
        else:
            social_link = "https://review.bizxthai.com"
    else:
        print(f"✅ Blog published! URL: {blog_url}")
        social_link = blog_url
        
    # 4. Post to Social Media
    print("📢 Broadcasting to Social Media...")
    poster = SocialPoster()
    results = poster.post_all(
        ai_result=ai_result, 
        image_url=social_image, 
        link=social_link
    )
    
    print("✅ Finished!")
    print("Results:", results)
    
    # If at least one platform succeeded
    if 'Success' in results.values():
        if not is_knowledge_time and selected_prod:
            print(f"📝 Saving product {selected_prod['product_id']} to memory to prevent duplicate posts.")
            mark_as_posted(str(selected_prod['product_id']))
        else:
            print("📝 Knowledge trend post completed successfully.")
    else:
        print("⚠️ All posts failed.")

if __name__ == "__main__":
    main()
