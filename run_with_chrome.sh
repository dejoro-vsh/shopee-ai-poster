#!/bin/bash
# Script เปิด Google Chrome บน Mac ในโหมด Remote Debugging Port 9222
# เพื่อให้บอทเชื่อมต่อ Chrome ตัวจริงได้ทันที 100% ไร้ Anti-bot

echo "=================================================="
echo "🚀 ระบบเปิด Google Chrome สำหรับบอท Shopee (Mac)"
echo "=================================================="

# 1. ตรวจสอบว่าเปิดอยู่ด้วย Port 9222 หรือยัง
if curl -s http://localhost:9222/json/version > /dev/null 2>&1; then
    echo "✅ ตรวจพบ Google Chrome กำลังรัน Port 9222 อยู่แล้ว! พร้อมใช้งานทันที"
    exit 0
fi

# 2. ถ้ามี Chrome เปิดอยู่แต่ยังไม่มี port 9222 ต้องปิดก่อนเพื่อให้ port 9222 ทำงาน
if pgrep -x "Google Chrome" > /dev/null; then
    echo "⚠️ ตรวจพบ Google Chrome เปิดค้างอยู่แบบปกติ (ไม่มี Port 9222)"
    echo "🔄 กำลังรีสตาร์ต Chrome ในโหมด Port 9222 (แท็บเดิมจะกลับมาทั้งหมด)..."
    killall "Google Chrome" 2>/dev/null
    sleep 2
fi

echo "🌐 กำลังเปิด Google Chrome พร้อม Port 9222..."
nohup /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --restore-last-session "https://affiliate.shopee.co.th/offer/custom_link" > /dev/null 2>&1 &
sleep 3

if curl -s http://localhost:9222/json/version > /dev/null 2>&1; then
    echo "🎉 สำเร็จ! Google Chrome เชื่อมต่อ Port 9222 พร้อมทำงานแล้ว"
    echo "👉 สามารถรันคำสั่งแปลงลิงก์ได้เลยทันที:"
    echo "   python3 custom_link_generator.py \"<URL สินค้า>\""
else
    echo "⚠️ Chrome กำลังเปิด... ลองรัน python3 custom_link_generator.py ได้เลยครับ"
fi
echo "=================================================="
