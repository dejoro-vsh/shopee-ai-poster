import os
from datetime import datetime
from dotenv import load_dotenv
from db import get_todays_products, init_db, get_posted_product_ids, mark_as_posted, get_recently_used_images
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
    
    # Check memory for already posted products and used images
    posted_ids = get_posted_product_ids()
    recently_used_images = get_recently_used_images(limit=100)
    
    # 1. Pre-filter: Only unposted products with a valid image URL that haven't been recently posted
    fresh_products = [
        p for p in all_products 
        if str(p['product_id']) not in posted_ids 
        and p.get('image_url') and p['image_url'].strip() 
        and p['image_url'].strip() not in recently_used_images
    ]
    
    # If all unposted products have recently used images, relax image filter to avoid starving
    if not fresh_products:
        print("⚠️ All unposted products have recently used images. Relaxing image deduplication filter.")
        fresh_products = [
            p for p in all_products 
            if str(p['product_id']) not in posted_ids 
            and p.get('image_url') and p['image_url'].strip()
        ]
        
    products = fresh_products
    
    if not products:
        print("✅ All high-commission products today have already been posted. Nothing to do!")
        return
        
    print(f"✅ Found {len(products)} valid, unposted products ready for AI.")
    
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
        selected_id = str(ai_result.get('selected_product_id', '')).strip()
        print(f"🎯 AI Selected Product ID: {selected_id}")
        print(f"💡 AI Reason: {ai_result.get('reason')}")
        
        # Match product by exact ID
        selected_prod = next((p for p in products if str(p['product_id']) == selected_id), None)
        
        # If ID not found, attempt fuzzy match by item_name in AI blog_title
        if not selected_prod:
            blog_title = ai_result.get('blog_title', '')
            for p in products:
                name_clean = p['item_name'][:20]
                if name_clean in blog_title or p['item_name'] in blog_title:
                    selected_prod = p
                    print(f"🔍 Matched product by title: {p['item_name'][:40]} (ID: {p['product_id']})")
                    break
                    
        # Fallback to first available fresh product if AI gave invalid ID
        if not selected_prod:
            print("⚠️ AI selected an ID that doesn't exist. Falling back to first available product.")
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
        category = ai_result.get("category", "อื่นๆ")
        
        # สำหรับบทความเทรนด์: ใช้ภาพ AI Lifestyle Banner ความละเอียดสูงตามหมวดหมู่เสมอ
        # ป้องกันไม่ให้เอารูปสินค้าเฉพาะเจาะจงมาใส่เป็นปกบทความภาพรวม/เทรนด์
        import random
        import urllib.parse
        keywords_by_category = {
            "ไอที & แกดเจ็ต": "modern minimalist workspace tech gadgets setup",
            "เครื่องใช้ในบ้าน": "cozy modern home interior living room appliances",
            "สุขภาพ & ความงาม": "natural organic skincare wellness spa beauty products flatlay",
            "กีฬา & ไลฟ์สไตล์": "active lifestyle fitness gym outdoor workout gear",
            "อื่นๆ": "trendy modern lifestyle shopping consumer products flatlay"
        }
        kw = keywords_by_category.get(category, "trendy modern lifestyle shopping products")
        seed = random.randint(10000, 999999)
        encoded_kw = urllib.parse.quote(f"{kw}, aesthetic photography, highly detailed, 8k resolution, soft natural lighting")
        trend_image = f"https://image.pollinations.ai/prompt/{encoded_kw}?width=1200&height=800&seed={seed}"
        selected_prod = None
        print(f"🎨 สร้างภาพหน้าปก AI คุณภาพสูงเฉพาะบทความเทรนด์: หมวดหมู่ {category} (Seed: {seed})")
        
        # Ensure we pass an empty affiliate link for trends
        blog_url = publisher.publish_single_post(
            slug=final_slug,
            category=category,
            title=final_title,
            content=final_content,
            excerpt=ai_result.get("blog_excerpt", ""),
            image_url=trend_image,
            affiliate_link=""
        )
        social_image = trend_image
    else:
        # กรณีรีวิวสินค้าเดี่ยว: ใช้รูปภาพและลิงก์ของสินค้าที่เลือก 100% ไม่มีการสลับสินค้าหลัง AI สร้างเนื้อหา
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
    is_any_success = 'Success' in results.values() or any('Success' in str(v) for v in results.values())
    if is_any_success:
        if selected_prod:
            print(f"📝 Saving product {selected_prod['product_id']} to memory to prevent duplicate posts.")
            mark_as_posted(str(selected_prod['product_id']))
        else:
            print("📝 Knowledge trend post completed successfully.")
    else:
        print("⚠️ All posts failed.")

if __name__ == "__main__":
    main()
