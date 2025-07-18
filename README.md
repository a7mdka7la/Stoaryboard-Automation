# AI Workflow Automation - Web App

A simple web interface for the AI Workflow Automation system that allows non-developers to easily search and analyze scientific content.

## Features

🔍 **Smart Search** - AI-optimized queries for better results  
📄 **PDF Processing** - Extracts content from scientific PDFs  
🤖 **AI Summarization** - Intelligent content analysis  
🌐 **Clean Web Interface** - Easy-to-use for non-developers  
📊 **Real-time Results** - See progress and statistics  

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
Make sure your `.env` file contains:
```env
GOOGLE_CUSTOM_SEARCH_JSON_API_KEY=your_api_key_here
SEARCH_ENGINE_ID=your_search_engine_id_here
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run the Web App
```bash
python app.py
```

### 4. Open Your Browser
Go to: **http://localhost:5000**

## Usage

1. **Enter your research question** in the search box
2. **Click Search** or press Enter
3. **Wait for results** - the system will:
   - Optimize your query using AI
   - Search scientific sources (.edu, .gov, .org)
   - Extract content from PDFs and web pages
   - Generate intelligent summaries
4. **Review the results** with structured summaries including:
   - Brief descriptions
   - Key findings
   - Actionable insights

## Example Queries

- "Determine soluble oxygen in water"
- "Machine learning algorithms for natural language processing" 
- "Climate change impact on ocean pH levels"
- "Renewable energy storage solutions"
- "Artificial intelligence in medical diagnosis"

## Project Structure

```
AI-Workflow-Automation/
├── app.py                 # Flask web application
├── templates/
│   └── index.html        # Web interface
├── src/                  # Core processing modules
│   ├── search_query.py   # AI query optimization
│   ├── cse.py           # Google Custom Search
│   ├── utils.py         # Content processing
│   └── summarize_page_content.py  # AI summarization
├── .env                 # Environment variables
└── requirements.txt     # Python dependencies
```

## API Endpoints

- `GET /` - Main web interface
- `POST /search` - Process search requests
- `GET /health` - Health check

## Troubleshooting

**Rate Limits**: If you get rate limit errors, wait a few minutes before trying again.

**No Results**: Check that your API keys are valid and APIs are enabled in Google Cloud Console.

**PDF Issues**: Some PDFs may not be accessible due to website restrictions.

## Command Line Version

You can still use the original command-line version:
```bash
python src/main.py
```