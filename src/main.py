import os
import groq
import dotenv
import search_query, cse, utils, summarize_page_content
# Remove parallel processing imports - use sequential instead

# Access the Environment Variables
dotenv.load_dotenv()

# Load the environment variables
engine_id = os.getenv("SEARCH_ENGINE_ID") # search engines id
google_cse_api = os.getenv("GOOGLE_CUSTOM_SEARCH_JSON_API_KEY") # google custom search api key
groq_api_key = os.getenv("GROQ_API_KEY")

# Define the Groq client instance
groq_client = groq.Groq(api_key=groq_api_key)

# Define the search query
user_defined_query = "Determine soluble oxygen in water" # to be replaced later with message form slack

print("=== AI WORKFLOW AUTOMATION ===")
print(f"Processing query: {user_defined_query}")

# Use llama-3.3-70b-versatile model to optimize the search query for the engine using groq api
# Input: user raw query and groq client object
# Output: optimized_query -> enhanced version of the user query with type str,
# explanation -> short explanation of what the model does for the logs
try:
    optimized_query, explanation, search_intent = search_query.build_search_query(user_defined_query, groq_client)
    print(f"\n✅ Query Optimization Successful:")
    print(f"Original query: {user_defined_query}")
    print(f"Optimized query: {optimized_query}")
    print(f"Search intent: {search_intent}")
    print(f"Explanation: {explanation}")
except Exception as e:
    print(f"❌ Query optimization failed: {e}")
    optimized_query = "dissolved oxygen water measurement site:edu OR site:gov"
    print(f"Using fallback query: {optimized_query}")

# Sequential Processing (No Parallel Processing)
print(f"\n--- Sequential Search & Content Processing ---")

try:
    # Step 1: Get search results using CSE
    print("🔍 Searching...")
    search_results = cse.cse(optimized_query, 2, google_cse_api, engine_id)
    
    if not search_results:
        print("❌ No search results found. Check API credentials.")
        exit(1)
    
    print(f"✅ Found {len(search_results)} search results")
    
    # Step 2: Process results sequentially (top 3 for efficiency)
    processed_results = []
    max_results = 3
    
    print(f"\n📄 Processing top {max_results} results sequentially...")
    
    for idx, (title, link) in list(search_results.items())[:max_results]:
        result_num = len(processed_results) + 1
        print(f"\n--- Processing Result {result_num}/{max_results} ---")
        print(f"Title: {title}")
        print(f"URL: {link}")
        
        try:
            # Fetch content sequentially (no async/parallel processing)
            print("📥 Fetching content...")
            content = utils.fetch_page_content(link)
            
            if content and len(content.split()) > 50:
                word_count = len(content.split())
                print(f"✅ Content fetched: {word_count} words")
                
                # Add to processed results
                processed_results.append({
                    'title': title,
                    'url': link,
                    'content': content,
                    'word_count': word_count
                })
                
            else:
                print("❌ Content too short or failed to fetch")
                continue
                
        except Exception as e:
            print(f"❌ Error fetching content: {e}")
            continue
    
    print(f"\n✅ Successfully processed {len(processed_results)} results")
    
    # Step 3: Summarize content sequentially
    if processed_results:
        print(f"\n🤖 Generating summaries...")
        
        for i, result in enumerate(processed_results, 1):
            print(f"\n{'='*20} RESULT {i} {'='*20}")
            print(f"Title: {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Word count: {result['word_count']}")
            
            try:
                print("🔄 Summarizing...")
                
                # Choose summarization strategy based on content length
                if result['word_count'] > 2000:
                    # Use chunked summarization for large content
                    print("📊 Using chunked summarization for large content...")
                    summary_list = summarize_page_content.summary(
                        result['content'], 2, groq_client
                    )
                    final_summary = summarize_page_content.summarize_html_content(
                        ' '.join(summary_list), groq_client
                    )
                else:
                    # Direct summarization for smaller content
                    final_summary = summarize_page_content.summarize_html_content(
                        result['content'], groq_client
                    )
                
                print(f"\n📝 SUMMARY:")
                if isinstance(final_summary, dict):
                    if 'error' in final_summary:
                        print(f"❌ Summarization error: {final_summary}")
                    else:
                        print(f"📋 Brief Description: {final_summary.get('brief_description', 'N/A')}")
                        print(f"📄 Summary: {final_summary.get('concise_summary', 'N/A')}")
                        
                        key_findings = final_summary.get('key_findings', [])
                        if key_findings:
                            print(f"🔍 Key Findings:")
                            for j, finding in enumerate(key_findings, 1):
                                print(f"   {j}. {finding}")
                        
                        insights = final_summary.get('actionable_insights', [])
                        if insights:
                            print(f"💡 Actionable Insights:")
                            for j, insight in enumerate(insights, 1):
                                print(f"   {j}. {insight}")
                else:
                    print(f"Summary: {final_summary}")
                    
            except Exception as e:
                print(f"❌ Error summarizing: {e}")
            
            print("=" * 60)
        
        print(f"\n🎉 Processing completed successfully!")
        print(f"📊 Statistics:")
        print(f"   - Search results found: {len(search_results)}")
        print(f"   - Results processed: {len(processed_results)}")
        print(f"   - Total word count: {sum(r['word_count'] for r in processed_results)}")
        
    else:
        print("❌ No content was successfully processed")
        
except Exception as e:
    print(f"❌ Error in main processing: {e}")
    print("\nTrying with simplified approach...")
    
    # Fallback with mock data for testing
    print("\n--- Testing with Mock Data ---")
    mock_content = """
    Dissolved oxygen (DO) is a measure of how much oxygen is dissolved in the water. 
    It is an important parameter in assessing water quality because of its influence on the organisms living within a body of water. 
    Methods for measuring dissolved oxygen include the Winkler method, electrochemical probes, and optical sensors. 
    The Winkler method involves titration to determine the amount of dissolved oxygen. 
    Electrochemical probes use sensors that measure oxygen concentration directly. 
    Temperature and pressure affect oxygen solubility in water significantly.
    """
    
    try:
        print("🔄 Testing summarization with mock content...")
        test_summary = summarize_page_content.summarize_html_content(mock_content, groq_client)
        print(f"✅ Test summary: {test_summary}")
    except Exception as summary_error:
        print(f"❌ Summarization test failed: {summary_error}")

print(f"\n🏁 AI Workflow Automation Complete!")