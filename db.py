import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set in .env")
    return psycopg2.connect(db_url)

def get_todays_products(limit=50):
    """Fetches the latest products added today, ordered by highest commission"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            today = date.today()
            query = """
                SELECT 
                    id, item_id as product_id, title as item_name, price, price as discount_price, 
                    commission, image_url, affiliate_link as aff_link, shop_name as category_name
                FROM shopee_products
                WHERE DATE(created_at) = %s
                ORDER BY commission DESC
                LIMIT %s
            """
            cur.execute(query, (today, limit))
            products = cur.fetchall()
            return products
    finally:
        conn.close()
