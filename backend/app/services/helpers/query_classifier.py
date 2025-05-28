"""
Query Classification Helper

This module provides functions to classify user queries as general or case-specific.
"""
import re
from typing import Dict, Any, Tuple

# Keywords that suggest case-specific queries
CASE_SPECIFIC_KEYWORDS = [
    "case", "cases", "ruling", "rulings", "decision", "decisions", 
    "precedent", "precedents", "judgment", "judgments", "verdict", 
    "verdicts", "court", "courts", "judge", "judges", "tribunal",
    "find similar", "similar cases", "relevant cases", "find cases",
    "example cases", "show me cases", "search for cases", "what cases",
    "recent cases", "specific cases"
]

# Keywords that suggest general legal information queries
GENERAL_KEYWORDS = [
    "what is", "how to", "explain", "definition", "define", "meaning",
    "process", "procedure", "guidelines", "steps", "requirements",
    "overview", "summary", "introduction", "basics", "fundamental",
    "principles", "concept", "theory", "framework", "structure", 
    "approach", "strategy", "advice", "help", "guidance", "tips"
]

def classify_query(query: str) -> Tuple[str, float]:
    """
    Classify a query as either case-specific or general.
    
    Args:
        query: The user query string
        
    Returns:
        Tuple containing:
            - Classification ("case_specific" or "general")
            - Confidence score (0-1)
    """
    query = query.lower()
    
    # Count occurrences of keywords
    case_specific_count = sum(1 for keyword in CASE_SPECIFIC_KEYWORDS if keyword.lower() in query)
    general_count = sum(1 for keyword in GENERAL_KEYWORDS if keyword.lower() in query)
    
    # Check for explicit case-specific patterns
    case_specific_patterns = [
        r"(find|show|give|provide).*case",  # "find me a case"
        r"(previous|prior|past|similar).*case",  # "similar cases to"
        r"case.*(about|related to|involving|concerning)",  # "cases about X"
        r"(example|instance).*(of|where)",  # "examples where"
        r"v\.",  # Case citation pattern (Smith v. Jones)
        r"\[\d{4}\]",  # Year citation pattern [2023]
        r"\d{4}.*WASAT",  # Citation pattern 2023 WASAT
    ]
    
    # Check for explicit general question patterns
    general_patterns = [
        r"(what|how|why|when|where|who).*(is|are|do|does|should|would|could|can)",  # WH-questions
        r"explain.*(how|why|what)",  # "explain how to"
        r"(meaning|definition).*of",  # "meaning of X"
        r"(steps|process|procedure).*(for|to|in)",  # "steps to follow"
    ]
    
    # Count pattern matches
    case_pattern_matches = sum(1 for pattern in case_specific_patterns if re.search(pattern, query))
    general_pattern_matches = sum(1 for pattern in general_patterns if re.search(pattern, query))
    
    # Calculate total scores
    case_specific_score = case_specific_count + (case_pattern_matches * 2)  # Weight patterns more heavily
    general_score = general_count + (general_pattern_matches * 2)
    
    # If both scores are 0, default to general with low confidence
    if case_specific_score == 0 and general_score == 0:
        return "general", 0.5
    
    # Calculate confidence based on differential
    total = case_specific_score + general_score
    confidence = abs(case_specific_score - general_score) / total if total > 0 else 0.5
    confidence = min(0.95, max(0.5, confidence))  # Bound confidence between 0.5 and 0.95
    
    # Determine classification
    if case_specific_score >= general_score:
        return "case_specific", confidence
    else:
        return "general", confidence

def get_hybrid_response_template(query_type: str) -> Dict[str, str]:
    """
    Get response templates for hybrid approach based on query type.
    
    Args:
        query_type: Either "case_specific" or "general"
        
    Returns:
        Dict containing response template modifications
    """
    if query_type == "case_specific":
        return {
            "instruction": """
Your response should prioritize specific case details first:
1. Start with the most relevant cases that directly address the query
2. For each case, provide detailed analysis of the relevant facts, reasoning, and outcome
3. After presenting the cases, provide general legal information that helps understand the context
4. Ensure all case citations are accurate and include URLs where available
5. Structure the response with cases first, then general information
""",
            "format_template": """
## Relevant Cases for [Query Topic]
Brief introduction focusing on why these specific cases are relevant.

### Case 1: [**Smith v. Jones**](https://example.com/case1) (2023 WASAT 123)
* **Summary:** Details of this specific case and its relevance to the query
* **Key Points:**
* Specifics of this case's facts and reasoning
* How this case directly addresses the query
* Outcome and implications

### Case 2: [**Adams v. Miller**](https://example.com/case2) (2022 WASAT 456)
* **Summary:** Details of this specific case and why it's relevant
* **Key Points:**
* Specific facts and reasoning from this case
* Directly relevant findings

## General Legal Information
Now that we've examined the specific cases, here's some general context:
* General explanation of the legal principles involved
* Broader context for understanding these types of cases
"""
        }
    else:  # general query
        return {
            "instruction": """
Your response should prioritize general legal information first:
1. Start with a clear explanation of the general legal concepts, principles, or processes
2. Provide comprehensive information about the legal topic without focusing on specific cases
3. After explaining the general information, cite a few relevant cases as examples
4. Use the cases to illustrate how the general principles are applied in practice
5. Structure the response with general information first, then supporting cases
6. Ensure consistent spacing - do not add more than one blank line between any elements
""",
            "format_template": """
## [Legal Topic] Explained
Comprehensive explanation of the general legal concept, principle, or process that addresses the query directly.

* Detailed information about how this works in the legal system
* Clear explanation of legal requirements and considerations
* Practical information for understanding the topic

## Relevant Case Examples
Here are some cases that illustrate these principles:

### Case 1: [**Smith v. Jones**](https://example.com/case1) (2023 WASAT 123)
* **Summary:** Brief overview focused on how this case illustrates the general principle
* **Key Points:**
* How this case demonstrates the application of the legal principles
* Key findings relevant to the general topic

### Case 2: [**Adams v. Miller**](https://example.com/case2) (2022 WASAT 456)
* **Summary:** Another example showing how courts have applied these principles
* **Key Points:**
* Specific aspects that reinforce the general information
* Outcome that demonstrates the principles in action
"""
        }
    
def generate_hybrid_prompt(query: str, context: str) -> Dict[str, Any]:
    """
    Generate a hybrid prompt based on query classification.
    
    Args:
        query: The user query
        context: The retrieved context
        
    Returns:
        Dict with prompt components and metadata
    """
    query_type, confidence = classify_query(query)
    template_data = get_hybrid_response_template(query_type)
    
    # Get the base template with added hybrid instructions
    template = """
You are a helpful legal assistant that helps lawyers find and understand relevant cases.

USER QUERY: {query}

RELEVANT CASES:
{context}

{hybrid_instruction}

Based on the above relevant cases, provide a comprehensive and accurate response to the user's query. 
If the provided cases are not relevant to the query or if there's not enough information, say so clearly - 
DO NOT make up information or hallucinate content that isn't supported by the retrieved cases.

Your response should:
1. Be directly relevant to the query
2. Cite specific cases and their relevant parts when appropriate
3. Maintain legal accuracy
4. Use professional legal language
5. Format your response using extremely compact markdown following these EXACT SPACING rules:
   - Use headings (##, ###) to structure your response
   - Place EXACTLY ONE blank line after each section
   - Each case should start with "### Case N: [**Title**](case_url) (Citation_Number)" format
   - Make both the case title and citation number clickable with the same URL
   - Place EXACTLY ONE blank line between sections
   - For bullet points: NO blank lines between list items
   - For bullet points: ONE blank line after the last bullet point before new content
   - NEVER use more than one consecutive blank line anywhere
   - ALL case names and citation numbers should be clickable links to the case URL

6. Structure your response following this approach:
{format_template}

CRITICAL: You MUST use the exact case URLs provided in the context to create the markdown links. Make both the case title and citation number clickable links to the same case URL.

CRITICAL: Pay very close attention to spacing. Do not add multiple blank lines between paragraphs or list items. Use exactly one blank line between paragraphs or sections.
"""
    
    return {
        "prompt": template.format(
            query=query, 
            context=context,
            hybrid_instruction=template_data["instruction"],
            format_template=template_data["format_template"]
        ),
        "classification": {
            "type": query_type,
            "confidence": confidence
        }
    }
