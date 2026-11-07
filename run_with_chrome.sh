#!/bin/bash
# Script เปิด Google Chrome บน Mac ในโหมด Remote Debugging Port 9222
# เพื่อให้บอทเชื่อมต่อได้ทันที 100% ไร้ Anti-bot

echo "🚀 กำลังเปิด Google Chrome สำหรับระบบ Shopee Poster..."

# ตรวจสอบว่า Chrome เปิดอยู่หรือไม่ ถ้ามีให้เปิดพร้อม port 9222
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --no-first-run --no-default-browser-check "https://affiliate.shopee.co.th/offer/custom_link" &

echo "✅ เปิด Google Chrome เรียบร้อยแล้ว (Port 9222)"
echo "💡 เมื่อหน้าต่างเปิดขึ้นมา หากต้องการแปลงลิงก์ สามารถสั่งรัน:"
echo "   python3 custom_link_generator.py \"<URL สินค้า>\""
