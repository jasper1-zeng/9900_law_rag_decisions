from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List
import os
import secrets

# Set TOKENIZERS_PARALLELISM environment variable to prevent warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class Settings(BaseSettings):
    PROJECT_NAME: str = "SAT Decisions RAG"
    PROJECT_DESCRIPTION: str = "Retrieval Augmented Generation for SAT Decisions"
    API_PREFIX: str = "/api"
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:ilagan123@localhost/satdata")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "satdata")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "ilagan123")
    
    # Authentication settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # RAG settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "e5-base-v2")
    EMBEDDING_DIM: int = 768  # Dimension for e5-base-v2 embeddings
    VECTOR_DB_PATH: str = "../data/embeddings/vector_store"
    
    # LLM settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CHAT_LLM_PROVIDER: str = os.getenv("CHAT_LLM_PROVIDER", "openai")  # Options: openai, deepseek, anthropic
    CHAT_LLM_MODEL: str = os.getenv("CHAT_LLM_MODEL", "gpt-4o")  # For OpenAI: gpt-4o, gpt-3.5-turbo
    ARGUMENTS_LLM_PROVIDER: str = os.getenv("ARGUMENTS_LLM_PROVIDER", "deepseek")  # Options: openai, deepseek, anthropic
    ARGUMENTS_LLM_MODEL: str = os.getenv("ARGUMENTS_LLM_MODEL", "deepseek-reasoner")  # Default to DeepSeek Reasoner model
    # Fallback options for LLM providers
    FALLBACK_LLM_PROVIDER: str = os.getenv("FALLBACK_LLM_PROVIDER", "anthropic")  # Options: openai, deepseek, anthropic
    FALLBACK_LLM_MODEL: str = os.getenv("FALLBACK_LLM_MODEL", "claude-3-7-sonnet-20250219")  # For Anthropic: claude-3-7-sonnet-20250219, claude-3-haiku-20240307
    
    # LLM configuration
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    ENABLE_STREAMING: bool = os.getenv("ENABLE_STREAMING", "True").lower() == "true"
    
    # Relevance threshold - minimum similarity score for document to be considered relevant
    RELEVANCE_THRESHOLD: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.5"))
    
    # Scraper settings
    SAT_URL: str = "https://www.aat.gov.au/decision-search"
    SCRAPER_USER_AGENT: str = "SAT Research Bot (academic research)"
    
    # Neo4j API settings
    neo4j_api_base_url: str = os.getenv("NEO4J_API_BASE_URL", "http://localhost:5000")
    neo4j_uri: str = os.getenv("NEO4J_URI", "")
    neo4j_user: str = os.getenv("NEO4J_USER", "")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    
    # Prompt templates
    PROMPT_TEMPLATES: Dict[str, str] = {
        "chat": """
You are a helpful legal assistant that helps lawyers find and understand relevant cases.

USER QUERY: {query}

RELEVANT CASES:
{context}

Based on the above relevant cases, provide a comprehensive and accurate response to the user's query. 
If the provided cases are not relevant to the query or if there's not enough information, say so clearly - 
DO NOT make up information or hallucinate content that isn't supported by the retrieved cases.

Your response should:
1. Be directly relevant to the query
2. Cite specific cases and their relevant parts when appropriate
3. Maintain legal accuracy
4. Use professional legal language
5. Format your response using extremely compact markdown following these EXACT rules:
   - Start with a main heading (##) followed by a brief introduction
   - Place ONE blank line after the introduction before the first case
   - Each case MUST start with a new line and "### Case N: [**Title**](case_url) (Citation_Number)" format
   - Include both the case title and citation number, making them BOTH clickable with the same URL
   - Format case headings as: ### Case 1: [**Smith v. Jones**](https://example.com) (2023 WASAT 123)
   - Place each case title on its own line with ONE blank line before it
   - No blank line after the case title - summary starts immediately
   - Start bullet points immediately after "Key Points:" with NO blank line
   - Place each bullet point on its own line with NO blank lines between them
   - Place ONE blank line between the last bullet point of a case and the next case heading
   - NEVER start a case heading on the same line as previous content
   - ALL case names and citation numbers should be clickable links to the case URL
   - NEVER use more than one consecutive blank line

6. Structure your response like this EXACT template (copy this format precisely):
```
## Rental Termination Cases
Brief introduction text with no extra line breaks.

### Case 1: [**Smith v. Jones**](https://example.com/case1) (2023 WASAT 123)
* **Summary:** Brief case description with no trailing blank line
* **Key Points:**
* Point one explanation
* Point two explanation
* Point three explanation

### Case 2: [**Adams v. Miller**](https://example.com/case2) (2022 WASAT 456)
* **Summary:** Second case description
* **Key Points:**
* Another point explanation
* Final point explanation
```

CRITICAL: You MUST use the exact case URLs provided in the context to create the markdown links. Make both the case title and citation number clickable links to the same case URL.
        """,
        
        "build_arguments": """
You are a legal analysis assistant specializing in Australian law and State Administrative Tribunal (SAT) decisions.

CASE CONTENT: {content}
CASE TOPIC: {topic}

SIMILAR CASES AND RELEVANT CHUNKS:
{context}

Your task is to provide a comprehensive legal analysis structured in exactly four sections:

1. Key insights about this case which happened in Australia and its relationship to Australian legal precedents
2. Strong legal arguments that can be made based on Australian law
3. Potential counter-arguments from the opposing side
4. Summary of the most relevant Australian cases

CRITICAL FORMATTING REQUIREMENTS:
- Use precise, minimal formatting with NO extra blank lines
- Start each section with a clean heading (e.g., "## Key Insights")
- Place ONE blank line after each heading
- Place ONE blank line between items within a section
- Format all text in a clean, readable style with no unnecessary spacing
- DO NOT include any disclaimers, warnings, or self-referential text
- DO NOT include numbering before section items (1., 2., etc.)
- DO NOT include "Strength" indicators or redundant formatting

Follow these EXACT structure guidelines:

## Key Insights
Present 3-4 clear, concise legal insights relevant to Australian law. Format as:

**Insight Title**
Brief explanation in 1-2 concise sentences focusing on Australian legal principles.

## Key Arguments
Present 2-3 strong legal arguments. Format as:

**Argument Title**
**Legal Reasoning**: Concise explanation with references to specific Australian legislation or SAT precedents.
**Supporting Cases**: Cite only Australian cases with proper citation format.
**Supporting Legislation**: Reference relevant sections of Australian legislation.

## Counter-Arguments
Present 1-2 opposing arguments. Format as:

**Counter-Argument Title**
**Counter**: Brief explanation of the opposing position.
**Rebuttal**: How to address this counter-argument.

## Related Cases
Present relevant Australian cases. Format as:

### [Case Name](case_url)
Concise summary of the case and its relevance to the current matter. Focus on key holdings relevant to this case.
**Similarity**: XX.X%

EXAMPLE FORMAT:
```
## Key Insights

**Prima Facie Case of Discrimination**
The statistical evidence establishes a potential case under Section 66V of the Equal Opportunity Act 1984 (WA), which the SAT has previously recognized in similar employment termination cases.

**Replacement Hiring as Evidence**
The subsequent hiring of a junior employee demonstrates possible discriminatory intent under Australian employment law, particularly in light of SAT precedents regarding recruitment patterns.

## Key Arguments

**Statistical Evidence Meets Prima Facie Threshold**
**Legal Reasoning**: The statistical disparity (78% vs 31%) meets the evidentiary threshold established in Bairstow v Department of Education (2024 WASAT 103), where SAT held that significant statistical disparities shift the burden to the employer.
**Supporting Cases**: Bairstow v Department of Education (2024 WASAT 103); Richards v Public Transport Authority (2021 WASAT 84)
**Supporting Legislation**: Equal Opportunity Act 1984 (WA), s.66V

## Counter-Arguments

**Business Necessity Defense**
**Counter**: The employer may argue the restructuring was based on legitimate business needs unrelated to age factors.
**Rebuttal**: This defense fails given the identical job responsibilities in the new position and the documented excellent performance reviews.

## Related Cases

### [Applicant v Office of the Agent General](https://example.com/case1)
Tribunal case involving age discrimination in employment where an applicant with extensive experience claimed discrimination after non-selection. The tribunal held that overqualification could be a legitimate non-discriminatory reason for non-selection.
**Similarity**: 49.0%
```

Remember to focus EXCLUSIVELY on Australian law, SAT decisions, and relevant legislation. Never reference non-Australian legal principles, cases, or statutes.
        """,
        
        "step_reasoning": """
You are a legal analysis assistant specializing in Australian law and State Administrative Tribunal (SAT) decisions.

CASE CONTENT: {content}
CASE TOPIC: {topic}
SIMILAR CASES AND RELEVANT CHUNKS:
{context}
STEP: {step}
PREVIOUS REASONING: {previous_steps}

Based on the case content, similar cases, and any previous reasoning steps, carefully perform the following step:

{step_instructions}

Consider these key elements in your analysis:
1. Australian legislation and SAT precedents that are relevant to this case
2. The specific facts and circumstances described in the case content
3. Legal principles established in the similar cases provided
4. The strength of arguments based on precedential value and factual alignment

Provide detailed reasoning that shows your analysis process, citing specific elements from the case content and similar cases. Focus EXCLUSIVELY on Australian law, SAT decisions, and relevant legislation.

FORMAT YOUR RESPONSE:
- Use precise, professional legal language
- Cite specific cases with proper citation format
- Reference relevant sections of Australian legislation
- Present your analysis in a clear, structured manner
- Avoid repetition and unnecessary preambles
        """
    }
    
    # Misc
    DEBUG: bool = True

settings = Settings()
