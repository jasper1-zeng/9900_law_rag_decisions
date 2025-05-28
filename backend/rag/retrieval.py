"""
RAG Retrieval Module

This module handles the retrieval of documents from the vector store.
"""
from typing import List, Dict, Any, Union, Optional
import logging
from sqlalchemy import text
from sqlalchemy.engine import create_engine
from app.config import settings
from app.db.database import engine as app_engine
import os

# Import for reranking functionality
try:
    from sentence_transformers import CrossEncoder
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch
    RERANKING_AVAILABLE = True
except ImportError:
    RERANKING_AVAILABLE = False
    logging.getLogger(__name__).warning("sentence_transformers or transformers not available. Reranking will be disabled.")

logger = logging.getLogger(__name__)

# Constants
RERANKER_MODEL_NAME = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
MAX_SEQ_LENGTH = 4096
# Set up cache directory using project settings
MODELS_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models_cache')

# Create cache directory if it doesn't exist
os.makedirs(MODELS_CACHE_DIR, exist_ok=True)

# Global variable to store loaded reranker
_reranker = None

def get_reranker(model_name: str = RERANKER_MODEL_NAME):
    """
    Get or initialize the reranker with local caching
    
    Args:
        model_name: The name of the reranker model
        
    Returns:
        CrossEncoder or a custom Longformer model: The initialized reranker model
    """
    global _reranker
    
    if _reranker is not None:
        return _reranker
        
    try:
        logger.info(f"Loading reranker model {model_name}")
        
        # We now default to using a cross-encoder model which is more efficient
        # but we keep the Longformer code for backward compatibility or if someone
        # explicitly wants to use a Longformer model
        if "longformer" in model_name.lower():
            # For Longformer models, we need a custom implementation
            # Set cache directory via environment variable
            os.environ['TRANSFORMERS_CACHE'] = MODELS_CACHE_DIR
            
            # Initialize tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Create a custom reranker class that mimics CrossEncoder interface
            class LongformerReranker:
                def __init__(self, model, tokenizer):
                    self.model = model
                    self.tokenizer = tokenizer
                    self.device = "cuda" if torch.cuda.is_available() else "cpu"
                    self.model.to(self.device)
                    self.model.eval()
                
                def predict(self, sentence_pairs):
                    """Compute similarity scores for pairs of sentences"""
                    scores = []
                    with torch.no_grad():
                        for query, document in sentence_pairs:
                            # Tokenize input pair
                            inputs = self.tokenizer(
                                query, 
                                document,
                                padding=True,
                                truncation='longest_first',
                                max_length=MAX_SEQ_LENGTH,
                                return_tensors="pt"
                            )
                            inputs = {k: v.to(self.device) for k, v in inputs.items()}
                            
                            # Forward pass
                            outputs = self.model(**inputs)
                            logits = outputs.logits
                            
                            # Get score (use the first logit for classification tasks)
                            score = logits[0][0].item()
                            scores.append(score)
                    return scores
            
            _reranker = LongformerReranker(model, tokenizer)
        else:
            # Default to CrossEncoder for other models
            os.environ['SENTENCE_TRANSFORMERS_HOME'] = MODELS_CACHE_DIR
            _reranker = CrossEncoder(model_name)
        
        return _reranker
    except Exception as e:
        logger.error(f"Error loading reranker model: {e}")
        # Fallback to loading without cache in case of issues
        logger.info(f"Fallback: Loading reranker model {model_name} without caching")
        if "longformer" in model_name.lower():
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            _reranker = LongformerReranker(model, tokenizer)
        else:
            _reranker = CrossEncoder(model_name)
        return _reranker

def retrieve_documents(query_embedding: List[float], limit: int = 4, topic: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve documents based on query embedding, optionally filtered by topic.
    
    Args:
        query_embedding: The embedding of the query
        limit: The maximum number of documents to retrieve
        topic: Optional topic filter
        
    Returns:
        List[Dict[str, Any]]: The list of retrieved documents
    """
    try:
        # Use the existing engine from app.db.database
        # This ensures we're using the same connection pool
        engine = app_engine
        
        # Build the base query
        query_text = """
        SELECT 
            id,
            case_title,
            reasons_summary,
            reasons,
            citation_number,
            case_topic,
            catchwords,
            case_url,
            1 - (reasons_summary_embedding <-> CAST(:embedding AS vector)) as similarity
        FROM 
            satdata
        """
        
        # Add topic filter if provided
        params = {"embedding": query_embedding, "limit": limit}
        if topic:
            query_text += " WHERE case_topic = :topic"
            params["topic"] = topic
        
        # Add order by and limit
        query_text += """
        ORDER BY 
            reasons_summary_embedding <-> CAST(:embedding AS vector)
        LIMIT 
            :limit
        """
        
        # Execute the query
        with engine.connect() as conn:
            result = conn.execute(
                text(query_text), 
                params
            ).fetchall()
        
        # Format the results - using consistent database column names
        documents = []
        for row in result:
            documents.append({
                "id": row.id,
                "case_title": row.case_title,
                "reasons_summary": row.reasons_summary,
                "reasons": row.reasons,
                "citation_number": row.citation_number,
                "case_topic": row.case_topic,
                "catchwords": row.catchwords,
                "case_url": row.case_url,
                "similarity": float(row.similarity)
            })
        
        logger.info(f"Retrieved {len(documents)} documents from vector store")
        return documents
    
    except Exception as e:
        logger.error(f"Error retrieving documents from vector store: {e}")
        # Return empty list on error
        return []

def retrieve_case_chunks(query_embedding: List[float], limit: int = 4, case_id: Optional[str] = None, topic: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve case chunks similar to a query embedding.
    
    Args:
        query_embedding: The embedding of the query
        limit: The maximum number of chunks to retrieve
        case_id: Optional case ID to filter chunks from a specific case
        topic: Optional topic filter
        
    Returns:
        List[Dict[str, Any]]: The list of retrieved case chunks
    """
    try:
        engine = app_engine
        
        # Build the base query
        query_text = """
        SELECT 
            rc.id as chunk_id,
            rc.chunk_text,
            rc.chunk_index,
            rc.case_id,
            rc.case_topic,
            s.case_title,
            s.reasons,
            s.citation_number,
            s.case_url,
            1 - (rc.chunk_embedding <-> CAST(:embedding AS vector)) as similarity
        FROM 
            reasons_chunks rc
        JOIN 
            satdata s ON rc.case_id = s.id
        WHERE 1=1
        """
        
        # Add filters if provided
        params = {"embedding": query_embedding, "limit": limit}
        if case_id:
            query_text += " AND rc.case_id = :case_id"
            params["case_id"] = case_id
        
        if topic:
            query_text += " AND rc.case_topic = :topic"
            params["topic"] = topic
        
        # Add order by and limit
        query_text += """
        ORDER BY rc.chunk_embedding <-> CAST(:embedding AS vector)
        LIMIT :limit
        """
        
        # Execute the query
        with engine.connect() as conn:
            result = conn.execute(text(query_text), params).fetchall()
        
        # Format the results
        chunks = []
        for row in result:
            chunks.append({
                "chunk_id": row.chunk_id,
                "chunk_text": row.chunk_text,
                "chunk_index": row.chunk_index,
                "case_id": row.case_id,
                "case_title": row.case_title,
                "case_topic": row.case_topic,
                "reasons": row.reasons,
                "citation_number": row.citation_number,
                "case_url": row.case_url,
                "similarity": float(row.similarity)
            })
        
        logger.info(f"Retrieved {len(chunks)} case chunks from vector store")
        return chunks
    
    except Exception as e:
        logger.error(f"Error retrieving case chunks from vector store: {e}")
        # Return empty list on error
        return []

def rerank_documents(documents: List[Dict[str, Any]], query_text: str, model_name: str = RERANKER_MODEL_NAME) -> List[Dict[str, Any]]:
    """
    Rerank documents based on their relevance to the query text.
    
    Args:
        documents: The candidate documents to rerank
        query_text: The query text to rank against
        model_name: The name of the reranker model
        
    Returns:
        List[Dict[str, Any]]: The reranked documents
    """
    if not RERANKING_AVAILABLE:
        logger.warning("Reranking is not available, skipping reranking step")
        return documents
    
    if not documents:
        return []
        
    try:
        # Initialize reranker using the caching function
        reranker = get_reranker(model_name)
        
        # Prepare input pairs (query + document text)
        # Prioritize reasons_summary over full reasons to avoid truncation issues
        pairs = [(query_text, doc.get("reasons_summary", doc.get("reasons", ""))) for doc in documents]
        
        # Get scores
        scores = reranker.predict(pairs)
        
        # Add new scores to documents and create a new list
        reranked_docs = []
        for i, doc in enumerate(documents):
            # Create a copy to avoid modifying the original
            reranked_doc = doc.copy()
            reranked_doc["rerank_score"] = float(scores[i])
            reranked_docs.append(reranked_doc)
        
        # Sort by new scores
        reranked_docs.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        
        logger.info(f"Reranked {len(documents)} documents")
        return reranked_docs
        
    except Exception as e:
        logger.error(f"Error reranking documents: {e}")
        # Return the original documents on error
        return documents

def retrieve_with_reranking(query_embedding: List[float], query_text: str, limit: int = 4, 
                           topic: Optional[str] = None, candidate_multiplier: int = 2) -> List[Dict[str, Any]]:
    """
    Retrieve documents with reranking.
    
    This retrieves a larger set of candidate documents first,
    then reranks them using a cross-encoder model for more precise relevance.
    
    Args:
        query_embedding: The embedding of the query
        query_text: The original query text
        limit: The maximum number of documents to return after reranking
        topic: Optional topic filter
        candidate_multiplier: How many more candidates to retrieve for reranking
        
    Returns:
        List[Dict[str, Any]]: The list of reranked documents
    """
    # Step 1: Get a larger candidate set
    candidate_limit = limit * candidate_multiplier  # Get more candidates for reranking
    candidates = retrieve_documents(query_embedding, limit=candidate_limit, topic=topic)
    
    if not candidates:
        return []
    
    # Step 2: Apply reranking
    reranked_candidates = rerank_documents(candidates, query_text)
    
    # Step 3: Return top N after reranking
    return reranked_candidates[:limit]

def retrieve_case_chunks_with_reranking(query_embedding: List[float], query_text: str, limit: int = 4, 
                                       case_id: Optional[str] = None, topic: Optional[str] = None,
                                       candidate_multiplier: int = 2) -> List[Dict[str, Any]]:
    """
    Retrieve case chunks with reranking.
    
    Args:
        query_embedding: The embedding of the query
        query_text: The original query text
        limit: The maximum number of chunks to return after reranking
        case_id: Optional case ID to filter chunks from a specific case
        topic: Optional topic filter
        candidate_multiplier: How many more candidates to retrieve for reranking
        
    Returns:
        List[Dict[str, Any]]: The list of reranked case chunks
    """
    # Step 1: Get a larger candidate set
    candidate_limit = limit * candidate_multiplier
    candidates = retrieve_case_chunks(query_embedding, limit=candidate_limit, case_id=case_id, topic=topic)
    
    if not candidates:
        return []
    
    # Step 2: Apply reranking - for chunks we use chunk_text instead of reasons_summary
    try:
        if RERANKING_AVAILABLE:
            # Initialize reranker using the shared caching function
            reranker = get_reranker(RERANKER_MODEL_NAME)
            
            # Prepare input pairs (query + chunk text)
            # Prioritize chunk_text instead of full reasons to avoid truncation issues
            pairs = [(query_text, chunk.get("chunk_text", chunk.get("reasons", ""))) for chunk in candidates]
            
            # Get scores
            scores = reranker.predict(pairs)
            
            # Add new scores to chunks and create a new list
            reranked_chunks = []
            for i, chunk in enumerate(candidates):
                # Create a copy to avoid modifying the original
                reranked_chunk = chunk.copy()
                reranked_chunk["rerank_score"] = float(scores[i])
                reranked_chunks.append(reranked_chunk)
            
            # Sort by new scores
            reranked_chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            
            logger.info(f"Reranked {len(reranked_chunks)} chunks")
            return reranked_chunks[:limit]
        else:
            # If reranking is not available, return the original chunks
            return candidates[:limit]
    
    except Exception as e:
        logger.error(f"Error reranking chunks: {e}")
        # Return the original chunks on error
        return candidates[:limit] 