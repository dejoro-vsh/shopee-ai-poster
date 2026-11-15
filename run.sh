#!/bin/bash
# Shopee AI Poster - One-Click Launcher (Mac)
# อัปเดตโค้ดล่าสุดอัตโนมัติและสั่งรันทันทีในคำสั่งเดียว

cd "$(dirname "$0")"

echo "🔄 กำลังซิงค์โค้ดล่าสุดจาก GitHub (ถ้ามี)..."
git pull

echo "🚀 กำลังเริ่มระบบ Shopee AI Poster..."
python3 app.py
