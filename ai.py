import os
import json
import time
import google.generativeai as genai
from google.api_core import exceptions

def get_available_models():
    """โมเดลเป้าหมายหลักตามที่ผู้ใช้กำหนด: gemini-3.1-flash-lite"""
    return [
        'gemini-3.1-flash-lite',
        'models/gemini-3.1-flash-lite',
        'gemini-2.5-flash',
        'gemini-flash-latest'
    ]

def call_gemini_with_retry(prompt, generation_config=None, max_retries=3):
    """
    เรียก Gemini API พร้อมระบบ Dynamic Model Discovery และ Cooldown อัตโนมัติ
    - ดึงโมเดลจริงที่เปิดใช้งานอยู่จาก list_models เพื่อป้องกัน Error 404
    - Cooldown อัตโนมัติเมื่อติด Rate Limit (429)
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in .env")
    
    genai.configure(api_key=api_key)
    models_to_try = get_available_models()

    if generation_config is None:
        generation_config = {
            "response_mime_type": "application/json",
        }

    for attempt in range(max_retries):
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=generation_config)
                if response and response.text:
                    result = json.loads(response.text)
                    return result
            except exceptions.ResourceExhausted as e:
                wait_seconds = 20 * (attempt + 1)
                print(f"⏳ ติด Gemini Rate Limit (429) บนโมเดล {model_name}. กำลังรอ {wait_seconds} วินาทีเพื่อลองใหม่ (รอบที่ {attempt + 1}/{max_retries})...")
                time.sleep(wait_seconds)
                continue
            except exceptions.NotFound:
                # ถ้าโมเดลไม่มีอยู่ ให้ข้ามไปโมเดลถัดไปทันที
                continue
            except json.JSONDecodeError:
                print(f"⚠️ แปลงผลลัพธ์เป็น JSON ไม่สำเร็จจากโมเดล {model_name}: {response.text[:150]}")
                continue
            except Exception as e:
                print(f"⚠️ เกิดข้อผิดพลาดเมื่อเรียก {model_name}: {e}")
                time.sleep(3)
                continue

    print("❌ ไม่สามารถดึงข้อมูลจาก Gemini ได้หลังจากลองใหม่ครบทุกรอบ")
    return None

def generate_social_content(products):
    """
    Asks Gemini to analyze products, pick the best one, and write a caption.
    Expects a list of dictionaries containing product details.
    """
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
    คุณคือนักรีวิวสินค้าและบล็อกเกอร์สาย AI SEO & GEO (Generative Engine Optimization) ที่เขียนภาษาไทยได้เป็นธรรมชาติ น่าเชื่อถือ และดึงดูดผู้อ่าน
    เป้าหมายคือเขียนบทความรีวิวที่ Search Engines และระบบ AI (เช่น Google AI Overviews, Perplexity, ChatGPT Search, Gemini) สามารถจับประเด็น ดึงไปสรุป และใช้อ้างอิงเป็นคำตอบอันดับหนึ่งได้อย่างแม่นยำ
    
    นี่คือรายการสินค้า {len(products)} ชิ้น ที่ดึงมาจาก Shopee วันนี้ พร้อมข้อมูลยอดขายและรีวิว:
    
    {chr(10).join(product_summary)}
    
    งานของคุณคือ:
    1. วิเคราะห์และเลือกสินค้ามา 1 ชิ้น ที่น่าสนใจที่สุด (ยอดขายสูง รีวิวดี ค่าคอมคุ้มค่า)
    2. จัดหมวดหมู่สินค้าชิ้นนี้ โดยเลือกจากตัวเลือกต่อไปนี้เท่านั้น: "ไอที & แกดเจ็ต", "เครื่องใช้ในบ้าน", "สุขภาพ & ความงาม", "กีฬา & ไลฟ์สไตล์", หรือ "อื่นๆ"
    3. เขียนบทความรีวิวสินค้านี้เพื่อลงเว็บไซต์แบบ AI SEO (ไม่ต้องใส่ <h1> เพราะเว็บมีให้แล้ว) โดยมีโครงสร้างดังนี้:
       - ชื่อบทความ (blog_title): พาดหัวกระตุ้นความสนใจ ชวนคลิก ใส่ชื่อสินค้า ชูจุดเด่นหลัก และมีคำค้นหายอดฮิต เช่น "รีวิว [ชื่อสินค้า] ดีไหม? สรุปจุดเด่น ข้อพิจารณา และความคุ้มค่าก่อนซื้อ"
       - ลิงก์ SEO (blog_slug): ภาษาอังกฤษหรือคาราโอเกะสั้นๆ ตัวพิมพ์เล็ก ใช้ขีดกลางคั่น (เช่น review-buddytech-bluetooth-keyboard)
       - คำโปรยสั้นๆ (blog_excerpt): สรุปประเด็นหลัก 1-2 ประโยค สำหรับแสดงหน้าแรกและเป็น Meta Description
       - เนื้อหาบทความ (blog_content): จัดรูปแบบเป็น HTML คุณภาพสูงตามโครงสร้าง Answer-First ต่อไปนี้:
         1) [⚡ กล่องสรุปด่วนใน 3 วินาที (Summary Box)]: อยู่บนสุดของบทความ ใช้แท็กและสไตล์ HTML ดังนี้:
            <div style="background:rgba(2,132,199,0.08); border-left:4px solid #0284c7; padding:16px 20px; margin-bottom:24px; border-radius:8px;">
              <strong style="color:#0369a1; font-size:1.05em;">⚡ สรุปด่วนใน 3 วินาที:</strong>
              <p style="margin:8px 0 0 0;">(บอกสั้นกระชับ 2-3 บรรทัดว่าสินค้านี้คืออะไร จุดเด่นที่สุดคืออะไร เหมาะกับใคร และคุ้มค่าไหมกับราคา)</p>
            </div>
         2) [บทนำและปัญหา <h2>]: เล่าถึงปัญหาของผู้ใช้ทั่วไป และทำไมสินค้านี้ถึงเป็นทางออกที่น่าสนใจ
         3) [จุดเด่นและฟังก์ชันเด่น <h3> พร้อม <ul> <li>]: เจาะลึกฟีเจอร์เด่น 3-4 ข้อ พร้อมอธิบายประโยชน์ต่อการใช้งานจริง
         4) [⚖️ จุดเด่น vs ข้อพิจารณา (Pros & Cons) <h3>]: นำเสนอข้อดีและข้อสังเกตอย่างตรงไปตรงมาเพื่อความน่าเชื่อถือตามหลัก Google E-E-A-T
            - <strong>จุดเด่น (ข้อดี):</strong> ใช้แท็ก <ul> <li><strong>...:</strong> ...</li>
            - <strong>ข้อพิจารณา (ข้อสังเกต):</strong> ใช้แท็ก <ul> <li><strong>...:</strong> ...</li> (ข้อสังเกตหรือข้อจำกัดเล็กๆ น้อยๆ ที่ผู้ซื้อควรรู้)
         5) [👤 สินค้านี้เหมาะกับใคร <h3>]: สรุปให้ชัดเจนว่าใครควรซื้อ และใครอาจจะไม่เหมาะ
         6) [❓ คำถามที่พบบ่อย (FAQ) <h3>]: คำถามที่คนค้นหาบ่อย 3 ข้อ พร้อมคำตอบสั้น กระชับ ตรงประเด็น จัดรูปแบบ:
            <p><strong>Q: [คำถาม เช่น ใช้งานยากไหม? / คุ้มค่าไหม?]</strong><br>A: [คำตอบสั้น ชัดเจน ตรงประเด็น]</p>
         7) [🎯 สรุปความคุ้มค่า <h3>]: บทสรุปส่งท้าย ช่วยให้ผู้อ่านตัดสินใจซื้อได้อย่างมั่นใจ
    4. แต่งแคปชั่นเพื่อโปรโมท "บทความนี้" ไปลง 3 แพลตฟอร์ม (เป้าหมายคือให้คนกดลิงก์เข้าไปอ่านบทความในเว็บ):
       - เว้นที่ [LINK] ไว้สำหรับใส่ลิงก์บทความ (ไม่ต้องใส่ลิงก์ Affiliate ในโซเชียล ให้คนเข้าเว็บก่อน)
       - Facebook: เล่าเกริ่นนำกระตุ้นความอยากรู้ ชวนให้คลิกอ่านรีวิวเต็มๆ ที่เว็บ ความยาว 3-5 บรรทัด
       - Twitter (X): สั้น กระชับ จับใจความน่าสนใจ พร้อม Hashtag ความยาวไม่เกิน 2 บรรทัด 
       - LINE OA: ทักทายสั้นๆ เป็นกันเอง เหมือนเพื่อนส่งลิงก์รีวิวเด็ดๆ มาให้อ่าน
       
    ตอบกลับมาในรูปแบบ JSON เท่านั้น โดยมีโครงสร้างดังนี้:
    {{
        "selected_product_id": "รหัส ID ของสินค้าที่คุณเลือก",
        "reason": "เหตุผลที่เลือกสินค้านี้",
        "category": "หมวดหมู่ของสินค้า (จากตัวเลือกที่กำหนด)",
        "blog_slug": "ลิงก์ url สำหรับ seo",
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
    
    return call_gemini_with_retry(prompt, generation_config)

def generate_trend_content(products):
    """
    Asks Gemini to analyze products and write a knowledge/trend article with AI SEO structure.
    """
    product_summary = []
    for p in products[:30]: # Use top 30 to save tokens
        sales_info = f" | ยอดขาย: {p.get('sales', 0)} ชิ้น" if 'sales' in p else ""
        desc = p.get('description') or ''
        short_desc = desc[:150] + "..." if len(desc) > 150 else desc 
        
        product_summary.append(
            f"Name: {p['item_name']} | Price: {p['price']}{sales_info}\n"
            f"รายละเอียด: {short_desc}\n"
            "---"
        )
    
    prompt = f"""
    คุณคือนักการตลาดและบล็อกเกอร์สายความรู้ (Tech & Lifestyle Blogger) ที่เชี่ยวชาญด้าน AI SEO & GEO
    นี่คือข้อมูลสินค้ายอดฮิต {len(product_summary)} อันดับแรก ที่คนกำลังให้ความสนใจบน Shopee ในขณะนี้:
    
    {chr(10).join(product_summary)}
    
    งานของคุณคือ:
    1. วิเคราะห์ข้อมูลเหล่านี้ แล้วเขียนบทความให้ความรู้ (Tips & Tricks) หรืออัปเดตเทรนด์ตลาด โดย *ไม่ต้องฮาร์ดเซลขายสินค้าเจาะจง* แต่ให้พูดถึงภาพรวม เทคนิคการเลือกซื้อ หรือวิธีเปรียบเทียบในกลุ่มสินค้าที่กำลังฮิต
    2. จัดหมวดหมู่บทความนี้ โดยเลือกจากตัวเลือกต่อไปนี้เท่านั้น: "ไอที & แกดเจ็ต", "เครื่องใช้ในบ้าน", "สุขภาพ & ความงาม", "กีฬา & ไลฟ์สไตล์", หรือ "อื่นๆ"
    3. เขียนบทความแบบ AI SEO (ไม่ต้องใส่ <h1> เพราะเว็บมีให้แล้ว) โดยมีโครงสร้างดังนี้:
       - ชื่อบทความ (blog_title): พาดหัวดึงดูด น่าคลิก เช่น "เจาะเทรนด์...", "วิธีเลือกซื้อ... ฉบับปี 2026 รู้ไว้ก่อนเสียเงินฟรี"
       - ลิงก์ SEO (blog_slug): ภาษาอังกฤษสั้นๆ ตัวพิมพ์เล็ก ใช้ขีดกลางคั่น (เช่น trend-smart-home-2026)
       - คำโปรยสั้นๆ (blog_excerpt): สรุปใจความสำคัญ 1-2 ประโยค
       - เนื้อหาบทความ (blog_content): จัดรูปแบบเป็น HTML คุณภาพสูงตามโครงสร้าง Answer-First ดังนี้:
         1) [⚡ สรุปสาระสำคัญใน 1 นาที (Summary Box)]: อยู่บนสุดของบทความ ใช้แท็กและสไตล์ HTML:
            <div style="background:rgba(2,132,199,0.08); border-left:4px solid #0284c7; padding:16px 20px; margin-bottom:24px; border-radius:8px;">
              <strong style="color:#0369a1; font-size:1.05em;">⚡ สรุปสาระสำคัญใน 1 นาที:</strong>
              <p style="margin:8px 0 0 0;">(สรุปภาพรวมเทรนด์ ประเด็นหลักที่ผู้อ่านจะได้รับ และคำแนะนำสำคัญ 2-3 บรรทัด)</p>
            </div>
         2) [บทวิเคราะห์และที่มาของเทรนด์ <h2>]: ทำไมเทรนด์นี้ถึงมาแรง พฤติกรรมผู้บริโภคที่เปลี่ยนไป
         3) [เทคนิคการเลือกและข้อควรรู้ <h3> พร้อม <ul>, <ol>]: รายละเอียดและคำแนะนำเชิงลึกที่เป็นประโยชน์
         4) [⚖️ เช็กลิสต์ความคุ้มค่าก่อนซื้อ <h3>]: เกณฑ์ที่ต้องพิจารณา สิ่งที่ควรมี vs สิ่งที่ไม่จำเป็น
         5) [❓ คำถามที่พบบ่อย (FAQ) <h3>]: 3 คำถามยอดฮิตที่คนมักสงสัยเกี่ยวกับเทรนด์นี้ พร้อมคำตอบตรงประเด็น:
            <p><strong>Q: [คำถาม?]</strong><br>A: [คำตอบสั้น ชัดเจน ตรงประเด็น]</p>
         6) [🎯 สรุปภาพรวมและข้อคิด <h3>]: ข้อสรุปปิดท้าย
    4. แต่งแคปชั่นเพื่อแชร์ความรู้นี้ไปลง 3 แพลตฟอร์ม (เป้าหมายคือให้คนกดลิงก์เข้าไปอ่านบทความในเว็บ):
       - เว้นที่ [LINK] ไว้สำหรับใส่ลิงก์บทความ
       - Facebook: เล่าเกริ่นนำกระตุ้นความอยากรู้ ความยาว 3-5 บรรทัด
       - Twitter (X): สั้น กระชับ จับใจความน่าสนใจ พร้อม Hashtag ความยาวไม่เกิน 2 บรรทัด 
       - LINE OA: ทักทายสั้นๆ เป็นกันเอง เหมือนเพื่อนส่งบทความดีๆ มาให้อ่าน
       
    ตอบกลับมาในรูปแบบ JSON เท่านั้น โดยมีโครงสร้างดังนี้:
    {{
        "category": "หมวดหมู่ของบทความ (จากตัวเลือกที่กำหนด)",
        "blog_slug": "ลิงก์ url สำหรับ seo",
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
    
    return call_gemini_with_retry(prompt, generation_config)
