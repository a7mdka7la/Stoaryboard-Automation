import json
import time
import random

context_final_summary = \
"""
You are WebPage Insight Summarizer, an analytical writing assistant.
    • Audience: collage educated people from science school.
    • Voice: concise, neutral, and fact-focused.
    • Faithfulness: never invent facts—rely only on the supplied text.

**Task**
    1. **Brief Description** – In ≤100 words, describe what this web page is about and why it exists.
    2. **Concise Summary** – In 5-8 sentences, capture the main argument or storyline, preserving any numbers, trends, or named entities that matter.
    3. **Key Findings** – Bullet-list the 3-6 most important facts, statistics, or conclusions stated.
    4. **Actionable Insights / Implications** – Bullet-list up to 5 insights the reader can act on or reflect upon.

**Guidelines**
    - Pull only from the provided text; do **not** browse further.
    - Quote exact phrases sparingly and only when they carry distinctive meaning.
    - If content is extremely long (>2000 words), prioritise the latest data, outcomes, and novel ideas over generic background.
    - Omit boilerplate (cookies banners, navigation labels, ads, etc.).
    - Keep total output ≤500 words.

**Output Format**: Respond with valid JSON in this exact structure:
{
  "brief_description": "description text here",
  "concise_summary": "summary text here", 
  "key_findings": ["finding 1", "finding 2", "finding 3"],
  "actionable_insights": ["insight 1", "insight 2", "insight 3"]
}
"""

context_summary = \
"""
You are Lossless-Shrink-512, a professional text compressor.
	• Goal: rewrite the supplied text in ≤512 Llama tokens while preserving every explicit fact,
	  statistic, named entity, causal link, and chronological order.
	• Style: concise, information-dense, neutral tone. No added examples, no omissions, no paraphrase
	  that drops meaning. Remove redundancy, filler words, and editorial asides only.
	• Faithfulness: DO NOT invent or infer facts; rely strictly on the input.

USER
	Compress the following content.  The output **must not exceed 512 tokens**.  
	Keep all numbers, units, years, names, citations, and ordered steps intact.  
	Prefer short sentences; merge or collapse where safe.  Use bullet lists only if they increase
	clarity without adding tokens.  Return plain text—no markdown headings.

"""

# def _chunks(text:str, num_chunks:int) -> str:
# 	chunks = []	
# 	len_text = len(text)
# 	chunk_size = len_text // num_chunks
# 	for i in range(num_chunks):
# 		chunk = chunks.append(text[i*chunk_size: (chunk_size*i)+chunk_size])
# 	return chunks

def build_text(text:str, genrated_summaries:list ,num_chunks:int, chunk_num:int) -> str:
	chunk_size = len(text) // num_chunks
	processed_text = ""

	if chunk_num == 0:
		processed_text = text[:chunk_size]
	else:
		processed_text = " ".join(genrated_summaries) + " " + text[chunk_num*chunk_size::]
	return processed_text


def summary(text: str, num_chunks: int, client: object):
    summary_list = []
    
    for i in range(num_chunks):
        try:
            prompt = build_text(text, summary_list, num_chunks, i)
            
            # Add delay between chunks
            if i > 0:
                time.sleep(3)
            
            chat_completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Use faster model
                max_tokens=512,
                temperature=0,          
                top_p=1,        
                seed=42,          
                presence_penalty=0,
                frequency_penalty=0,
                messages=[
                    {"role": "system", "content": context_summary},
                    {"role": "user", "content": prompt[:3000]}
                ],
            )
            
            response = chat_completion.choices[0].message.content
            summary_list.append(response)
            
        except Exception as e:
            if "rate_limit" in str(e).lower():
                print(f"⏳ Rate limit on chunk {i+1}. Adding to list with error note...")
                summary_list.append(f"[Rate limit - chunk {i+1} skipped]")
            else:
                summary_list.append(f"[Error in chunk {i+1}: {str(e)[:50]}]")
    
    return summary_list


def summarize_html_content(page_content: str, client: object) -> str:
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            chat_completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Use faster model with higher limits
                temperature=0,          
                top_p=1,        
                seed=42,          
                presence_penalty=0,
                frequency_penalty=0,
                max_tokens=512,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": context_final_summary},
                    {"role": "user", "content": page_content[:3000]}  # Limit input size
                ],
            )
            
            response = json.loads(chat_completion.choices[0].message.content)
            return response
            
        except Exception as e:
            error_str = str(e)
            if "rate_limit_exceeded" in error_str or "429" in error_str:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(1, 3)
                    print(f"⏳ Rate limit hit. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    return {"error": "Rate limit exceeded after retries"}
            else:
                return {"error": str(e)}
    
    return {"error": "Max retries exceeded"}