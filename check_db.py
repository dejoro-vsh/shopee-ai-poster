from db import init_db, get_db_connection

def update_recent_posts():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check what posts exist
    cur.execute("SELECT id, title, image_url, category FROM blog_posts ORDER BY created_at DESC LIMIT 5;")
    posts = cur.fetchall()
    
    for p in posts:
        print(f"ID: {p[0]}, Title: {p[1]}, Category: {p[3]}")
        print(f"Image: {p[2]}")
        print("-" * 50)
        
if __name__ == "__main__":
    update_recent_posts()
