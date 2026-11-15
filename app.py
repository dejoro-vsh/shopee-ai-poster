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
        
    recently_used_images = get_recently_used_images(limit=100)
    
    if is_knowledge_time:
        final_title = ai_result.get("blog_title")
        final_content = ai_result.get("blog_content")
        category = ai_result.get("category", "อื่นๆ")
        
        # 1. พยายามเลือกสินค้าที่ตรงกับที่ AI แนะนำ หรือสุ่มจากสินค้าที่ยังไม่เคยใช้รูป
        chosen_prod = None
        cover_id = ai_result.get("cover_product_id")
        if cover_id:
            chosen_prod = next((p for p in products if str(p['product_id']) == str(cover_id) and p.get('image_url') and p['image_url'] not in recently_used_images), None)
            
        if not chosen_prod:
            # กรองสินค้าที่รูปยังไม่เคยถูกนำไปโพสต์ใน 100 บทความล่าสุด
            available_prods = [p for p in products if p.get('image_url') and p['image_url'] not in recently_used_images]
            if available_prods:
                import random
                # สุ่มเลือกจากกลุ่ม 15 อันดับแรกที่ไม่เคยใช้รูป เพื่อกระจายภาพ ไม่ให้ค้างอยู่ที่ index 0
                chosen_prod = random.choice(available_prods[:15])
                
        if chosen_prod and chosen_prod.get('image_url'):
            trend_image = chosen_prod['image_url']
            selected_prod = chosen_prod # ให้บันทึก mark_as_posted เพื่อไม่ให้วนกลับมาซ้ำอีก
            print(f"🖼️ เลือกรูปภาพสินค้าปกเทรนด์ (ไม่ซ้ำ): {chosen_prod.get('item_name', '')[:40]} (ID: {chosen_prod['product_id']})")
        else:
            # 2. กรณีสินค้าหมด หรือรูปซ้ำทั้งหมด -> สร้าง Dynamic AI Lifestyle Banner ความละเอียดสูงตามหมวดหมู่ พร้อมสุ่ม seed ทุกรอบ
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
        # กรณีรีวิวสินค้าเดี่ยว: ตรวจสอบว่ารูปของสินค้าที่เลือกซ้ำหรือไม่
        if selected_prod and selected_prod.get('image_url') in recently_used_images:
            print(f"⚠️ รูปภาพของสินค้า {selected_prod['product_id']} เคยใช้ไปแล้วในบทความล่าสุด กำลังสลับไปสินค้าที่มีรูปไม่ซ้ำ...")
            alt_prod = next((p for p in products if p.get('image_url') and p['image_url'] not in recently_used_images), None)
            if alt_prod:
                selected_prod = alt_prod
                print(f"🔄 สลับไปใช้สินค้า: {selected_prod.get('item_name', '')[:40]} (ID: {selected_prod['product_id']})")

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
