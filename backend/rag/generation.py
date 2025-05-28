"""
RAG Generation Module

This module handles the generation of text responses based on retrieved documents.
"""
from typing import List, Dict, Any, Optional, Union, Callable
import logging
from app.config import settings
from rag.llm_providers import get_llm_provider
import time
import tiktoken

logger = logging.getLogger(__name__)

def format_context(documents: List[Dict[str, Any]]) -> str:
    """
    Format retrieved documents into a context string for the LLM.
    
    Args:
        documents: The retrieved documents
        
    Returns:
        str: The formatted context
    """
    if not documents:
        logger.warning("No documents were provided to format_context")
        return "No relevant documents found."
    
    # Log the first document to help debugging
    if len(documents) > 0:
        logger.info(f"First document keys: {list(documents[0].keys())}")
        logger.info(f"First document similarity: {documents[0].get('similarity', 0)}")
    
    # Use a much lower effective threshold to ensure we get results even with less similar documents
    effective_threshold = settings.RELEVANCE_THRESHOLD * 0.5  # Lower the threshold to 30% of configured value (was 0.8)
    
    # Check if documents have sufficient relevance
    relevant_docs = [doc for doc in documents if doc.get("similarity", 0) >= effective_threshold]
    
    if not relevant_docs:
        logger.warning(f"No documents met the relevance threshold of {effective_threshold}")
        return "No sufficiently relevant documents found."
    
    context_parts = []
    
    for i, doc in enumerate(relevant_docs):
        # Format depends on the document type
        if doc.get("type") == "chunk":
            # Look for content in either reasons_summary or chunk_text
            content = doc.get("reasons_summary") or doc.get("chunk_text") or ""
            chunk_info = (
                f"CHUNK {i+1} [Similarity: {doc.get('similarity'):.2f}]:\n"
                f"From case: {doc.get('case_title', 'Unknown')}\n"
                f"Citation: {doc.get('citation_number', 'N/A')}\n"
                f"Case URL: {doc.get('case_url', '#')}\n"
                f"Text: {content}\n"
            )
            context_parts.append(chunk_info)
        else:
            # Standard document format - using standard DB column names
            content = doc.get("reasons_summary") or ""
            case_url = doc.get('case_url', '#')
            doc_info = (
                f"DOCUMENT {i+1} [Similarity: {doc.get('similarity'):.2f}]:\n"
                f"Title: {doc.get('case_title', 'Unknown')}\n"
                f"Citation: {doc.get('citation_number', 'N/A')}\n"
                f"Case URL: {case_url}\n"
                f"Content: {content}\n"
                f"IMPORTANT: Use this exact URL in markdown links: {case_url}\n"
            )
            context_parts.append(doc_info)
    
    logger.info(f"Formatted {len(relevant_docs)} documents for context")
    return "\n".join(context_parts)

def generate_response(query: str, documents: List[Dict[str, Any]], 
                     conversation_history: List[Dict[str, str]] = None, 
                     streaming_callback: Callable[[str], None] = None) -> str:
    """
    Generate a response based on the query and retrieved documents.
    
    Args:
        query: The user's query
        documents: The retrieved documents
        conversation_history: Optional conversation history for context
        streaming_callback: Optional callback for streaming responses
        
    Returns:
        str: The generated response
    """
    # Import the query classifier
    from app.services.helpers.query_classifier import generate_hybrid_prompt
    
    # Format the context from documents
    context = format_context(documents)
    
    # Check if we have relevant documents
    if context == "No relevant documents found." or context == "No sufficiently relevant documents found.":
        return (f"I'm sorry, but I couldn't find any relevant legal cases that match your query: '{query}'. "
                f"Could you try rephrasing your question or providing more specific details about the legal "
                f"issue you're interested in?")
    
    # Generate the hybrid prompt based on query classification
    hybrid_prompt_data = generate_hybrid_prompt(query, context)
    prompt = hybrid_prompt_data["prompt"]
    
    # Add conversation history if available
    if conversation_history and len(conversation_history) > 0:
        history_text = "\nCONVERSATION HISTORY:\n"
        for msg in conversation_history:
            role = msg.get("role", "").capitalize()
            content = msg.get("content", "")
            history_text += f"{role}: {content}\n"
        
        # Add history to the prompt
        prompt = prompt.replace("USER QUERY:", f"{history_text}\nUSER QUERY:")
    
    # Log the query classification
    logger.info(f"Query classification: {hybrid_prompt_data['classification']['type']} "
                f"(confidence: {hybrid_prompt_data['classification']['confidence']:.2f})")
    
    # Get the LLM provider (for chat feature)
    llm = get_llm_provider(for_chat=True)
    
    # Generate the response
    if streaming_callback and settings.ENABLE_STREAMING:
        # Streaming mode
        llm.generate_streaming(prompt, streaming_callback)
        return ""  # The response is delivered via callback
    else:
        # Regular mode
        return llm.generate(prompt)

def generate_insights(case_content: str, similar_docs: List[Dict[str, Any]], topic: Optional[str] = None, 
                     llm_model: Optional[str] = None) -> List[str]:
    """
    Generate insights based on the case content and similar documents.
    
    Args:
        case_content: The case content/reasons
        similar_docs: The similar documents
        topic: Optional topic for specialized insights
        llm_model: Optional model name to use for generation
        
    Returns:
        List[str]: The generated insights
    """
    # Format the context from documents
    context = format_context(similar_docs)
    
    # Check if we have relevant documents
    if context == "No relevant documents found." or context == "No sufficiently relevant documents found.":
        return ["No sufficiently relevant cases were found to generate insights."]
    
    # Get the arguments template
    template = settings.PROMPT_TEMPLATES.get("build_arguments", "")
    
    # Fill in the template
    prompt = template.format(content=case_content, context=context, topic=topic or "Not specified")
    
    # Add instruction to focus on insights with strength assessments
    prompt += """
\nFocus on generating KEY INSIGHTS only. For each insight, include an assessment of its strength (Strong, Moderate, or Weak) based on:
- Strong: Well-supported by multiple legal precedents, clear factual evidence, or established legal principles
- Moderate: Supported by some precedents or factual evidence, but with some limitations
- Weak: Limited supporting evidence, potentially contested, or based on relatively untested legal theories

Format your response as a list of insights, each with a strength assessment at the end like this:
1. [Insight text]. Strength: Strong
2. [Insight text]. Strength: Moderate 
"""
    
    # Use the specified model if provided, otherwise use the default
    llm = get_llm_provider(for_chat=False, model=llm_model)
    response = llm.generate(prompt)
    
    # Check if there was an error with generation and fall back to OpenAI if needed
    if response.startswith("Error"):
        logger.warning(f"Primary LLM failed for insights, falling back to OpenAI")
        fallback_llm = get_llm_provider(provider="openai", model=settings.CHAT_LLM_MODEL, for_chat=False)
        response = fallback_llm.generate(prompt)
    
    # Parse the response into insights
    insights = []
    in_insights = False
    
    for line in response.split('\n'):
        line = line.strip()
        
        # Look for key insights section
        if line.lower().startswith("key insights") or "insights" in line.lower():
            in_insights = True
            continue
            
        # Skip empty lines
        if not line:
            continue
            
        # If we're in the insights section and the line starts with a number or bullet point
        if in_insights and (line[0].isdigit() or line[0] in ['•', '-', '*']):
            # Remove the bullet point or number
            insight = line
            if line[0].isdigit() and line[1:3] in ['. ', ') ']:
                insight = line[3:].strip()
            elif line[0] in ['•', '-', '*']:
                insight = line[1:].strip()
                
            insights.append(insight)
            
        # If we hit another section heading, stop processing insights
        if in_insights and line.endswith(':') and not line.startswith('-'):
            break
    
    # If we couldn't parse insights properly, extract by simple line splitting
    if not insights:
        # Simple fallback parsing
        insights = [line.strip() for line in response.split('\n') if line.strip() and not line.strip().endswith(':')]
        insights = insights[:5]  # Limit to first 5 lines
    
    return insights

def generate_arguments(case_content: str, similar_docs: List[Dict[str, Any]], topic: Optional[str] = None,
                     streaming_callback: Callable[[str], None] = None, llm_model: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Generate arguments based on the case content and similar documents.
    
    Args:
        case_content: The case content/reasons
        similar_docs: The similar documents
        topic: Optional topic for specialized arguments
        streaming_callback: Optional callback for streaming the generation process
        llm_model: Optional model name to use for generation
        
    Returns:
        List[Dict[str, Any]]: The generated arguments
    """
    # Format the context from documents
    context = format_context(similar_docs)
    
    # Check if we have relevant documents
    if context == "No relevant documents found." or context == "No sufficiently relevant documents found.":
        return [{
            "title": "Insufficient Similar Cases",
            "content": "No sufficiently relevant cases were found to generate arguments.",
            "supporting_cases": [],
            "strength": "N/A"
        }]
    
    # Get the arguments template
    template = settings.PROMPT_TEMPLATES.get("build_arguments", "")
    
    # Fill in the template
    prompt = template.format(content=case_content, context=context, topic=topic or "Not specified")
    
    # Add instruction to focus on arguments
    prompt += "\n\nFocus on generating LEGAL ARGUMENTS only. Format your response with clear argument titles."
    
    # Get the primary LLM provider for arguments feature with the specified model
    llm = get_llm_provider(for_chat=False, model=llm_model)
    
    # Check if we're in streaming mode
    if streaming_callback and settings.ENABLE_STREAMING:
        # Create an error flag to track if the primary provider fails
        stream_error = {"error_occurred": False, "error_message": ""}
        
        # Create a wrapper callback that watches for errors
        def error_checking_callback(chunk: str):
            if chunk.startswith("\nError") and "DeepSeek" in chunk:
                stream_error["error_occurred"] = True
                stream_error["error_message"] = chunk
            else:
                # Only forward non-error chunks
                if not stream_error["error_occurred"]:
                    streaming_callback(chunk)
        
        # Try streaming with primary provider
        llm.generate_streaming(prompt, error_checking_callback)
        
        # If error occurred, fall back to OpenAI
        if stream_error["error_occurred"]:
            logger.warning(f"DeepSeek streaming failed: {stream_error['error_message']}, falling back to OpenAI")
            streaming_callback("\n[Switching to backup model...]\n")
            
            # Get OpenAI provider and use it instead
            fallback_llm = get_llm_provider(provider="openai", model=settings.CHAT_LLM_MODEL, for_chat=False)
            fallback_llm.generate_streaming(prompt, streaming_callback)
            
        # We rely on streaming callback to deliver the content, not the return value
        response = ""
    else:
        # Regular mode
        response = llm.generate(prompt)
        
        # Check if there was an error with DeepSeek and fall back to OpenAI if needed
        if response.startswith("Error") and "DeepSeek" in response:
            logger.warning("DeepSeek failed, falling back to OpenAI for arguments generation")
            llm = get_llm_provider(provider="openai", model=settings.CHAT_LLM_MODEL, for_chat=False)
            response = llm.generate(prompt)
    
    # Parse the response into arguments (simplified for now)
    # In a real scenario, this would be more sophisticated
    arguments = []
    current_argument = None
    
    for line in response.split('\n'):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # If the line looks like a heading (ends with colon or is all caps)
        if line.endswith(':') or line.isupper():
            # If we have an existing argument, add it to the list
            if current_argument:
                arguments.append(current_argument)
            
            # Start a new argument
            current_argument = {
                "title": line.rstrip(':'),
                "content": "",
                "supporting_cases": [],
                "strength": "Medium"  # Default strength
            }
        elif current_argument:
            # If the line contains strength assessment
            if any(strength in line.lower() for strength in ["strong", "moderate", "weak"]):
                for strength in ["strong", "moderate", "weak"]:
                    if strength in line.lower():
                        current_argument["strength"] = strength.capitalize()
                        break
            
            # If the line mentions cases
            elif "case" in line.lower() or "v." in line:
                current_argument["supporting_cases"].append(line)
            
            # Otherwise, add to content
            else:
                current_argument["content"] += line + " "
    
    # Add the last argument
    if current_argument:
        arguments.append(current_argument)
    
    # If no arguments were parsed or generation failed
    if not arguments:
        # Create a default argument from the response
        arguments = [{
            "title": "Legal Argument",
            "content": response[:1000],  # Limit content length
            "supporting_cases": [],
            "strength": "Medium"
        }]
    
    return arguments

def generate_with_reasoning_steps(case_content: str, similar_docs: List[Dict[str, Any]], topic: Optional[str] = None,
                                step_callback: Callable[[Dict[str, Any]], None] = None) -> Dict[str, Any]:
    """
    Generate arguments with step-by-step reasoning using Langchain.
    
    Args:
        case_content: The case content/reasons
        similar_docs: The similar documents
        topic: Optional topic for specialized arguments
        step_callback: Optional callback for notifying about each step
        
    Returns:
        Dict[str, Any]: The generation result with steps
    """
    
    # Define the reasoning steps
    steps = [
        {
            "name": "Analyze Case Content",
            "instructions": "Analyze the given case content. Identify the key legal issues, facts, and any specific legal principles mentioned."
        },
        {
            "name": "Compare With Similar Cases",
            "instructions": "Compare the current case with the similar cases provided. Identify similarities and differences in legal principles, facts, and outcomes."
        },
        {
            "name": "Identify Potential Arguments",
            "instructions": "Based on the analysis and comparison, identify potential legal arguments that could be made. Consider both supporting and opposing arguments."
        },
        {
            "name": "Evaluate Argument Strength",
            "instructions": "Evaluate the strength of each identified argument. Consider legal precedent, factual support, and potential counterarguments."
        },
        {
            "name": "Formulate Final Arguments",
            "instructions": "Review the analysis from previous steps. Formulate the final arguments with clear titles, supporting cases, and assessed strength (Strong, Moderate, or Weak). **Crucially, first reiterate the Key Insights identified in the 'Analyze Case & Compare' step, including their strengths.** Format your response clearly, starting with a '## Key Insights' section, followed by a '## Key Arguments' section."
        }
    ]
    
    # Get the step reasoning template
    template = settings.PROMPT_TEMPLATES.get("step_reasoning", "")
    
    # Format the context from documents
    context = format_context(similar_docs)
    
    # Check if we have relevant documents
    if context == "No relevant documents found." or context == "No sufficiently relevant documents found.":
        if step_callback:
            step_callback({
                "step": "Error",
                "output": "No sufficiently relevant cases were found to generate arguments."
            })
        return {
            "error": "No sufficiently relevant cases were found.",
            "steps": []
        }
    
    # Get the LLM provider (for arguments feature)
    llm_provider = get_llm_provider(for_chat=False)
    
    # Initialize result object
    result = {
        "steps": [],
        "final_output": None
    }
    
    # Process each step
    previous_steps_text = ""
    
    for i, step in enumerate(steps):
        print(f"\n==== STARTING STEP {i+1}: {step['name']} ====")
        
        # Fill in the template for this step
        prompt = template.format(
            content=case_content,
            step=step["name"],
            step_instructions=step["instructions"],
            previous_steps=previous_steps_text
        )
        
        # Generate step output
        try:
            print(f"Generating with {llm_model or 'default model'}...")
            step_output = llm_provider.generate(prompt)
            
            # Check if there was an error with the primary provider
            if step_output.startswith("Error"):
                print(f"Primary LLM failed, trying fallback for step {i+1}")
                logger.warning(f"Primary LLM provider failed, falling back to Claude for step {i+1}")
                
                # Fall back to Claude-3.7-sonnet
                fallback_llm = get_llm_provider(provider="anthropic", model="claude-3-7-sonnet-20250219", for_chat=False)
                step_output = fallback_llm.generate(prompt)
                
                # If still having issues, log the error but continue with what we have
                if step_output.startswith("Error"):
                    print(f"Fallback also failed for step {i+1}")
                    logger.error(f"Fallback to Claude also failed for step {i+1}: {step_output}")
        except Exception as e:
            print(f"Error in step {i+1}: {str(e)}")
            logger.error(f"Error generating step {i+1}: {str(e)}")
            step_output = f"Error processing this step: {str(e)}"
        
        # Record the step
        step_result = {
            "step": step["name"],
            "instructions": step["instructions"],
            "output": step_output
        }
        
        # Add to results
        result["steps"].append(step_result)
        
        # Update previous steps text
        previous_steps_text += f"\n\nSTEP {i+1}: {step['name']}\n{step_output}"
        
        # Notify callback if provided
        if step_callback:
            print(f"Calling step_callback for step {i+1}")
            step_callback(step_result)
            
        print(f"==== COMPLETED STEP {i+1}: {step['name']} ====")
    
    # Final step output is our final result
    result["final_output"] = result["steps"][-1]["output"]
    
    return result 

# Function to count tokens for different model providers
def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count the number of tokens in a text string for a given model.
    
    Args:
        text: The text to count tokens for
        model: The model to use for tokenization (default: gpt-4)
        
    Returns:
        int: The number of tokens
    """
    try:
        # For OpenAI models
        if "gpt" in model.lower():
            try:
                encoding = tiktoken.encoding_for_model(model)
                return len(encoding.encode(text))
            except Exception:
                # Fallback to cl100k_base for newer models that might not be in tiktoken yet
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
        
        # For Claude models - approximation based on whitespace tokenization multiplied by 1.3
        elif "claude" in model.lower():
            # Claude uses about 30% more tokens than whitespace tokenization on average
            return int(len(text.split()) * 1.3)
        
        # For DeepSeek models - approximation similar to Claude
        elif "deepseek" in model.lower():
            # Approximation based on whitespace tokenization
            return int(len(text.split()) * 1.2)
        
        # Default fallback for unknown models
        else:
            # Use a character-based approximation (very rough)
            return len(text) // 4
            
    except Exception as e:
        logger.warning(f"Error counting tokens: {e}")
        # Rough character-based estimate as fallback
        return len(text) // 4

def generate_with_optimized_reasoning(case_content: str, similar_docs: List[Dict[str, Any]], topic: Optional[str] = None,
                                 step_callback: Callable[[Dict[str, Any]], None] = None, 
                                 llm_model: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate arguments with an optimized reasoning approach using fewer steps.
    
    Args:
        case_content: The case content/reasons
        similar_docs: The similar documents
        topic: Optional topic for specialized arguments
        step_callback: Optional callback for notifying about each step
        llm_model: Optional model name to use for generation
        
    Returns:
        Dict[str, Any]: The generation result with steps
    """
    start_time = time.time()  # Start timing
    
    print(f"\n==== STARTING OPTIMIZED REASONING GENERATION ====")
    print(f"Using model: {llm_model or 'default'}")
    print(f"Topic: {topic or 'Not specified'}")
    print(f"Similar docs count: {len(similar_docs)}")
    print(f"Step callback provided: {step_callback is not None}")
    
    # Initialize token counters
    total_input_tokens = 0
    total_output_tokens = 0
    
    # Initialize timing for each step
    step_times = []
    
    # Define the optimized reasoning steps (reduced from 5 to 3)
    steps = [
        {
            "name": "Analyze Case & Compare",
            "instructions": "Analyze the provided CASE CONTENT in light of the SIMILAR CASES/CHUNKS. Identify the key **legal issues** and relevant **legal principles/rules** (including primary legislation sections like EO Act s.66V, s.66W, and relevant principles from precedents). Generate 3-4 key **insights** *specific* to applying these principles to the case facts, noting similarities/differences with precedents. For each insight, assess its strength (Strong, Moderate, Weak) based on Australian law/precedents. Use the EXACT format: '[Insight text]. Strength: [StrengthValue]'. Do not include extra formatting."
        },
        {
            "name": "Identify & Evaluate Arguments",
            "instructions": "Based on the issues and insights from Step 1, identify potential legal arguments. For each argument: **(1) State the relevant legal RULE** (cite specific legislation section AND key precedent principle). **(2) APPLY the rule by comparing the specific facts** of the input case content to the facts and outcomes of the cited precedents. **(3) Evaluate the argument's STRENGTH** (Strong/Moderate/Weak) considering how well the facts align with supportive precedents and potential counterarguments."
        },
        {
            "name": "Formulate Final Arguments",
            "instructions": "Review the analysis. **First, reiterate Key Insights and strengths.** Then, formulate the final arguments using a clear IRAC structure for each. For every argument: **(1) State the ISSUE.** **(2) State the applicable RULE** (cite specific legislation section AND key precedent). **(3) APPLY the rule by explicitly comparing the client's facts to the facts of the supporting/distinguishing precedents.** **(4) CONCLUDE on the argument and its assessed STRENGTH (Strong/Moderate/Weak).** Format using clear titles, 'Legal Reasoning' (covering Rule & Application), 'Supporting Cases' (list cited precedents), and 'Supporting Legislation'. Ensure citations directly support the Rule and Application analysis."
        }
    ]
    
    # Get the step reasoning template
    template = settings.PROMPT_TEMPLATES.get("step_reasoning", "")
    
    # Format the context from documents
    context = format_context(similar_docs)
    
    # Check if we have relevant documents
    if context == "No relevant documents found." or context == "No sufficiently relevant documents found.":
        if step_callback:
            step_callback({
                "step": "Error",
                "output": "No sufficiently relevant cases were found to generate arguments."
            })
        return {
            "error": "No sufficiently relevant cases were found.",
            "steps": []
        }
    
    # Get the LLM provider with the specified model
    llm = get_llm_provider(for_chat=False, model=llm_model)
    
    # Initialize result object
    result = {
        "steps": [],
        "final_output": None,
        "token_usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        },
        "execution_time": 0
    }
    
    # Process each step
    previous_steps_text = ""
    
    for i, step in enumerate(steps):
        step_start_time = time.time()  # Start timing for this step
        print(f"\n==== STARTING STEP {i+1}: {step['name']} ====")
        
        # Fill in the template for this step
        prompt = template.format(
            content=case_content,
            context=context, # Ensure context is included in the prompt
            topic=topic or "Not specified",
            step=step["name"],
            step_instructions=step["instructions"],
            previous_steps=previous_steps_text
        )
        
        # Count input tokens
        input_token_count = count_tokens(prompt, llm_model or "gpt-4")
        total_input_tokens += input_token_count
        
        # Generate step output
        try:
            print(f"Generating with {llm_model or 'default model'}...")
            step_output = llm.generate(prompt)
            
            # Count output tokens
            output_token_count = count_tokens(step_output, llm_model or "gpt-4")
            total_output_tokens += output_token_count
            
            # Check if there was an error with the primary provider
            if step_output.startswith("Error"):
                print(f"Primary LLM failed, trying fallback for step {i+1}")
                logger.warning(f"Primary LLM provider failed, falling back to Claude for step {i+1}")
                
                # Fall back to Claude-3.7-sonnet
                fallback_llm = get_llm_provider(provider="anthropic", model="claude-3-7-sonnet-20250219", for_chat=False)
                step_output = fallback_llm.generate(prompt)
                
                # Recount output tokens with the fallback model
                output_token_count = count_tokens(step_output, "claude-3-7-sonnet-20250219")
                total_output_tokens += output_token_count
                
                # If still having issues, log the error but continue with what we have
                if step_output.startswith("Error"):
                    print(f"Fallback also failed for step {i+1}")
                    logger.error(f"Fallback to Claude also failed for step {i+1}: {step_output}")
        except Exception as e:
            print(f"Error in step {i+1}: {str(e)}")
            logger.error(f"Error generating step {i+1}: {str(e)}")
            step_output = f"Error processing this step: {str(e)}"
            output_token_count = count_tokens(step_output, llm_model or "gpt-4")
            total_output_tokens += output_token_count
        
        # Calculate step time
        step_time = time.time() - step_start_time
        step_times.append(step_time)
        
        # Record the step
        step_result = {
            "step": step["name"],
            "instructions": step["instructions"],
            "output": step_output,
            "metrics": {
                "input_tokens": input_token_count,
                "output_tokens": output_token_count,
                "execution_time_seconds": step_time
            }
        }
        
        # Add to results
        result["steps"].append(step_result)
        
        # Update previous steps text
        previous_steps_text += f"\n\nSTEP {i+1}: {step['name']}\n{step_output}"
        
        # Log token usage for this step
        print(f"Step {i+1} tokens - Input: {input_token_count}, Output: {output_token_count}, Time: {step_time:.2f}s")
        
        # Notify callback if provided
        if step_callback:
            print(f"Calling step_callback for step {i+1}")
            step_callback(step_result)
            
        print(f"==== COMPLETED STEP {i+1}: {step['name']} ====")
    
    # Final step output is our final result
    result["final_output"] = result["steps"][-1]["output"] if result["steps"] else "Failed to generate arguments"
    
    # Calculate total execution time
    total_execution_time = time.time() - start_time
    
    # Update token usage in result
    result["token_usage"]["input_tokens"] = total_input_tokens
    result["token_usage"]["output_tokens"] = total_output_tokens
    result["token_usage"]["total_tokens"] = total_input_tokens + total_output_tokens
    result["execution_time"] = total_execution_time
    
    # Print token usage summary
    print("\n==== GENERATION METRICS SUMMARY ====")
    print(f"Total Input Tokens: {total_input_tokens}")
    print(f"Total Output Tokens: {total_output_tokens}")
    print(f"Total Tokens: {total_input_tokens + total_output_tokens}")
    print(f"Total Execution Time: {total_execution_time:.2f} seconds")
    
    for i, step_time in enumerate(step_times):
        step_percentage = (step_time / total_execution_time) * 100
        print(f"Step {i+1} Time: {step_time:.2f}s ({step_percentage:.1f}% of total)")
    
    return result

def format_document(doc: Dict[str, Any]) -> str:
    """
    Format a document for use in a prompt.
    
    Args:
        doc: The document to format
        
    Returns:
        A formatted string representation of the document
    """
    # Format citation information
    citation = f"Citation: {doc.get('citation_number', 'Unknown')}"
    
    # Include document content with truncation if too long
    content_section = ""
    if 'reasons_summary' in doc:
        content_section = f"Text: {doc.get('reasons_summary', '')}\n"
    
    # Combine all sections
    formatted_doc = (
        f"===== CASE DOCUMENT =====\n"
        f"Title: {doc.get('case_title', 'Unknown')}\n"
        f"{citation}\n"
        f"Topic: {doc.get('case_topic', 'Unknown')}\n"
        f"Content: {doc.get('reasons_summary', '')}\n"
        f"Relevance: {doc.get('similarity', 0):.2f}\n"
    )
    
    return formatted_doc 

def generate_with_single_call_reasoning(case_content: str, similar_docs: List[Dict[str, Any]], topic: Optional[str] = None,
                                       llm_model: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate arguments with a single LLM call but structured internal reasoning steps.
    
    Args:
        case_content: The case content/reasons
        similar_docs: The similar documents
        topic: Optional topic for specialized arguments
        llm_model: Optional model name to use for generation
        
    Returns:
        Dict[str, Any]: The generation result
    """
    start_time = time.time()  # Start timing
    
    print(f"\n==== STARTING SINGLE-CALL REASONING GENERATION ====")
    print(f"Using model: {llm_model or 'default'}")
    print(f"Topic: {topic or 'Not specified'}")
    print(f"Similar docs count: {len(similar_docs)}")
    
    # Format the context from documents
    context = format_context(similar_docs)
    
    # Check if we have relevant documents
    if context == "No relevant documents found." or context == "No sufficiently relevant documents found.":
        return {
            "error": "No sufficiently relevant cases were found.",
            "final_output": "No sufficiently relevant cases were found to generate arguments."
        }
    
    # Build comprehensive prompt with all reasoning steps
    prompt = f"""
# Legal Argument Generation Task

## Input
Case Content: {case_content}
Topic: {topic or "Not specified"}

## Context (Similar Cases)
{context}

## Instructions
You are a legal expert tasked with generating strong legal arguments. Follow this 3-step reasoning process carefully:

STEP 1: ANALYZE CASE & COMPARE
Analyze the provided case content and compare it with similar cases. Identify key legal issues and relevant legal principles/rules.
Generate 3-4 key insights specific to applying these principles to the case facts, noting similarities/differences with precedents.
For each insight, assess its strength (Strong, Moderate, Weak) based on applicable law and precedents.

STEP 2: IDENTIFY & EVALUATE ARGUMENTS
Based on your analysis, identify potential legal arguments. For each argument:
(1) State the relevant legal RULE with specific legislation and precedent
(2) APPLY the rule by comparing facts of the input case to cited precedents
(3) Evaluate argument STRENGTH (Strong/Moderate/Weak)

STEP 3: FORMULATE FINAL ARGUMENTS
Formulate final arguments using IRAC structure:
(1) State the ISSUE
(2) State the RULE (legislation and precedent)
(3) APPLY the rule to client's facts
(4) CONCLUDE on the argument and its STRENGTH

## Output Format
Begin with a heading "LEGAL ANALYSIS: [TOPIC]"

Under "## Key Insights", list each insight with its strength in the format:
1. [Insight title]: [Insight explanation]. Strength: [Strong/Moderate/Weak]

Under "## Key Arguments", structure each argument with:
- Title: The legal issue/claim
- Legal Reasoning: The rule and application
- Supporting Cases: Cases cited
- Strength: Strong/Moderate/Weak
"""
    
    # Count input tokens
    input_token_count = count_tokens(prompt, llm_model or "gpt-4")
    
    # Get LLM provider
    llm = get_llm_provider(for_chat=False, model=llm_model)
    
    try:
        # Generate response
        print(f"Generating with {llm_model or 'default model'}...")
        output = llm.generate(prompt)
        
        # Count output tokens
        output_token_count = count_tokens(output, llm_model or "gpt-4")
        
        # Check if there was an error with the primary provider
        if output.startswith("Error"):
            print(f"Primary LLM failed, trying fallback")
            logger.warning(f"Primary LLM provider failed, falling back to Claude for single-call generation")
            
            # Fall back to Claude-3.7-sonnet
            fallback_llm = get_llm_provider(provider="anthropic", model="claude-3-7-sonnet-20250219", for_chat=False)
            output = fallback_llm.generate(prompt)
            
            # Recount output tokens with the fallback model
            output_token_count = count_tokens(output, "claude-3-7-sonnet-20250219")
    except Exception as e:
        print(f"Error in generation: {str(e)}")
        logger.error(f"Error in single-call generation: {str(e)}")
        output = f"Error processing this generation: {str(e)}"
        output_token_count = count_tokens(output, llm_model or "gpt-4")
    
    # Calculate total time
    total_execution_time = time.time() - start_time
    
    # Log metrics
    print(f"\n==== SINGLE-CALL GENERATION METRICS ====")
    print(f"Input Tokens: {input_token_count}")
    print(f"Output Tokens: {output_token_count}")
    print(f"Total Tokens: {input_token_count + output_token_count}")
    print(f"Execution Time: {total_execution_time:.2f} seconds")
    
    return {
        "final_output": output,
        "token_usage": {
            "input_tokens": input_token_count,
            "output_tokens": output_token_count,
            "total_tokens": input_token_count + output_token_count
        },
        "execution_time": total_execution_time
    } 