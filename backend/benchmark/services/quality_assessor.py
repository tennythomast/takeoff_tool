"""
Quality assessment service for benchmark results.

This service is responsible for:
1. Calculating semantic similarity between responses
2. Assessing quality retention
3. Providing task-specific metrics
"""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple

# Try to import sentence-transformers for semantic similarity
try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Using fallback similarity method.")

# Try to import spaCy for NLP tasks
try:
    import spacy
    SPACY_AVAILABLE = True
    try:
        nlp = spacy.load("en_core_web_md")
    except:
        nlp = None
        SPACY_AVAILABLE = False
        logging.warning("spaCy model 'en_core_web_md' not available. Please install it with: python -m spacy download en_core_web_md")
except ImportError:
    SPACY_AVAILABLE = False
    nlp = None
    logging.warning("spaCy not available. Using fallback similarity method.")

logger = logging.getLogger(__name__)

# Initialize sentence transformer model if available
sentence_model = None
if SENTENCE_TRANSFORMERS_AVAILABLE:
    try:
        sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Loaded sentence-transformers model: all-MiniLM-L6-v2")
    except Exception as e:
        logger.warning(f"Failed to load sentence-transformers model: {str(e)}")
        SENTENCE_TRANSFORMERS_AVAILABLE = False


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity between two texts.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0
    
    # Method 1: Use sentence-transformers if available (best quality)
    if SENTENCE_TRANSFORMERS_AVAILABLE and sentence_model:
        try:
            embeddings1 = sentence_model.encode([text1], convert_to_tensor=True)
            embeddings2 = sentence_model.encode([text2], convert_to_tensor=True)
            cosine_scores = util.pytorch_cos_sim(embeddings1, embeddings2)
            return float(cosine_scores[0][0])
        except Exception as e:
            logger.warning(f"Error using sentence-transformers: {str(e)}. Falling back to spaCy.")
    
    # Method 2: Use spaCy if available (medium quality)
    if SPACY_AVAILABLE and nlp:
        try:
            doc1 = nlp(text1[:10000])  # Limit text length to avoid memory issues
            doc2 = nlp(text2[:10000])
            return doc1.similarity(doc2)
        except Exception as e:
            logger.warning(f"Error using spaCy: {str(e)}. Falling back to basic similarity.")
    
    # Method 3: Basic fallback (low quality)
    return _basic_similarity(text1, text2)


def _basic_similarity(text1: str, text2: str) -> float:
    """Calculate a basic similarity score between two texts.
    
    This is a fallback method when better NLP libraries are not available.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0 and 1
    """
    # Convert to lowercase and split into words
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    if union == 0:
        return 0.0
    
    return intersection / union


def assess_quality_retention(similarity_vs_gpt4: float, similarity_vs_claude: float) -> bool:
    """Assess if quality is retained based on similarity scores.
    
    Args:
        similarity_vs_gpt4: Similarity score vs GPT-4
        similarity_vs_claude: Similarity score vs Claude
        
    Returns:
        True if quality is retained, False otherwise
    """
    # Quality is retained if similarity is above threshold for either model
    threshold = 0.85
    return similarity_vs_gpt4 >= threshold or similarity_vs_claude >= threshold


def calculate_task_specific_metrics(
    input_text: str,
    expected_output: Optional[str],
    actual_response: str,
    task_type: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate task-specific metrics for a benchmark result.
    
    Args:
        input_text: Input text
        expected_output: Expected output (if available)
        actual_response: Actual response
        task_type: Type of task (e.g., "classification", "qa", etc.)
        
    Returns:
        Dictionary of task-specific metrics
    """
    metrics = {}
    
    # If no task type is specified, try to infer it
    if task_type is None:
        task_type = _infer_task_type(input_text, expected_output)
    
    # Calculate metrics based on task type
    if task_type == "classification" and expected_output:
        metrics["accuracy"] = _calculate_classification_accuracy(expected_output, actual_response)
    elif task_type == "qa":
        metrics["answer_relevance"] = _calculate_answer_relevance(input_text, actual_response)
    elif task_type == "summarization":
        metrics["conciseness"] = _calculate_conciseness(input_text, actual_response)
        metrics["coverage"] = _calculate_coverage(input_text, actual_response)
    
    return metrics


def _infer_task_type(input_text: str, expected_output: Optional[str]) -> str:
    """Infer the type of task based on input and expected output.
    
    Args:
        input_text: Input text
        expected_output: Expected output (if available)
        
    Returns:
        Task type
    """
    # If expected output is a single word or number, it's likely classification
    if expected_output and len(expected_output.split()) <= 2:
        return "classification"
    
    # If input contains a question mark, it's likely QA
    if "?" in input_text:
        return "qa"
    
    # Default to summarization for longer texts
    if len(input_text.split()) > 100:
        return "summarization"
    
    # Default
    return "general"


def _calculate_classification_accuracy(expected: str, actual: str) -> float:
    """Calculate classification accuracy.
    
    Args:
        expected: Expected output
        actual: Actual response
        
    Returns:
        Accuracy (0 or 1)
    """
    # Simple exact match
    expected_clean = expected.lower().strip()
    
    # Check if the expected label is contained in the actual response
    if expected_clean in actual.lower():
        return 1.0
    
    return 0.0


def _calculate_answer_relevance(question: str, answer: str) -> float:
    """Calculate relevance of an answer to a question.
    
    Args:
        question: Question text
        answer: Answer text
        
    Returns:
        Relevance score between 0 and 1
    """
    # Use semantic similarity as a proxy for relevance
    return calculate_semantic_similarity(question, answer)


def _calculate_conciseness(original_text: str, summary: str) -> float:
    """Calculate conciseness of a summary.
    
    Args:
        original_text: Original text
        summary: Summary text
        
    Returns:
        Conciseness score between 0 and 1
    """
    original_length = len(original_text.split())
    summary_length = len(summary.split())
    
    if original_length == 0:
        return 0.0
    
    compression_ratio = summary_length / original_length
    
    # Ideal compression ratio is around 0.2 (80% reduction)
    if compression_ratio <= 0.2:
        return 1.0
    elif compression_ratio >= 1.0:
        return 0.0
    else:
        # Linear scale between 0.2 and 1.0
        return 1.0 - ((compression_ratio - 0.2) / 0.8)


def _calculate_coverage(original_text: str, summary: str) -> float:
    """Calculate coverage of a summary.
    
    Args:
        original_text: Original text
        summary: Summary text
        
    Returns:
        Coverage score between 0 and 1
    """
    # Use semantic similarity as a proxy for coverage
    return calculate_semantic_similarity(original_text, summary)
