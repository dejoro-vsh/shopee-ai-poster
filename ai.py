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
        rating_info = f" | รีวิว: {p.get('rating', 0.0)} ดาว" if 'rating' in p and p.get('rating', 0) > 0 else ""
        desc = p.get('description', '')
        short_desc = desc[:300] + "..." if len(desc) > 300 else desc # limit length to save tokens
        
        product_summary.append(
            f"ID: {p['product_id']} | Name: {p['item_name']} | Price: {p['price']} | Commission: {p['commission']}{sales_info}{rating_info}\n"
            f"รายละเอียด: {short_desc}\n"
            "---"
        )
    
    prompt = f"""
    คุณคือนักรีวิวสินค้าและป้ายยา (Affiliate Marketer) ที่เขียนภาษาไทยได้เป็นธรรมชาติสุดๆ เหมือนเพื่อนป้ายยาเพื่อน
    นี่คือรายการสินค้า {len(products)} ชิ้น ที่ดึงมาจาก Shopee วันนี้ พร้อมข้อมูลยอดขายและรีวิว:
    
    {chr(10).join(product_summary)}
    
    งานของคุณคือ:
    1. วิเคราะห์และเลือกสินค้ามาเพียง 1 ชิ้น โดยเลือกตัวที่มีความน่าสนใจที่สุด (พิจารณาจากยอดขายที่สูง, รีวิวที่ดี, สินค้าใช้งานได้จริง หรือได้ค่าคอมมิชชันคุ้มค่า)
    2. แต่งแคปชั่นเพื่อนำไปโพสต์แยก 3 แพลตฟอร์ม โดยมีเงื่อนไขสำคัญคือ:
       - ต้องอ่านแล้ว 'เป็นธรรมชาติ' ไม่ดูเหมือนหุ่นยนต์โฆษณา
       - ดึง 'ข้อมูลที่สำคัญจริงๆ' จากรายละเอียดสินค้า (Description) มาบอกคนอ่าน เช่น จุดเด่น, วิธีใช้, หรือทำไมถึงควรซื้อ
       - หากสินค้ามียอดขายสูง หรือรีวิวดี ให้นำมาอ้างอิงเพื่อเพิ่มความน่าเชื่อถือด้วย
       - เว้นที่ [LINK] ไว้สำหรับใส่ลิงก์ Affiliate
       
       - Facebook: เล่าเรื่องเป็นธรรมชาติ ให้ความรู้หรือบอกประโยชน์ชัดเจน ความยาว 3-6 บรรทัด
       - Twitter (X): สั้น กระชับ จับใจความสำคัญ พร้อม Hashtag ที่เข้ากับสินค้า ความยาวไม่เกิน 2 บรรทัด
       - LINE OA: สั้น เป็นกันเอง เหมือนทักแชทไปบอกเพื่อน กระตุ้นให้กดดู
       
    ตอบกลับมาในรูปแบบ JSON เท่านั้น โดยมีโครงสร้างดังนี้:
    {{
        "selected_product_id": "รหัส ID ของสินค้าที่คุณเลือก",
        "reason": "เหตุผลที่คุณเลือกสินค้านี้ (สั้นๆ)",
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
