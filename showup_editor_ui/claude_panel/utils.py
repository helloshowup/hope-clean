# utils.py

import re
import logging
from collections import Counter
from typing import List

logger = logging.getLogger(__name__)

# Stop-word list (can be expanded or loaded from a file)
DEFAULT_STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for', 'with',
    'it', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'we', 'they', 'my', 'your', 'his', 'her',
    'its', 'our', 'their', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
    'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just',
    'don', 'should', 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', 'couldn', 'didn', 'doesn',
    'hadn', 'hasn', 'haven', 'isn', 'ma', 'mightn', 'mustn', 'needn', 'shan', 'shouldn', 'wasn', 'weren',
    'won', 'wouldn'
}

def normalize_text_for_similarity(text: str, stop_words: set = None) -> List[str]:
    """Normalize text for similarity calculation: lowercase, remove punctuation, split, remove stop words."""
    if stop_words is None:
        stop_words = DEFAULT_STOP_WORDS
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    words = text.split()
    words = [w for w in words if w not in stop_words and len(w) > 2]
    return words

def calculate_cosine_similarity(text1: str, text2: str, stop_words: set = None) -> float:
    """Calculate cosine similarity between two text passages."""
    try:
        if not text1 or not text2:
            return 0.0
        
        words1 = normalize_text_for_similarity(text1, stop_words)
        words2 = normalize_text_for_similarity(text2, stop_words)
        
        if not words1 or not words2: # If one text becomes empty after normalization
            return 0.0

        counter1 = Counter(words1)
        counter2 = Counter(words2)
        
        all_words = set(counter1.keys()) | set(counter2.keys())
        
        if not all_words:
            return 0.0
            
        dot_product = sum(counter1.get(word, 0) * counter2.get(word, 0) for word in all_words)
        magnitude1 = sum(count ** 2 for count in counter1.values()) ** 0.5
        magnitude2 = sum(count ** 2 for count in counter2.values()) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
            
        similarity = dot_product / (magnitude1 * magnitude2)
        return similarity
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return 0.0

def extract_local_keywords(lesson_content: str, stop_words: set = None, limit: int = 15) -> List[str]:
    """Extract keywords locally from lesson structure (headings, bold, lists, proper nouns)."""
    if stop_words is None:
        stop_words = DEFAULT_STOP_WORDS
    
    keywords = []
    # Extract from headings (highest priority)
    headings = re.findall(r'#+\s+(.+?)(?:\n|$)', lesson_content)
    for heading in headings:
        heading_words = re.findall(r'\b[A-Za-z]{3,}\b', heading.lower())
        keywords.extend(heading_words)
    
    # Extract from bold/emphasized text
    bold_text = re.findall(r'\*\*(.+?)\*\*', lesson_content)
    italic_text = re.findall(r'\*(.+?)\*', lesson_content)
    for text_group in [bold_text, italic_text]:
        for text in text_group:
            text_words = re.findall(r'\b[A-Za-z]{3,}\b', text.lower())
            keywords.extend(text_words)
    
    # Extract from bullet points and lists
    list_items = re.findall(r'^\s*[-*+]\s+(.+?)(?:\n|$)', lesson_content, re.MULTILINE)
    for item in list_items:
        item_words = re.findall(r'\b[A-Za-z]{4,}\b', item.lower())
        keywords.extend(item_words[:2])  # Limit per item
    
    # Extract technical terms and proper nouns (simple heuristic: capitalized words)
    proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', lesson_content)
    keywords.extend([term.lower() for term in proper_nouns if len(term) > 3])
    
    # Filter and deduplicate keywords
    filtered_keywords = []
    seen_keywords = set()
    for keyword in keywords:
        kw_lower = keyword.lower().strip()
        if kw_lower not in stop_words and len(kw_lower) >= 3 and kw_lower not in seen_keywords and kw_lower.isalpha():
            filtered_keywords.append(kw_lower)
            seen_keywords.add(kw_lower)
            
    return filtered_keywords[:limit]

# Placeholder for other utility functions that might be extracted:
# - _assess_content_complexity
# - _create_lesson_summary
# - _fallback_query_construction
# - _extract_paragraph_title

if __name__ == '__main__':
    # Example usage for testing utils
    sample_text1 = "This is a sample text about Python programming and software development."
    sample_text2 = "Another text discussing Python coding and general software engineering practices."
    similarity = calculate_cosine_similarity(sample_text1, sample_text2)
    print(f"Similarity: {similarity:.4f}")

    lesson = """
    # Introduction to Python
    Python is a **versatile** language. It's used for web development, data science, and more.
    * Easy to learn
    * Large community
    Key concepts: Variables, Loops, Functions. Also, Object-Oriented Programming (OOP) is important.
    """
    keywords = extract_local_keywords(lesson)
    print(f"Keywords: {keywords}")
