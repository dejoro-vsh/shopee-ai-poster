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
    # Use 1.5 Flash for speed and cost-effectiveness (free tier is huge)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Prepare data for AI
    product_summary = []
    for p in products:
        product_summary.append(
            f"ID: {p['product_id']} | Name: {p['item_name']} | Price: {p['price']} | Discounted: {p['discount_price']} | Commission: {p['commission']} | Category: {p['category_name']}"
        )
    
    prompt = f"""
    คุณคือนักการตลาดออนไลน์ระดับแนวหน้า (Affiliate Marketer) ที่เขียนคำโฆษณาภาษาไทยได้เก่งมาก
    นี่คือรายการสินค้า {len(products)} ชิ้น ที่ดึงมาจาก Shopee วันนี้:
    
    {chr(10).join(product_summary)}
    
    งานของคุณคือ:
    1. วิเคราะห์และเลือกสินค้าที่ "น่าจะขายดีที่สุดและได้ไวรัล" มาเพียง 1 ชิ้น (พิจารณาจากราคาที่ลดเยอะ หรือ ค่านายหน้าที่คุ้มค่า)
    2. แต่งแคปชั่น Facebook ให้น่าสนใจ มีความกระตือรือร้น ใช้ Emoji ให้เหมาะสม (อย่าเยอะเกินไป) และใส่ Hashtag ที่เกี่ยวข้อง
    3. ความยาวแคปชั่นประมาณ 3-5 บรรทัด กำลังดี
    4. ห้ามใส่ URL ลิงก์ในแคปชั่น (เราจะเติมลิงก์ Affiliate เองในโค้ด) ให้เว้นที่ไว้ว่า [LINK]
    
    ตอบกลับมาในรูปแบบ JSON เท่านั้น โดยมีโครงสร้างดังนี้:
    {{
        "selected_product_id": "รหัส ID ของสินค้าที่คุณเลือก",
        "reason": "เหตุผลที่คุณเลือกสินค้านี้สั้นๆ",
        "caption": "ข้อความแคปชั่นที่คุณแต่ง (เว้นที่ [LINK] ไว้ใส่ลิงก์)"
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
