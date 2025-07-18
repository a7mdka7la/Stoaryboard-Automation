import re
import bs4
import requests
from typing import Optional
import PyPDF2
import pdfplumber
import io

def process_html(html_code: str) -> str:
    try:
        # parse the html file content
        soup = bs4.BeautifulSoup(html_code, 'html.parser')

        # remove irrelevant tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
            tag.decompose()

        # get the page main content
        body = soup.body if soup.body else soup
        raw_text = body.get_text(" ", strip=True)

        # Fix: search for any white space characters and replace with single space
        raw_text = re.sub(r"\s+", " ", raw_text)  # Fixed regex pattern

        return raw_text.strip()
    except Exception as e:
        print(f"Error processing HTML: {e}")
        return ""

def extract_pdf_content(pdf_content: bytes) -> str:
    """Extract text content from PDF bytes"""
    try:
        # Method 1: Try pdfplumber first (better for complex PDFs)
        try:
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                text = ""
                # Limit to first 10 pages for performance
                max_pages = min(10, len(pdf.pages))
                for page_num in range(max_pages):
                    page = pdf.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                if text.strip():
                    # Clean up text
                    text = re.sub(r'\s+', ' ', text)
                    return text.strip()
        except Exception as e:
            print(f"pdfplumber failed: {e}")
        
        # Method 2: Fallback to PyPDF2
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            text = ""
            # Limit to first 10 pages
            max_pages = min(10, len(pdf_reader.pages))
            for page_num in range(max_pages):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            if text.strip():
                # Clean up text
                text = re.sub(r'\s+', ' ', text)
                return text.strip()
        except Exception as e:
            print(f"PyPDF2 failed: {e}")
            
        return ""
        
    except Exception as e:
        print(f"Error extracting PDF content: {e}")
        return ""

def fetch_page_content(url: str, timeout: int = 15) -> str:
    """Fetch and process content from URL (HTML or PDF)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        print(f"  📡 Requesting: {url[:80]}...")
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        
        if 'pdf' in content_type or url.lower().endswith('.pdf'):
            print(f"  📄 Processing PDF content...")
            content = extract_pdf_content(response.content)
            if content:
                print(f"  ✅ PDF extracted: {len(content.split())} words")
                return content
            else:
                print(f"  ❌ PDF extraction failed")
                return ""
                
        elif 'html' in content_type:
            print(f"  🌐 Processing HTML content...")
            content = process_html(response.content)
            if content:
                print(f"  ✅ HTML processed: {len(content.split())} words")
                return content
            else:
                print(f"  ❌ HTML processing failed")
                return ""
        else:
            print(f"  ⚠️  Unsupported content type: {content_type}")
            return ""
            
    except requests.exceptions.Timeout:
        print(f"  ⏰ Timeout fetching {url}")
        return ""
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request error for {url}: {e}")
        return ""
    except Exception as e:
        print(f"  ❌ Error fetching {url}: {e}")
        return ""

def fetch_multiple_contents_sequential(urls_with_titles: list, max_results: int = 5) -> list:
    """Sequential content fetching (alternative to parallel processing)"""
    results = []
    
    for i, (title, url) in enumerate(urls_with_titles[:max_results], 1):
        print(f"Fetching content {i}/{min(len(urls_with_titles), max_results)}: {title[:60]}...")
        
        content = fetch_page_content(url)
        
        if content and len(content.split()) > 100:  # Increased threshold for meaningful content
            results.append({
                'title': title,
                'url': url,
                'content': content,
                'word_count': len(content.split())
            })
            print(f"✓ Success: {len(content.split())} words")
        else:
            print(f"✗ Skipped: insufficient content")
    
    return results