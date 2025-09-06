"""
Shared search utilities for RAG components.
"""
from typing import List, Dict, Any, Set
import re


class SearchUtilities:
    """Utility class for common search operations."""
    
    @staticmethod
    def normalize_search_term(term: str) -> str:
        """Normalize search terms for consistent matching."""
        if not term:
            return ""
        return term.lower().strip()
    
    @staticmethod
    def extract_keywords(text: str, min_length: int = 3) -> Set[str]:
        """Extract keywords from text for search indexing."""
        if not text:
            return set()
        
        # Remove special characters and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter by minimum length and remove common stop words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = {word for word in words if len(word) >= min_length and word not in stop_words}
        
        return keywords
    
    @staticmethod
    def calculate_text_similarity(text1: str, text2: str) -> float:
        """Calculate basic text similarity score."""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(SearchUtilities.extract_keywords(text1))
        words2 = set(SearchUtilities.extract_keywords(text2))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    @staticmethod
    def filter_articles_by_keywords(articles: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        """Filter articles based on keyword presence."""
        if not keywords:
            return articles
        
        filtered = []
        normalized_keywords = [SearchUtilities.normalize_search_term(kw) for kw in keywords]
        
        for article in articles:
            title = article.get('title', '').lower()
            body = article.get('body', '').lower()
            
            # Check if any keyword appears in title or body
            if any(keyword in title or keyword in body for keyword in normalized_keywords):
                filtered.append(article)
        
        return filtered
    
    @staticmethod
    def rank_articles_by_relevance(articles: List[Dict[str, Any]], search_terms: List[str]) -> List[Dict[str, Any]]:
        """Rank articles by relevance to search terms."""
        if not search_terms:
            return articles
        
        search_text = ' '.join(search_terms).lower()
        
        def calculate_relevance(article: Dict[str, Any]) -> float:
            title = article.get('title', '')
            body = article.get('body', '')
            combined_text = f"{title} {body}"
            
            return SearchUtilities.calculate_text_similarity(search_text, combined_text)
        
        # Sort by relevance score (highest first)
        return sorted(articles, key=calculate_relevance, reverse=True)
