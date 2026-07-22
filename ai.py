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
        sales_info = f" | Sales: {p.get('sales', 0)}" if 'sales' in p else ""
        product_summary.append(
            f"ID: {p['product_id']} | Name: {p['item_name']} | Price: {p['price']} | Commission: {p['commission']}{sales_info} | Category: {p['category_name']}"
        )
    
    prompt = f"""
    คุณคือนักการตลาดออนไลน์ระดับแนวหน้า (Affiliate Marketer) ที่เขียนคำโฆษณาภาษาไทยได้เก่งมาก
    นี่คือรายการสินค้า {len(products)} ชิ้น ที่ดึงมาจาก Shopee วันนี้:
    
    {chr(10).join(product_summary)}
    
    งานของคุณคือ:
    1. วิเคราะห์และเลือกสินค้ามาเพียง 1 ชิ้น โดยพิจารณาจาก 2 กลยุทธ์หลัก:
       - กลยุทธ์ที่ 1 (เน้นกำไร): เลือกสินค้าที่ค่านายหน้า (Commission) สูง
       - กลยุทธ์ที่ 2 (เน้นไวรัล/Click-bait): เลือกสินค้าที่ราคาถูกมากๆ (Price) เช่น 1 บาท ถึง 99 บาท เพื่อใช้เป็นเหยื่อล่อให้คนกดลิงก์เข้ามาดูเยอะๆ
       ให้คุณตัดสินใจเลือกกลยุทธ์ที่เหมาะสมที่สุดสำหรับวันนี้ และดึงสินค้ามา 1 ชิ้น
    2. แต่งแคปชั่นเพื่อนำไปโพสต์แยก 3 แพลตฟอร์ม โดยห้ามใช้ข้อความเหมือนกัน (เว้นที่ [LINK] ไว้ใส่ลิงก์):
       - Facebook: เล่าเรื่องน่าสนใจ มีความกระตือรือร้น ใช้ Emoji ให้เหมาะสม ความยาว 3-5 บรรทัด
       - Twitter (X): สั้น กระชับ กระแทกใจ ความยาวไม่เกิน 2 บรรทัด (ไม่เกิน 200 ตัวอักษร) พร้อม Hashtag ที่กำลังฮิต
       - LINE OA: สั้นๆ ฟีลเพื่อนป้ายยาเพื่อน ทักทายแบบเป็นกันเอง กระตุ้นให้รีบกดด่วน (Urgency)
       
    ตอบกลับมาในรูปแบบ JSON เท่านั้น โดยมีโครงสร้างดังนี้:
    {{
        "selected_product_id": "รหัส ID ของสินค้าที่คุณเลือก",
        "reason": "เหตุผลที่คุณเลือกสินค้านี้สั้นๆ",
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
