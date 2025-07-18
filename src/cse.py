import json
import requests
import time
from datetime import datetime, timedelta

class QuotaManager:
    """Manages API quota to prevent exceeding limits"""
    def __init__(self, daily_limit=100):
        self.daily_limit = daily_limit
        self.requests_today = 0
        self.last_reset_date = datetime.now().date()
    
    def check_quota(self):
        """Check if we have quota remaining"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.requests_today = 0
            self.last_reset_date = current_date
        
        return self.requests_today < self.daily_limit
    
    def increment_usage(self):
        """Increment usage counter"""
        self.requests_today += 1
    
    def get_remaining(self):
        """Get remaining quota"""
        return max(0, self.daily_limit - self.requests_today)

# Global quota manager instance
quota_manager = QuotaManager()

def cse(query: str, num_pages: int, API_KEY: str, SEARCH_ENGINE_ID: str) -> dict:
    """Enhanced CSE with quota management and better error handling"""
    results = {}
    
    # Check quota before making any requests
    if not quota_manager.check_quota():
        raise Exception(f"Daily quota exceeded ({quota_manager.daily_limit} requests/day). Remaining: 0")
    
    for i in range(num_pages):
        page = i + 1
        start = (page - 1) * 10 + 1

        # Check quota before each request
        if not quota_manager.check_quota():
            print(f"⚠️ Quota exhausted after page {i}. Remaining quota: 0")
            break

        url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={SEARCH_ENGINE_ID}&q={query}&start={start}"

        try:
            # Add exponential backoff for rate limiting
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, timeout=15)
                    
                    # Handle rate limiting specifically
                    if response.status_code == 429:
                        wait_time = (2 ** attempt) * 2  # Exponential backoff: 2, 4, 8 seconds
                        print(f"⏳ Rate limited (429). Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    break
                    
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(1)
            
            # Increment quota counter for successful request
            quota_manager.increment_usage()
            
            response_json = response.json()
            
            # Check for API errors
            if 'error' in response_json:
                error_info = response_json['error']
                if 'quotaExceeded' in str(error_info):
                    raise Exception(f"Google CSE quota exceeded: {error_info}")
                print(f"API Error on page {page}: {error_info}")
                continue
            
            # Get items safely
            data = response_json.get("items")
            
            if not data:  # Handle None or empty list
                print(f"No results found for page {page}")
                continue

            for idx, item in enumerate(data, start=1):
                title = item.get("title", "No title")
                link = item.get("link", "No link")
                
                # Clean YouTube titles and URLs
                if 'youtube.com' in link:
                    # Remove " - YouTube" from titles
                    title = title.replace(" - YouTube", "")
                    # Ensure clean YouTube URL
                    if 'youtube.com/watch' in link:
                        video_id = None
                        if 'v=' in link:
                            video_id = link.split('v=')[1].split('&')[0]
                            link = f"https://www.youtube.com/watch?v={video_id}"
                
                results[int(idx+start-1)] = [title, link]
                
            # Add delay between requests to be respectful
            if i < num_pages - 1:  # Don't sleep after last page
                time.sleep(0.5)
            
        except requests.exceptions.RequestException as e:
            if "429" in str(e):
                print(f"⚠️ Rate limiting detected: {e}")
                raise Exception(f"Rate limit exceeded: {e}")
            print(f"Request error on page {page}: {e}")
            continue
        except json.JSONDecodeError as e:
            print(f"JSON decode error on page {page}: {e}")
            continue
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"⚠️ Quota/Rate limit error: {e}")
                raise e
            print(f"Unexpected error on page {page}: {e}")
            continue

    print(f"Total results found: {len(results)} | Quota remaining: {quota_manager.get_remaining()}")
    return results

def get_quota_status():
    """Get current quota status"""
    return {
        'remaining': quota_manager.get_remaining(),
        'used_today': quota_manager.requests_today,
        'daily_limit': quota_manager.daily_limit,
        'reset_date': quota_manager.last_reset_date.isoformat()
    }