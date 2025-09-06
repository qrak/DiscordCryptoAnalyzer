"""
Context Building Module for RAG Engine

Handles building analysis context from news articles and search results.
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from src.logger.logger import Logger
from src.utils.token_counter import TokenCounter


class ContextBuilder:
    """Builds analysis context from various data sources."""
    
    def __init__(self, logger: Logger, token_counter: TokenCounter):
        self.logger = logger
        self.token_counter = token_counter
        self.latest_article_urls: Dict[str, str] = {}
    
    async def keyword_search(self, query: str, news_database: List[Dict[str, Any]], 
                           symbol: Optional[str] = None, coin_index: Dict[str, List[int]] = None,
                           category_word_map: Dict[str, str] = None,
                           important_categories: Set[str] = None) -> List[Tuple[int, float]]:
        """Search for articles matching keywords with relevance scores."""
        query = query.lower()
        keywords = set(re.findall(r'\b\w{3,15}\b', query))

        coin = None
        if symbol:
            coin = self._extract_base_coin(symbol).upper()

        scores: List[Tuple[int, float]] = []
        current_time = datetime.now().timestamp()

        for i, article in enumerate(news_database):
            score = self._calculate_article_relevance(
                article, keywords, query, coin, current_time,
                category_word_map or {}, important_categories or set()
            )
            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def _calculate_article_relevance(self, article: Dict[str, Any], keywords: Set[str],
                                   query: str, coin: Optional[str],
                                   current_time: float, category_word_map: Dict[str, str],
                                   important_categories: Set[str]) -> float:
        """Calculate article relevance score based on various factors."""
        # Extract article content
        content = self._extract_article_content(article)
        
        # Calculate base scores
        keyword_score = self._calculate_keyword_score(keywords, content)
        category_score = self._calculate_category_score(query, content.categories, category_word_map)
        coin_score = self._calculate_coin_score(coin, content) if coin else 0.0
        importance_score = self._calculate_importance_score(content.categories, important_categories)
        
        # Apply recency weighting
        pub_time = self._get_article_timestamp(article)
        recency = self._calculate_recency_factor(current_time, pub_time)
        
        base_score = keyword_score + category_score + coin_score + importance_score
        final_score = base_score * (0.3 + 0.7 * recency)
        
        # Special boost for market overview
        if article.get('id') == 'market_overview':
            final_score += 10
        
        return final_score
    
    def _extract_article_content(self, article: Dict[str, Any]):
        """Extract and normalize article content for scoring."""
        from collections import namedtuple
        ArticleContent = namedtuple('ArticleContent', ['title', 'body', 'categories', 'tags', 'detected_coins'])
        
        return ArticleContent(
            title=article.get('title', '').lower(),
            body=article.get('body', '').lower(),
            categories=article.get('categories', '').lower(),
            tags=article.get('tags', '').lower(),
            detected_coins=article.get('detected_coins', '').lower()
        )
    
    def _calculate_keyword_score(self, keywords: Set[str], content) -> float:
        """Calculate score based on keyword matches."""
        score = 0.0
        for keyword in keywords:
            if keyword in content.title:
                score += 10
            if keyword in content.body:
                score += 3
            if keyword in content.categories:
                score += 5
            if keyword in content.tags:
                score += 4
        return score
    
    def _calculate_category_score(self, query: str, categories: str, category_word_map: Dict[str, str]) -> float:
        """Calculate score based on category word mapping."""
        score = 0.0
        for word, category in category_word_map.items():
            if word in query and category.lower() in categories:
                score += 5
        return score
    
    def _calculate_coin_score(self, coin: str, content) -> float:
        """Calculate score based on coin-specific matches."""
        coin_lower = coin.lower()
        score = 0.0
        
        # Category matches
        if coin_lower in content.categories:
            score += 15
        
        # Title/body regex matches
        if re.search(rf'\b{re.escape(coin_lower)}\b', content.title):
            score += 15
        if re.search(rf'\b{re.escape(coin_lower)}\b', content.body):
            score += 5
        
        # Detected coins
        if coin_lower in content.detected_coins:
            score += 8
        
        # Special title patterns
        if content.title.startswith(coin_lower) or f"{coin_lower} price" in content.title:
            score += 20
        
        return score
    
    def _calculate_importance_score(self, categories: str, important_categories: Set[str]) -> float:
        """Calculate score based on important categories."""
        score = 0.0
        for category in important_categories:
            if category.lower() in categories:
                score += 3
        return score
    
    def _calculate_recency_factor(self, current_time: float, pub_time: float) -> float:
        """Calculate recency weighting factor."""
        time_diff = current_time - pub_time
        return max(0.0, 1.0 - (time_diff / (24 * 3600)))

    def _get_article_timestamp(self, article: Dict[str, Any]) -> float:
        """Extract timestamp from article in a consistent format."""
        pub_time = 0.0
        published_on = article.get('published_on', 0)

        if isinstance(published_on, (int, float)):
            pub_time = float(published_on)
        elif isinstance(published_on, str):
            try:
                if published_on.endswith('Z'):
                    published_on = published_on[:-1] + '+00:00'
                pub_time = datetime.fromisoformat(published_on).timestamp()
            except ValueError:
                try:
                    self.logger.warning(f"Could not parse timestamp string: {published_on}")
                    pub_time = 0.0
                except Exception as e:
                    self.logger.error(f"Error parsing timestamp string '{published_on}': {e}")
                    pub_time = 0.0
        elif published_on is None:
            pub_time = 0.0
        else:
            self.logger.warning(f"Unexpected type for published_on: {type(published_on)}, value: {published_on}")
            pub_time = 0.0
        return pub_time
    
    def _extract_base_coin(self, symbol: str) -> str:
        """Extract base coin from trading pair symbol."""
        if '/' in symbol:
            base = symbol.split('/')[0]
        else:
            base = symbol
        return base
    
    def add_articles_to_context(self, indices: List[int], news_database: List[Dict[str, Any]],
                               max_tokens: int, k: int) -> Tuple[str, int]:
        """Add articles to context with token limiting."""
        context_parts = []
        total_tokens = 0
        articles_added = 0
        self.latest_article_urls = {}
        
        for idx in indices:
            if idx >= len(news_database):
                continue

            article = news_database[idx]

            published_date = self._format_article_date(article)

            title = article.get('title', 'No Title')
            source = article.get('source', 'Unknown Source')

            article_text = f"## {title}\n"
            article_text += f"**Source:** {source} | **Date:** {published_date}\n\n"

            body = article.get('body', '')
            if body:
                paragraphs = body.split('\n\n')[:5]
                summary = '\n\n'.join(paragraphs)
                if len(summary) > 2500:
                    summary = summary[:2500] + "..."
                article_text += f"{summary}\n\n"

            categories = article.get('categories', '')
            tags = article.get('tags', '')
            if categories or tags:
                article_text += f"**Topics:** {categories} | {tags}\n\n"

            article_tokens = self.token_counter.count_tokens(article_text)
            if total_tokens + article_tokens <= max_tokens:
                context_parts.append(article_text)
                total_tokens += article_tokens
                articles_added += 1

                if 'url' in article:
                    self.latest_article_urls[title] = article['url']
            else:
                break

            if articles_added >= k:
                break

        return "".join(context_parts), total_tokens

    def _format_article_date(self, article: Dict[str, Any]) -> str:
        """Format article date in a consistent way."""
        published_date = "Unknown Date"
        published_on = article.get('published_on', 0)

        try:
            if isinstance(published_on, (int, float)) and published_on > 0:
                dt_object = datetime.fromtimestamp(published_on)
                published_date = dt_object.strftime('%Y-%m-%d')
            elif isinstance(published_on, str):
                if published_on.endswith('Z'):
                    published_on = published_on[:-1] + '+00:00'
                dt_object = datetime.fromisoformat(published_on)
                published_date = dt_object.strftime('%Y-%m-%d')
        except (ValueError, TypeError, OSError) as e:
            self.logger.warning(f"Could not format date for article: {article.get('id', 'N/A')}, value: {published_on}, error: {e}")

        return published_date
    
    def get_latest_article_urls(self) -> Dict[str, str]:
        """Get the latest article URLs from the last context build."""
        return self.latest_article_urls.copy()
