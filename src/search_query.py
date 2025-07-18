import json
import re
from typing import Tuple, Optional
from functools import lru_cache  

# Enhanced context with more specific instructions
context = """
You are SearchQueryPro, an expert at turning natural-language questions into laser-focused Google Custom Search queries.

Your Input  
USER_QUERY: <the raw human question or statement>

Your Task  
Rewrite USER_QUERY into ONE optimized Boolean query string that:  

**Priority Operators (use when relevant):**
1. **Scientific/Technical content**: Add site:edu OR site:gov OR site:org for authoritative sources
2. **Recent info**: Add after:2020-01-01 for current information  
3. **Specific file types**: Add filetype:pdf for research papers, filetype:ppt for presentations
4. **Exact phrases**: Use "exact phrase" for technical terms, proper nouns, or specific concepts
5. **Exclude noise**: Use -site:pinterest.com -site:youtube.com -ads -shopping -buy

**Advanced Techniques:**
- Use intitle: for key concepts that should be in the title
- Use OR for synonyms: (oxygen OR O2) (dissolved OR soluble)
- Use parentheses for grouping: (measurement OR determination OR analysis)
- Remove stop words: the, a, an, is, are, how, what, etc.

**Quality Checks:**
- Keep total length ≤ 200 characters for optimal performance
- Prioritize scientific accuracy over broad results
- Include technical synonyms when relevant
- Focus on actionable, specific results

Output Format (MUST follow exactly as valid JSON):
{
  "optimized_query": "<your single-line query string>",
  "explanation": "<≤80-word rationale explaining your optimization strategy>",
  "search_intent": "<research|how-to|comparison|definition|current-data>"
}

**Important**: For identical inputs, produce identical outputs. Never invent facts. Always respond with valid JSON format.
"""

def build_search_query(original_query: str, client: object) -> Tuple[str, str, str]:
    """
    Build optimized search query with enhanced context
    
    Returns:
        Tuple of (optimized_query, explanation, search_intent)
    """
    try:
        chat_completion = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            temperature=0,          
            top_p=1,        
            seed=42,          
            presence_penalty=0,
            frequency_penalty=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": original_query} 
            ],
        )
        
        response = json.loads(chat_completion.choices[0].message.content)
        
        optimized_query = response.get("optimized_query", "")
        explanation = response.get("explanation", "Query optimization applied")
        search_intent = response.get("search_intent", "research")
        
        # Fallback validation
        if not optimized_query or len(optimized_query) > 250:
            optimized_query = _fallback_optimization(original_query)
            explanation = "Fallback optimization applied"
        
        return optimized_query, explanation, search_intent
        
    except Exception as e:
        print(f"Error in query optimization: {e}")
        fallback_query = _fallback_optimization(original_query)
        return fallback_query, f"Fallback due to error: {str(e)[:50]}", "research"

def _fallback_optimization(query: str) -> str:
    """Simple fallback optimization when AI fails"""
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'how', 'what', 'why', 'when', 'where'}
    
    words = query.lower().split()
    filtered_words = [word for word in words if word not in stop_words]
    
    # Add basic scientific site restriction for technical queries
    technical_keywords = {'determine', 'measure', 'analyze', 'calculate', 'method', 'procedure', 'technique'}
    if any(keyword in query.lower() for keyword in technical_keywords):
        filtered_words.extend(['site:edu', 'OR', 'site:gov'])
    
    return ' '.join(filtered_words)

@lru_cache(maxsize=100)
def cached_build_search_query(original_query: str, client_id: str) -> Tuple[str, str, str]:
    """Cached version for repeated queries (requires string client_id instead of object)"""
    # This would need client recreation, but shows the caching concept
    pass