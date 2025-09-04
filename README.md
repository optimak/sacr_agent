# AI Agent for Cybersecurity Blog Knowledge Base

This is an autonomous AI agent that scrapes, extracts, stores, and queries cybersecurity blog data. Its purpose is to mirror SACR's real-world workflow by autonomously scraping data from cybersecurity blogs (Okta, CrowdStrike, Palo Alto Networks, Mandiant), storing it in a Notion database, and enabling natural language queries through a RAG pipeline.

## Live Demo & Links

* **Live Demo:** [https://sacr-frontend.onrender.com/](https://sacr-frontend.onrender.com/)
* **Backend API:** [https://sacr-backend.onrender.com/](https://sacr-backend.onrender.com/)
* **GitHub Repo:** [https://github.com/optimak/sacr_agent/](https://github.com/optimak/sacr_agent/)
* **Public Notion Database:** [https://www.notion.so/26434546e54081ff84d3d715357d6398](https://www.notion.so/26434546e54081ff84d3d715357d6398?v=26434546e54081af9aad000c33d4f783&source=copy_link)

---

## Architecture & Workflow

This system consists of four main components working together to create an intelligent cybersecurity knowledge base:

### System Components

1. **Data Ingestion Pipeline** - Web scrapers that extract content from cybersecurity blogs
2. **Notion Database** - Centralized storage for all scraped content with structured metadata
3. **RAG Agent** - Processes Notion content with OCR, chunking, and embedding generation
4. **Query Interface** - Streamlit frontend with FastAPI backend for natural language queries

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

## Technologies Used

### Technologies
* **Web Scraping:** BeautifulSoup4, Requests, HTTPx
* **RAG Pipeline:** Azure OpenAI, Azure AI Search, NLTK, Tiktoken
* **Notion Integration:** Notion Client SDK
* **Frontend:** Streamlit
* **Backend:** FastAPI, Uvicorn
* **Deployment:** Render (Docker containers)
* **AI Models:** Azure OpenAI text-embedding-3-small, GPT-4o

---

## Setup Instructions

### Prerequisites
* **Python 3.11+**
* **Docker and Docker Compose**
* **Notion Account**
* **Azure Account** with OpenAI, AI Search, and Prompt Flow services

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


### Environment Setup Guides

#### 1. Notion Setup
**Step-by-step guide:**

1. **Create Notion Account** (if you don't have one):
   - Go to [https://www.notion.so/](https://www.notion.so/)
   - Sign up for a free account

2. **Create Integration:**
   - Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
   - Click "New integration"
   - Give it a name (e.g., "SACR Agent")
   - Select your workspace
   - Click "Submit"
   - **Copy the "Internal Integration Token"** (starts with `secret_`)

3. **Create Database:**
   - In Notion, create a new page or use an existing one
   - Add a database with these properties:
     - Title (Title)
     - Company (Rich Text)
     - Date Published (Date)
     - Date Pulled (Date)
     - Webpage URL (URL)
     - Image URLs (Files)
     - Outbound Links (Rich Text)

4. **Share Database with Integration:**
   - Click "Share" on your database page
   - Click "Invite" and select your integration
   - Give it "Full access"

5. **Get Database ID:**
   - Copy the database ID from the URL: `https://notion.so/Database-Name-DATABASE_ID?v=...`
   - The ID is the long string after the last dash

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

### Query Performance Analysis

| # | Question | Your Answer | Expected Answer | Comment |
|---|----------|-------------|-----------------|---------|
| 1 | What capabilities does CrowdStrike Falcon Exposure Management unite in a single platform? | VM, ASM, CAASM integrated with continuous visibility, real-time risk prioritization, and automated remediation. | VM + ASM + CAASM unified for visibility, prioritization, remediation. | ✅ Strong — detailed and matches source exactly. |
| 2 | How does the platform help security teams prioritize risks based on adversary behavior? | Uses Threat Graph, Intel Graph, Asset Graph for single source of truth; risk prioritization algorithms aligned to adversary behavior. | Correlates risks across domains and prioritizes adversary-aligned threats. | ✅ Excellent depth — more detail than expected. |
| 3 | What key shift in approach is CrowdStrike advocating for securing AI infrastructure? | Advocates real-time, full-stack, unified security for AI attack surfaces (distributed infra, data, agents, SaaS). | Move from reactive tools → real-time, integrated AI security. | ✅ Comprehensive — shows awareness of AI-specific risks. |
| 4 | What recognition did Palo Alto Networks receive in Gartner's 2025 Magic Quadrant, and what qualities were highlighted? | Recognized as Leader; furthest for Completeness of Vision; noted for AI-powered unified protection across all environments. | Leader in 2025 Magic Quadrant; strong vision + execution. | ✅ Very strong — includes extra Gartner context. |
| 5 | What does a hybrid mesh firewall (HMF) refer to in this context? | Multi-deployment model (hardware, virtual, cloud), unified management, CI/CD integration, AI-driven threat prevention. | Unified firewall across hybrid envs, managed centrally. | ✅ Excellent — more detailed than required. |
| 6 | Who was the primary target and what technique was leveraged in the PRC-Nexus espionage campaign? | Diplomats in SE Asia; adversary-in-the-middle + social engineering; malware STATICPLUGIN + SOGU.SEC. | Diplomats in SE Asia; AiTM + malware delivery. | ✅ Very strong — includes malware names, adds precision. |
| 7 | What vulnerability category is discussed in the Sitecore blog, and what is its key characteristic? | ViewState deserialization (CVE-2025-53690); machine key exposure → RCE via malicious payloads. | ViewState deserialization vuln allowing RCE. | ✅ Excellent — precise CVE & root cause. |
| 8 | What types of identities does Okta ISPM help secure, and why are they particularly critical? | Human, non-human, and agentic identities; critical because they inherit powerful permissions (e.g., GitHub apps, AWS IAM). | Human + machine identities, especially high-privilege/service accounts. | ✅ Excellent — concrete examples add realism. |
| 9 | What is the fundamental challenge Okta emphasizes about AI agents and workload identities? | AI agents inherit risky permissions (privileged, unused, toxic combos), creating exploit risks; need comprehensive identity strategy. | Workload identity inheritance creates exploitable risks. | ✅ Very strong — precise, captures "toxic combos." |
| 10 | Across CrowdStrike and Palo Alto Networks, how are AI capabilities being integrated differently in securing cyber environments? | Only CrowdStrike AI info available (Falcon Cloud Security, Charlotte AI); Palo Alto AI details not in context. | CrowdStrike = AI-driven full-stack protection; Palo Alto = AI-enhanced HMF. | ⚠️ Incomplete — misses Palo Alto AI integration; needs extra retrieval. |

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
