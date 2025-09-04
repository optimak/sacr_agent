# AI Agent for Cybersecurity Blog Knowledge Base (Local Development)

This is the **development branch** for running the AI agent locally. It's an autonomous AI agent that scrapes, extracts, stores, and queries cybersecurity blog data using **ChromaDB** for local vector storage and **local Prompt Flow** for AI processing.

> **Note:** This is the development branch for local usage. The deployed version can be found in the [main branch](https://github.com/optimak/sacr_agent/tree/main).

## GitHub Repository

* **GitHub Repo:** [https://github.com/optimak/sacr_agent/](https://github.com/optimak/sacr_agent/)
* **Current Branch:** `development` (local ChromaDB setup)
* **Deployed Version:** Available in `main` branch

---

## Architecture & Workflow (Local Development)

This **local development version** uses ChromaDB for vector storage and local Prompt Flow for AI processing. The system consists of four main components:

### System Components

1. **Data Ingestion Pipeline** - Web scrapers that extract content from cybersecurity blogs
2. **Notion Database** - Centralized storage for all scraped content with structured metadata
3. **Local RAG Agent** - Processes Notion content with OCR, chunking, and ChromaDB vector storage
4. **Query Interface** - Streamlit frontend with FastAPI backend for natural language queries

### Local Development Features

- **ChromaDB**: Local vector database for fast similarity search
- **Local Prompt Flow**: AI workflows run locally without external dependencies
- **Real-time Status**: Frontend shows system health and readiness
- **One-Command Setup**: Single Docker command runs the entire pipeline

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CYBERSECURITY BLOG KNOWLEDGE BASE                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OKTA BLOG     │    │ CROWDSTRIKE     │    │ PALO ALTO       │    │   MANDIANT      │
│                 │    │     BLOG        │    │   NETWORKS      │    │     BLOG        │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │                      │
          └──────────────────────┼─────────────────────────────────────────────┘
                                 │                      
                    ┌────────────▼──────────────┐      
                    │     WEB SCRAPERS          │      
                    │  (BeautifulSoup + HTTPx)  │      
                    └─────────────┬─────────────┘      
                                  │                    
                    ┌─────────────▼─────────────┐      
                    │    NOTION DATABASE        │
                    │  (Structured Storage)     │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │      RAG PIPELINE         │
                    │  ┌─────────────────────┐  │
                    │  │   Image OCR         │  │
                    │  │   (GPT-4o Vision)   │  │
                    │  └─────────────────────┘  │
                    │  ┌─────────────────────┐  │
                    │  │   Text Chunking     │  │
                    │  │   (Semantic Split)  │  │
                    │  └─────────────────────┘  │
                    │  ┌─────────────────────┐  │
                    │  │  Embedding Gen      │  │
                    │  │  (Azure OpenAI)     │  │
                    │  └─────────────────────┘  │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   AZURE AI SEARCH         │
                    │  (Hybrid Search Index)    │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   AZURE PROMPT FLOW       │
                    │  (RAG Query Processing)   │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    FASTAPI BACKEND        │
                    │   (Query Endpoint)        │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   STREAMLIT FRONTEND      │
                    │   (User Interface)        │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     USER QUERIES          │
                    │  "What did Okta's latest  │
                    │   blog post focus on?"    │
                    └───────────────────────────┘
```



---

## Technologies Used (Local Development)

### Core Technologies
* **Web Scraping:** BeautifulSoup4, Requests, HTTPx
* **Vector Database:** ChromaDB (local storage)
* **RAG Pipeline:** Azure OpenAI, NLTK, Tiktoken
* **AI Processing:** Local Prompt Flow
* **Notion Integration:** Notion Client SDK
* **Frontend:** Streamlit with real-time status monitoring
* **Backend:** FastAPI, Uvicorn
* **Containerization:** Docker & Docker Compose
* **AI Models:** Azure OpenAI text-embedding-3-small, GPT-4o, GPT-4o-mini

---

## Setup Instructions

### Prerequisites
* **Docker and Docker Compose** (for local containerized setup)
* **Notion Account** (for data storage)
* **Azure OpenAI Account** (for AI models and embeddings)

### Quick Start with Docker (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/optimak/sacr_agent.git
   cd sacr_agent
   ```

2. **Set up environment variables:**
   Create a `.env` file in the root directory:
   ```bash
   # Notion Configuration
   NOTION_TOKEN=secret_xyz123...
   PARENT_PAGE_ID=your_parent_page_id
   DATABASE_ID=your_database_id
   
   # Azure OpenAI Configuration
   AZURE_OPENAI_KEY=your_azure_openai_key
   AZURE_ENDPOINT=https://your-resource.openai.azure.com/
   EMBEDDING_DEPLOYMENT=text-embedding-3-small
   GPT4O_DEPLOYMENT=gpt-4o
   
   # Azure AI Search Configuration
   AZURE_SEARCH_SERVICE_NAME=your_search_service
   AZURE_SEARCH_API_KEY=your_search_key
   INDEX_NAME=sacr-rag
   
   # Azure Prompt Flow Configuration
   PROMPTFLOW_ENDPOINT=https://your-promptflow-endpoint.azure.com/score
   PROMPTFLOW_KEY=your_promptflow_key
   
   # Port Configuration
   PORT=8501
   ```

3. **Run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Health Check: http://localhost:8000/health

## How to Use Locally

### Step 1: Get Your API Keys
You need these accounts and keys:
- **Notion**: Get your API token from [notion.so/my-integrations](https://notion.so/my-integrations)
- **Azure OpenAI**: Get your API key and endpoint from [Azure Portal](https://portal.azure.com)

### Step 2: Set Up Environment Variables
Create a `.env` file in the project folder with these variables:

```bash
# Notion (Required)
NOTION_TOKEN=secret_xyz123...
NOTION_DATABASE_NAME=CyberSecurity Database

# Azure OpenAI (Required)
AZURE_OPENAI_KEY=your_azure_openai_key
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
GPT4O_DEPLOYMENT=gpt-4o
GPT4O_MINI_DEPLOYMENT=gpt-4o-mini

# Local Setup (Required)
USE_LOCAL_VECTOR_DB=true
USE_PROMPTFLOW_LOCAL=true
ENABLE_IMAGE_OCR=true
```

### Step 3: Run the System
```bash
docker-compose up --build
```

Wait 2-3 minutes for everything to start up.

### Step 4: Use the App
1. Go to http://localhost:8501
2. Wait for "🚀 App: Ready!" status
3. Ask questions like:
   - "What is CrowdStrike Falcon?"
   - "How does Okta handle identity security?"
   - "What are the latest cybersecurity threats?"

### What Happens Automatically
1. **Data Scraping**: Downloads latest posts from cybersecurity blogs
2. **Processing**: Extracts text, images, and creates searchable chunks
3. **AI Setup**: Prepares the AI to answer your questions
4. **Ready**: Shows green status when everything is working

### Troubleshooting
- **"App: Starting..."**: Wait 2-3 minutes for full startup
- **"Backend: Offline"**: Check your `.env` file has correct API keys
- **No answers**: Make sure Azure OpenAI keys are valid

## Agent Workflow Details

### Local Development Workflow
1. **Data Scraping**: Downloads latest posts from cybersecurity blogs
2. **Notion Storage**: Stores content in your Notion database
3. **Processing**: Extracts text, runs OCR on images, creates chunks
4. **ChromaDB Indexing**: Stores embeddings in local vector database
5. **Query Processing**: Uses local Prompt Flow to answer questions
6. **Response Generation**: Returns answers with source citations

#### 2. Azure OpenAI Setup
**Complete setup guide:**

1. **Request Access:**
   - Go to [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
   - Click "Request access to Azure OpenAI Service"
   - Fill out the form and wait for approval (usually 1-2 business days)

2. **Create Azure OpenAI Resource:**
   - Go to [Azure Portal](https://portal.azure.com/)
   - Click "Create a resource"
   - Search for "Azure OpenAI"
   - Click "Create"
   - Fill in the required details:
     - Subscription: Your Azure subscription
     - Resource Group: Create new or use existing
     - Region: Choose a region that supports Azure OpenAI
     - Name: Choose a unique name
     - Pricing Tier: Standard S0 (recommended)

3. **Deploy Models:**
   - Go to your Azure OpenAI resource
   - Click "Go to Azure OpenAI Studio"
   - Click "Deployments" in the left menu
   - Click "Create new deployment"
   - Deploy these models:
     - **Model:** `text-embedding-3-small` (for embeddings)
     - **Model:** `gpt-4o` (for chat completions)
   - Use deployment names: `text-embedding-3-small` and `gpt-4o`

4. **Get API Key and Endpoint:**
   - In Azure Portal, go to your Azure OpenAI resource
   - Click "Keys and Endpoint" in the left menu
   - Copy "Key 1" (this is your `AZURE_OPENAI_KEY`)
   - Copy the "Endpoint" URL (this is your `AZURE_ENDPOINT`)

#### 3. Azure AI Search Setup
**Step-by-step guide:**

1. **Create Search Service:**
   - Go to [Azure Portal](https://portal.azure.com/)
   - Click "Create a resource"
   - Search for "Azure AI Search"
   - Click "Create"
   - Fill in the details:
     - Subscription: Your Azure subscription
     - Resource Group: Same as Azure OpenAI
     - Service Name: Choose a unique name (this becomes `AZURE_SEARCH_SERVICE_NAME`)
     - Location: Same region as Azure OpenAI
     - Pricing Tier: Basic (recommended for development)

2. **Get API Key:**
   - Go to your Azure AI Search service
   - Click "Keys" in the left menu
   - Copy "Primary admin key" (this is your `AZURE_SEARCH_API_KEY`)

3. **Verify Service:**
   - The RAG pipeline will automatically create the search index
   - No manual index creation needed

#### 4. Azure Prompt Flow Setup
**Setup guide:**

1. **Create Azure Machine Learning Workspace:**
   - Go to [Azure Portal](https://portal.azure.com/)
   - Click "Create a resource"
   - Search for "Machine Learning"
   - Click "Create"
   - Fill in the details:
     - Subscription: Your Azure subscription
     - Resource Group: Same as other services
     - Workspace Name: Choose a unique name
     - Region: Same region as other services

2. **Deploy Prompt Flow:**
   - Go to your Machine Learning workspace
   - Click "Launch studio" to open Azure ML Studio
   - In the left menu, click "Prompt flow"
   - Create a new flow or use the existing one
   - Configure the flow to use your Azure OpenAI deployments

3. **Get Endpoint Details:**
   - After deploying your flow, get the endpoint URL
   - This becomes your `PROMPTFLOW_ENDPOINT`
   - Get the API key from the deployment settings
   - This becomes your `PROMPTFLOW_KEY`


---

## Agent Workflow Details

### System Details
* **Web Scraping:** Extracts latest 5 posts from each cybersecurity blog with respectful delays
* **Notion Storage:** Structured database with title, company, dates, URLs, images, and links
* **RAG Pipeline:** OCR processing, semantic chunking, and embedding generation
* **Query Interface:** Natural language queries with source attribution

### Data Refresh & Orchestration
* **Manual Execution:** Currently requires manual execution of the scraping pipeline
* **Incremental Processing:** RAG pipeline only processes new/updated Notion pages on subsequent runs
* **Processing Tracker:** Maintains history of processed pages to avoid reprocessing
* **OCR Caching:** Caches OCR results to avoid reprocessing images
* **No Scheduled Refresh:** No automated scheduling - requires manual intervention for data updates

### Error Handling Strategy
* **Web Scraping Errors:**
  - Configurable request timeouts (default: 10 seconds)
  - Automatic retry with exponential backoff for network failures
  - Graceful handling of HTML parsing errors and missing content
  - Respectful delays between requests to avoid rate limiting

* **Notion API Errors:**
  - Pagination handling for large datasets
  - Batch processing to manage API rate limits
  - Duplicate detection to prevent re-processing existing content
  - Fallback handling for API quota exceeded scenarios

* **Azure Service Errors:**
  - Retry mechanisms for Azure OpenAI API calls
  - Fallback responses when services are unavailable
  - Comprehensive logging for debugging and monitoring
  - Graceful degradation when embedding generation fails

* **RAG Pipeline Errors:**
  - OCR failure handling with cached results
  - Chunking error recovery for malformed content
  - Vector embedding failure fallbacks
  - Search index update error handling

* **Frontend/Backend Errors:**
  - User-friendly error messages in Streamlit interface
  - Backend health checks and status monitoring
  - Request timeout handling in FastAPI
  - Graceful fallback when Prompt Flow is unavailable

---

## Sample Queries & Responses

Here are example queries that work with the Notion database:

### Sample Queries
* "What did Okta's most recent blog post focus on?"
* "Which company mentioned AI in their blog updates?"
* "What are the latest cybersecurity threats mentioned in the blogs?"
* "Show me articles about zero-day vulnerabilities."
* "What security tools were discussed in recent posts?"
* "Find articles with images showing attack patterns."
* "What security trends are emerging across all companies?"

---

## Challenges & Lessons Learned

### Key Challenges
* **Dynamic Content:** Different blog layouts requiring custom parsing logic
* **Rate Limiting:** Implemented respectful delays and retry mechanisms
* **Image Processing:** OCR for technical diagrams using GPT-4o vision
* **Azure Service Coordination:** Managing multiple Azure services and dependencies

### Difficulties Faced

#### Data Scraping
Experienced issues with scraping the source material, particularly because each blog had a different format. This made it difficult to automate the process.

#### Image Handling
* **Image Extraction:** Only relevant images are extracted and stored as image links during scraping
* **OCR Processing:** Used an OCR/Vision model (GPT-4o) to generate text descriptions for each image
* **Vector Embeddings:** Created vector embeddings of the image content for image-to-text queries
* **Inline Positioning:** Getting images to appear in-line with the text in Notion, exactly where they were on the original websites, was a major issue that consumed a significant amount of time

#### Agent Behavior
The agent's performance and behavior changed when the vector database grew with more information. Initially, with a smaller, more focused dataset (only Google blogs), images were more likely to be retrieved if the query was directly related. However, once the database was populated with a majority of text-based data, the likelihood of image retrieval became very low.

---

## Future Improvements

### Future Enhancements
* Add more cybersecurity sources
* Scheduled auto-refresh of data
* Multi-turn conversational memory
* Advanced filtering and search capabilities
* Implement caching for faster responses

### Future Plans

#### Prompt Engineering
Plan to focus on prompt engineering to improve and change the behavior of your agent. This is your primary goal to address the issues with image retrieval and agent performance as the database scales.

#### Front-End Development
Also plan to add more functionalities to the front-end of your application.

---

## API Documentation

### API Endpoints
* `GET /health` - Health check
* `POST /ask` - Query endpoint for natural language questions


---

## Acknowledgments

* **SACR** for the project design and requirements
* **Notion, Azure OpenAI, Azure AI Search** for their excellent APIs and services
* **Streamlit and FastAPI** for rapid development frameworks

---

## Support

For issues and questions:
1. Review the troubleshooting sections in component READMEs
2. Ensure all environment variables are properly configured
3. Verify Azure service deployments and permissions

**Note:** The live demo is already deployed at [https://sacr-frontend.onrender.com/](https://sacr-frontend.onrender.com/) and ready for testing!
