# src/api.py
import requests
import logging
from time import sleep

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Connection": "keep-alive"
}

def get_posts(url=None, max_retries=3, delay=2):
    if url is None:
        url = "https://jsonplaceholder.typicode.com/posts"

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            logging.info(f"Successfully fetched posts on attempt {attempt}")
            return response.json()

        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt} failed: {e}")

            if attempt < max_retries:
                sleep(delay)
            else:
                logging.error("Max retries reached")
                return []

if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(level=logging.INFO)
    
    posts = get_posts()

    logging.info(f"Number of posts fetched: {len(posts)}")

    if posts:
        logging.info(f"First post title: {posts[0]['title']}...")