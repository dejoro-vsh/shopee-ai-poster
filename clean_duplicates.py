import os
import psycopg2
from dotenv import load_dotenv
import db

def clean_duplicates():
    print("🧹 กำลังเริ่มกระบวนการล้างข้อมูลที่ซ้ำซ้อนใน Database...")
    conn = db.get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. Check total rows before cleaning
            cur.execute("SELECT COUNT(*) FROM shopee_products")
            total_before = cur.fetchone()[0]
            print(f"📦 จำนวนสินค้าทั้งหมดก่อนล้าง: {total_before} รายการ")

            # 2. Delete duplicates keeping the one with the highest ID (newest)
            # We only do this for rows where item_id is not null
            delete_query = """
                DELETE FROM shopee_products
                WHERE id NOT IN (
                    SELECT MAX(id)
                    FROM shopee_products
                    WHERE item_id IS NOT NULL
                    GROUP BY item_id
                ) AND item_id IS NOT NULL;
            """
            cur.execute(delete_query)
            deleted_count = cur.rowcount
            print(f"✂️ ลบข้อมูลที่ซ้ำซ้อนทิ้งไปจำนวน: {deleted_count} รายการ")

            # 3. Try to add a UNIQUE constraint so it never happens again
            try:
                cur.execute("ALTER TABLE shopee_products ADD CONSTRAINT shopee_products_item_id_key UNIQUE (item_id);")
                print("🔒 สร้างเกราะป้องกัน (UNIQUE Constraint) สำเร็จ! ต่อไปจะไม่มีข้อมูลซ้ำอีก")
            except Exception as e:
                # If constraint already exists or fails, it's fine. 
                # We rollback just the constraint addition to not ruin the transaction.
                conn.rollback()
                pass
            else:
                conn.commit()

            # If the constraint addition failed and rolled back the delete, we need to delete again and commit
            if deleted_count > 0:
                try:
                    cur.execute(delete_query)
                    conn.commit()
                except:
                    pass

            # 4. Check total rows after cleaning
            cur.execute("SELECT COUNT(*) FROM shopee_products")
            total_after = cur.fetchone()[0]
            print(f"✨ จำนวนสินค้าทั้งหมดหลังล้าง: {total_after} รายการ (สะอาดเอี่ยม!)")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    load_dotenv()
    clean_duplicates()
