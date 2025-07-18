from flask import Flask, render_template, request, jsonify, session
import os
import sys
import groq
import dotenv
import time
import uuid

# Add src directory to Python path (correct this time)
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Now import from src directory
import search_query, cse, utils, summarize_page_content

# Load environment variables
dotenv.load_dotenv()

app = Flask(__name__)  # Remove template_folder since templates/ is in same directory
app.secret_key = os.urandom(24)

# Initialize Groq client
groq_client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))

# Configuration
CONFIG = {
    'engine_id': os.getenv("SEARCH_ENGINE_ID"),
    'google_cse_api': os.getenv("GOOGLE_CUSTOM_SEARCH_JSON_API_KEY"),
    'max_results': 5,
    'num_pages': 3
}

# YouTube channels to search for relevant videos
YOUTUBE_CHANNELS = [
    "UCzvVPvdNU6nL4yxLxQgQZSQ",  # Khan Academy
    "UCHnyfMqiRRG1u-2MsSQLbXA",  # Veritasium
    "UCsXVk37bltHxD1rDPwtNM8Q",  # Kurzgesagt – In a Nutshell
    "UC6nSFpj9HTCZ5t-N3Rm3-HA",  # Vsauce
    "UCJ0-OtVpF0wOKEqT2Z1HEtA",  # ElectroBOOM
    "UCimiUgDLbi6P17BdaCZpVbg",  # SciShow
    "UC7_gcs09iThXybpVgjHZ_7g",  # PBS Space Time
    "UCHnyfMqiRRG1u-2MsSQLbXA",  # Veritasium
    "UCYO_jab_esuFRV4b17AJtAw",  # 3Blue1Brown
    "UCEIwxahdLz7bap-VDs9h35A"   # Steve Mould
]

def search_youtube_videos(query, max_videos=3):
    """Search for YouTube videos with intelligent quota management"""
    youtube_results = []
    
    try:
        print(f"🎥 Searching YouTube for: {query[:50]}...")
        
        # Check quota before starting
        quota_status = cse.get_quota_status()
        if quota_status['remaining'] < 2:  # Need at least 2 requests for YouTube search
            print(f"⚠️ Insufficient quota remaining ({quota_status['remaining']}) for YouTube search")
            return []
        
        # Single optimized YouTube search strategy
        youtube_query = f"site:youtube.com {query} tutorial OR explained OR guide"
        
        try:
            print(f"🔍 YouTube search: {youtube_query}")
            strategy_results = cse.cse(youtube_query, 1, CONFIG['google_cse_api'], CONFIG['engine_id'])
            
            if not strategy_results:
                print("📹 No YouTube results found")
                return []
            
            print(f"✅ Found {len(strategy_results)} potential YouTube videos")
            
            # Process results efficiently
            for idx, (title, link) in strategy_results.items():
                if len(youtube_results) >= max_videos:
                    break
                    
                if 'youtube.com/watch' in link or 'youtu.be/' in link:
                    try:
                        # Extract video ID
                        video_id = None
                        if 'v=' in link:
                            video_id = link.split('v=')[1].split('&')[0]
                        elif 'youtu.be/' in link:
                            video_id = link.split('youtu.be/')[1].split('?')[0]
                        
                        if video_id and len(video_id) == 11:  # YouTube video IDs are 11 characters
                            # Clean title
                            clean_title = title.replace(" - YouTube", "").strip()
                            if len(clean_title) > 100:
                                clean_title = clean_title[:97] + "..."
                            
                            youtube_results.append({
                                'title': clean_title,
                                'url': f"https://www.youtube.com/watch?v={video_id}",
                                'video_id': video_id,
                                'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                            })
                            
                    except Exception as e:
                        print(f"⚠️ Error processing video: {e}")
                        continue
            
            print(f"🎥 Successfully processed {len(youtube_results)} YouTube videos")
            return youtube_results
            
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"⏳ YouTube search stopped due to quota/rate limits")
                return []
            else:
                print(f"⚠️ YouTube search failed: {e}")
                return []
        
    except Exception as e:
        print(f"❌ YouTube search error: {e}")
        return []

def process_query(user_query):
    """Enhanced process_query with quota protection"""
    result = {
        'original_query': user_query,
        'status': 'processing',
        'results': [],
        'error': None,
        'stats': {},
        'quota_exceeded': False
    }
    
    try:
        # Step 1: Optimize query
        optimized_query, explanation, search_intent = search_query.build_search_query(
            user_query, groq_client
        )
        
        result.update({
            'optimized_query': optimized_query,
            'explanation': explanation,
            'search_intent': search_intent
        })
        
        # Step 2: Check quota before searching
        quota_status = cse.get_quota_status()
        if quota_status['remaining'] < 1:
            result['quota_exceeded'] = True
            result['error'] = f"Daily API quota exceeded ({quota_status['daily_limit']} requests/day). Resets tomorrow."
            result['youtube_videos'] = []
            result['quota_status'] = quota_status
            return result
        
        # Step 3: Search with enhanced error handling
        try:
            search_results = cse.cse(optimized_query, CONFIG['num_pages'], 
                                   CONFIG['google_cse_api'], CONFIG['engine_id'])
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                result['quota_exceeded'] = True
                result['error'] = "API quota exceeded or rate limited. Please try again later."
                result['youtube_videos'] = []
                result['quota_status'] = cse.get_quota_status()
                return result
            raise e
        
        if not search_results:
            result['error'] = "No search results found"
            return result
        
        # Step 3: Process results sequentially
        processed_results = []
        max_results = min(3, len(search_results))  # Process top 3 results for efficiency
        
        print(f"📄 Processing top {max_results} results...")
        
        for idx, (title, link) in list(search_results.items())[:max_results]:
            result_num = len(processed_results) + 1
            print(f"--- Processing Result {result_num}/{max_results} ---")
            print(f"Title: {title}")
            print(f"URL: {link}")
            
            try:
                # Fetch content
                print("📥 Fetching content...")
                content = utils.fetch_page_content(link)
                
                if content and len(content.split()) > 50:
                    word_count = len(content.split())
                    print(f"✅ Content fetched: {word_count} words")
                    
                    # Summarize content
                    print("🔄 Summarizing...")
                    try:
                        if word_count > 2000:
                            # Use chunked summarization for large content
                            summary_list = summarize_page_content.summary(content, 2, groq_client)
                            summary_result = summarize_page_content.summarize_html_content(
                                ' '.join(summary_list), groq_client
                            )
                        else:
                            # Direct summarization for smaller content
                            summary_result = summarize_page_content.summarize_html_content(
                                content, groq_client
                            )
                        
                        # Add to processed results
                        processed_results.append({
                            'title': title,
                            'url': link,
                            'content': content[:500] + "..." if len(content) > 500 else content,  # Truncate for response
                            'word_count': word_count,
                            'summary': summary_result
                        })
                        print(f"✅ Summarization completed")
                        
                    except Exception as summary_error:
                        print(f"⚠️ Summarization failed: {summary_error}")
                        # Add without summary if summarization fails
                        processed_results.append({
                            'title': title,
                            'url': link,
                            'content': content[:500] + "..." if len(content) > 500 else content,
                            'word_count': word_count,
                            'summary': {'error': str(summary_error)}
                        })
                        
                else:
                    print("❌ Content too short or failed to fetch")
                    continue
                    
            except Exception as e:
                print(f"❌ Error processing result: {e}")
                continue
        
        print(f"✅ Successfully processed {len(processed_results)} results")
        
        result['results'] = processed_results
        result['stats'] = {
            'search_results_found': len(search_results),
            'results_processed': len(processed_results),
            'total_word_count': sum(r['word_count'] for r in processed_results)
        }
        
        # Step 4: YouTube search (only if main results exist and quota available)
        if processed_results and not result.get('quota_exceeded'):
            try:
                print("🎥 Searching for related YouTube videos...")
                youtube_videos = search_youtube_videos(user_query, max_videos=3)  # Reduced number
                result['youtube_videos'] = youtube_videos
                result['stats']['youtube_videos_found'] = len(youtube_videos)
                
                if youtube_videos:
                    print(f"✅ Found {len(youtube_videos)} YouTube videos")
                else:
                    print("📹 No YouTube videos found")
                    
            except Exception as e:
                print(f"❌ YouTube search failed: {e}")
                result['youtube_videos'] = []
                result['stats']['youtube_videos_found'] = 0
        else:
            result['youtube_videos'] = []
            result['stats']['youtube_videos_found'] = 0
        
        result['status'] = 'completed'
        
    except Exception as e:
        result['error'] = str(e)
        result['status'] = 'error'
    
    return result

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """Process search request"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    if len(query) > 500:
        return jsonify({'error': 'Query too long (max 500 characters)'}), 400
    
    # Generate session ID for tracking
    session_id = str(uuid.uuid4())
    session['current_search'] = session_id
    
    try:
        result = process_query(query)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'services': {
            'groq_api': bool(os.getenv("GROQ_API_KEY")),
            'google_cse_api': bool(os.getenv("GOOGLE_CUSTOM_SEARCH_JSON_API_KEY")),
            'search_engine_id': bool(os.getenv("SEARCH_ENGINE_ID"))
        }
    })

@app.route('/quota')
def quota():
    """Get current API quota status"""
    try:
        quota_status = cse.get_quota_status()
        return jsonify({
            'status': 'success',
            'quota': quota_status,
            'can_search': quota_status['remaining'] > 0
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Check required environment variables
    required_vars = ['GROQ_API_KEY', 'GOOGLE_CUSTOM_SEARCH_JSON_API_KEY', 'SEARCH_ENGINE_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        exit(1)
    
    print("🚀 Starting AI Workflow Automation Web App...")
    print("📱 Open your browser to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
