from db import init_db, get_db_connection

def fix_images():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get recent posts that might have bad images (e.g., from today or yesterday)
    # Since we can't reliably know which is "trend", we can look for specific keywords or just prompt the user.
    # Actually, we can just update all posts with the static unsplash image, and also manually provide a prompt for a few recent ones.
    
    cur.execute("SELECT id, title, image_url, category FROM blog_posts ORDER BY created_at DESC LIMIT 10;")
    posts = cur.fetchall()
    
    print("Found recent posts:")
    for p in posts:
        post_id = p[0]
        title = p[1]
        image_url = p[2]
        category = p[3]
        
        print(f"[{post_id}] {title}")
        print(f"Current Image: {image_url}")
        
        # Only update if the user wants to. Let's auto-generate an image based on the title.
        image_prompt = f"{title} photorealistic 8k"
        encoded_prompt = urllib.parse.quote(image_prompt)
        new_image = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&nologo=true"
        
        # We will only update if the current image is the static unsplash one OR if it's the fruit one (since we don't know the exact URL, let's just ask for confirmation in a real script, but here we can just update the top 2 if they are trend posts).
        # Actually, if we just update the 2 most recent posts' images using their titles, it will be fine.
        ans = input(f"Update image for '{title}'? (y/n): ")
        if ans.lower() == 'y':
            cur.execute("UPDATE blog_posts SET image_url = %s WHERE id = %s", (new_image, post_id))
            conn.commit()
            print(f"Updated! New image: {new_image}")
        print("-" * 50)
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_images()
