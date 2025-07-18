import asyncio
import aiohttp
import concurrent.futures
from typing import List, Dict, Optional
import time
from utils import process_html

class ParallelContentProcessor:
    def __init__(self, max_workers: int = 5, timeout: int = 10):
        self.max_workers = max_workers
        self.timeout = timeout
        self.session_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    
    async def fetch_content_async(self, session: aiohttp.ClientSession, url: str) -> Dict:
        """Async fetch single URL content"""
        try:
            async with session.get(url, timeout=self.timeout) as response:
                if response.status == 200:
                    content = await response.text()
                    processed_content = process_html(content)
                    
                    return {
                        'url': url,
                        'content': processed_content,
                        'word_count': len(processed_content.split()),
                        'success': True,
                        'error': None
                    }
                else:
                    # Handle non-200 status codes
                    return {
                        'url': url,
                        'content': '',
                        'word_count': 0,
                        'success': False,
                        'error': f'HTTP {response.status}'
                    }
        except Exception as e:
            return {
                'url': url,
                'content': '',
                'word_count': 0,
                'success': False,
                'error': str(e)
            }
    
    async def fetch_multiple_contents(self, urls: List[str]) -> List[Dict]:
        """Fetch multiple URLs concurrently"""
        connector = aiohttp.TCPConnector(limit=self.max_workers)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        async with aiohttp.ClientSession(
            connector=connector, 
            timeout=timeout,
            headers=self.session_headers
        ) as session:
            tasks = [self.fetch_content_async(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and return successful results
            valid_results = []
            for result in results:
                if isinstance(result, dict):
                    valid_results.append(result)
                else:
                    print(f"Exception in fetch: {result}")
            
            return valid_results
    
    def process_search_results_parallel(self, search_results: Dict, max_results: int = 5) -> List[Dict]:
        """Process search results in parallel"""
        urls = []
        titles = []
        
        for idx, (title, link) in list(search_results.items())[:max_results]:
            urls.append(link)
            titles.append(title)
        
        # Run async content fetching
        start_time = time.time()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            content_results = loop.run_until_complete(self.fetch_multiple_contents(urls))
        finally:
            loop.close()
        
        end_time = time.time()
        print(f"Parallel processing completed in {end_time - start_time:.2f} seconds")
        
        # Combine with titles and filter successful results
        combined_results = []
        for i, content_result in enumerate(content_results):
            if content_result['success'] and content_result['word_count'] > 50:
                combined_results.append({
                    'title': titles[i] if i < len(titles) else 'Unknown',
                    'url': content_result['url'],
                    'content': content_result['content'],
                    'word_count': content_result['word_count']
                })
        
        return combined_results

# Usage example function
def get_enhanced_search_results(query: str, num_pages: int, API_KEY: str, 
                              SEARCH_ENGINE_ID: str, max_results: int = 5) -> List[Dict]:
    """Complete enhanced search with parallel processing"""
    from cse import cse
    
    # Get search results
    search_results = cse(query, num_pages, API_KEY, SEARCH_ENGINE_ID)
    
    # Process content in parallel
    processor = ParallelContentProcessor(max_workers=3)
    content_results = processor.process_search_results_parallel(search_results, max_results)
    
    return content_results