import os
import json
import google.generativeai as genai

def generate_social_content(products):
    """
    Asks Gemini to analyze products, pick the best one, and write a caption.
    Expects a list of dictionaries containing product details.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in .env")
    
    genai.configure(api_key=api_key)
    # Use flash-latest for speed and cost-effectiveness (free tier is huge)
    model = genai.GenerativeModel('gemini-flash-latest')
    
    # Prepare data for AI
    product_summary = []
    for p in products:
        sales_info = f" | ยอดขาย: {p.get('sales', 0)} ชิ้น" if 'sales' in p else ""
        rating_info = f" | รีวิว: {p.get('rating', 0.0)} ดาว" if 'rating' in p and p.get('rating') and float(p.get('rating')) > 0 else ""
        desc = p.get('description') or ''
        short_desc = desc[:300] + "..." if len(desc) > 300 else desc # limit length to save tokens
        
        product_summary.append(
            f"ID: {p['product_id']} | Name: {p['item_name']} | Price: {p['price']} | Commission: {p['commission']}{sales_info}{rating_info}\n"
            f"รายละเอียด: {short_desc}\n"
            "---"
        )
    
    prompt = f"""
    คุณคือนักรีวิวสินค้าและบล็อกเกอร์สาย SEO (Affiliate Marketer) ที่เขียนภาษาไทยได้เป็นธรรมชาติและดึงดูด
    นี่คือรายการสินค้า {len(products)} ชิ้น ที่ดึงมาจาก Shopee วันนี้ พร้อมข้อมูลยอดขายและรีวิว:
    
    {chr(10).join(product_summary)}
    
    งานของคุณคือ:
    1. วิเคราะห์และเลือกสินค้ามา 1 ชิ้น ที่น่าสนใจที่สุด (ยอดขายสูง รีวิวดี ค่าคอมคุ้มค่า)
    2. เขียนบทความรีวิวสินค้านี้เพื่อลงเว็บไซต์ (SEO Blog Post) โดยมี:
       - ชื่อบทความ (Title) ที่น่าคลิก ดึงดูดความสนใจ
       - คำโปรยสั้นๆ (Excerpt) สำหรับโชว์หน้าแรก
       - เนื้อหาบทความ (HTML) จัดรูปแบบด้วยแท็ก <h2>, <h3>, <p>, <ul> ให้สวยงาม วิเคราะห์จุดเด่น ข้อดี ข้อเสีย และสรุปว่าทำไมถึงควรซื้อ (ไม่ต้องใส่ <h1> เพราะเว็บมีให้แล้ว)
    3. แต่งแคปชั่นเพื่อโปรโมท "บทความนี้" ไปลง 3 แพลตฟอร์ม (เป้าหมายคือให้คนกดลิงก์เข้าไปอ่านบทความในเว็บ):
       - เว้นที่ [LINK] ไว้สำหรับใส่ลิงก์บทความ (ไม่ต้องใส่ลิงก์ Affiliate ในโซเชียล ให้คนเข้าเว็บก่อน)
       - Facebook: เล่าเกริ่นนำกระตุ้นความอยากรู้ ชวนให้คลิกอ่านรีวิวเต็มๆ ที่เว็บ ความยาว 3-5 บรรทัด
       - Twitter (X): สั้น กระชับ จับใจความน่าสนใจ พร้อม Hashtag ความยาวไม่เกิน 2 บรรทัด 
       - LINE OA: ทักทายสั้นๆ เป็นกันเอง เหมือนเพื่อนส่งลิงก์รีวิวเด็ดๆ มาให้อ่าน
       
    ตอบกลับมาในรูปแบบ JSON เท่านั้น โดยมีโครงสร้างดังนี้:
    {{
        "selected_product_id": "รหัส ID ของสินค้าที่คุณเลือก",
        "reason": "เหตุผลที่เลือกสินค้านี้",
        "blog_title": "ชื่อบทความ (SEO)",
        "blog_excerpt": "คำโปรยสั้นๆ",
        "blog_content": "เนื้อหาบทความแบบ HTML",
        "caption_facebook": "แคปชั่นสำหรับเฟซบุ๊ก [LINK]",
        "caption_twitter": "แคปชั่นสำหรับทวิตเตอร์ [LINK]",
        "caption_line": "แคปชั่นสำหรับไลน์ [LINK]"
    }}
    """
    
    generation_config = {
        "response_mime_type": "application/json",
    }
    
    response = model.generate_content(prompt, generation_config=generation_config)
    
    try:
        result = json.loads(response.text)
        return result
    except json.JSONDecodeError:
        print("Error decoding AI response:", response.text)
        return None
