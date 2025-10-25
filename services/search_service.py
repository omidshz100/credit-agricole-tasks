"""
Advanced Search Service for Credit Agricole Document Management System
Provides intelligent document content search with ranking, highlighting, and analytics
"""

import re
import time
import math
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
from fastapi import HTTPException, status

from database.connection import execute_query, execute_insert, get_candidate_by_id
from models.pydantic_models import (
    SearchRequest, SearchResponse, SearchResult, SearchHighlight,
    SearchHistoryRecord, SearchStatistics
)

class SearchService:
    """Advanced search service with relevance ranking and highlighting"""
    
    # Configuration
    MIN_WORD_LENGTH = 2
    MAX_HIGHLIGHT_DISTANCE = 50  # Characters between highlights to merge
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'among', 'this', 'that',
        'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
        'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
        'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
        'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'whose', 'when', 'where',
        'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
        'too', 'very', 'can', 'will', 'just', 'should', 'now'
    }
    
    @classmethod
    def _preprocess_query(cls, query: str) -> Dict[str, Any]:
        """
        Preprocess search query into searchable components
        
        Args:
            query (str): Raw search query
            
        Returns:
            Dict[str, Any]: Processed query components
        """
        processed = {
            'original': query,
            'phrases': [],
            'words': [],
            'excluded_words': [],
            'is_phrase_search': False
        }
        
        # Extract phrases in quotes
        phrase_pattern = r'"([^"]*)"'
        phrases = re.findall(phrase_pattern, query)
        if phrases:
            processed['phrases'] = [phrase.strip().lower() for phrase in phrases if phrase.strip()]
            processed['is_phrase_search'] = True
            # Remove phrases from query for word processing
            query = re.sub(phrase_pattern, '', query)
        
        # Extract individual words
        words = re.findall(r'\b\w+\b', query.lower())
        
        # Filter words
        for word in words:
            if len(word) >= cls.MIN_WORD_LENGTH:
                if word.startswith('-'):
                    # Excluded word (e.g., -unwanted)
                    processed['excluded_words'].append(word[1:])
                elif word not in cls.STOP_WORDS:
                    processed['words'].append(word)
        
        return processed
    
    @classmethod
    def _calculate_relevance_score(
        cls, 
        content: str, 
        processed_query: Dict[str, Any], 
        document_length: int
    ) -> Tuple[float, int]:
        """
        Calculate relevance score for a document
        
        Args:
            content (str): Document content
            processed_query (Dict): Processed query components
            document_length (int): Length of document content
            
        Returns:
            Tuple[float, int]: (relevance_score, match_count)
        """
        content_lower = content.lower()
        total_score = 0.0
        total_matches = 0
        
        # Score phrase matches (higher weight)
        for phrase in processed_query['phrases']:
            phrase_count = len(re.findall(re.escape(phrase), content_lower))
            if phrase_count > 0:
                # Phrase matches get higher scores
                phrase_score = phrase_count * 10
                total_score += phrase_score
                total_matches += phrase_count
        
        # Score word matches
        for word in processed_query['words']:
            word_pattern = r'\b' + re.escape(word) + r'\b'
            word_matches = len(re.findall(word_pattern, content_lower))
            if word_matches > 0:
                # Calculate TF-IDF like score
                term_frequency = word_matches / len(content_lower.split())
                word_score = term_frequency * 100 * math.log(1 + word_matches)
                total_score += word_score
                total_matches += word_matches
        
        # Penalize excluded words
        for excluded_word in processed_query['excluded_words']:
            if excluded_word in content_lower:
                total_score *= 0.1  # Heavy penalty
        
        # Normalize by document length (longer docs get slight penalty)
        if document_length > 1000:
            length_factor = 1000 / document_length
            total_score *= (0.5 + 0.5 * length_factor)
        
        # Cap score at 100
        relevance_score = min(total_score, 100.0)
        
        return relevance_score, total_matches
    
    @classmethod
    def _generate_highlights(
        cls, 
        content: str, 
        processed_query: Dict[str, Any], 
        highlight_length: int,
        max_highlights: int = 3
    ) -> List[SearchHighlight]:
        """
        Generate highlighted text snippets
        
        Args:
            content (str): Document content
            processed_query (Dict): Processed query components
            highlight_length (int): Length of each highlight
            max_highlights (int): Maximum number of highlights
            
        Returns:
            List[SearchHighlight]: List of highlights
        """
        highlights = []
        content_lower = content.lower()
        found_positions = []
        
        # Find all match positions
        all_terms = processed_query['phrases'] + processed_query['words']
        
        for term in all_terms:
            if processed_query['is_phrase_search'] and term in processed_query['phrases']:
                # Exact phrase search
                pattern = re.escape(term)
            else:
                # Word boundary search
                pattern = r'\b' + re.escape(term) + r'\b'
            
            for match in re.finditer(pattern, content_lower):
                found_positions.append(match.start())
        
        if not found_positions:
            return highlights
        
        # Sort positions and merge nearby ones
        found_positions.sort()
        merged_positions = []
        
        for pos in found_positions:
            if not merged_positions or pos - merged_positions[-1] > cls.MAX_HIGHLIGHT_DISTANCE:
                merged_positions.append(pos)
        
        # Generate highlights
        for i, pos in enumerate(merged_positions[:max_highlights]):
            start = max(0, pos - highlight_length // 2)
            end = min(len(content), pos + highlight_length // 2)
            
            # Adjust to word boundaries
            while start > 0 and content[start] != ' ':
                start -= 1
            while end < len(content) and content[end] != ' ':
                end += 1
            
            highlight_text = content[start:end].strip()
            if start > 0:
                highlight_text = "..." + highlight_text
            if end < len(content):
                highlight_text = highlight_text + "..."
            
            highlights.append(SearchHighlight(
                text=highlight_text,
                start_position=start
            ))
        
        return highlights
    
    @classmethod
    def _record_search_history(
        cls,
        query: str,
        candidate_id: Optional[int],
        results_count: int,
        search_time_ms: int,
        search_type: str = "content_search"
    ) -> int:
        """Record search operation in history"""
        try:
            history_id = execute_insert(
                """INSERT INTO Search_History 
                   (query, candidate_id, results_count, search_time_ms, 
                    search_timestamp, search_type)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (query, candidate_id, results_count, search_time_ms, 
                 datetime.now(), search_type)
            )
            return history_id
        except Exception:
            # Don't fail search if history recording fails
            return 0
    
    @classmethod
    def search_documents(cls, search_request: SearchRequest) -> SearchResponse:
        """
        Perform advanced document content search
        
        Args:
            search_request (SearchRequest): Search parameters
            
        Returns:
            SearchResponse: Search results with ranking and highlights
            
        Raises:
            HTTPException: If search fails
        """
        start_time = time.time()
        
        try:
            # Validate candidate if specified
            if search_request.candidate_id:
                candidate = get_candidate_by_id(search_request.candidate_id)
                if not candidate:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Candidate with ID {search_request.candidate_id} not found"
                    )
            
            # Preprocess query
            processed_query = cls._preprocess_query(search_request.query)
            
            if not processed_query['words'] and not processed_query['phrases']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Search query must contain at least one valid search term"
                )
            
            # Build database query
            where_conditions = []
            query_params = []
            
            # Base condition - only search extracted documents if requested
            if search_request.extracted_only:
                where_conditions.append("d.is_extracted = 1")
            
            # Candidate filter
            if search_request.candidate_id:
                where_conditions.append("d.candidate_id = ?")
                query_params.append(search_request.candidate_id)
            
            # Content search conditions
            content_conditions = []
            
            # Add phrase search conditions
            for phrase in processed_query['phrases']:
                content_conditions.append("dc.extracted_text LIKE ?")
                query_params.append(f"%{phrase}%")
            
            # Add word search conditions
            for word in processed_query['words']:
                content_conditions.append("dc.extracted_text LIKE ?")
                query_params.append(f"%{word}%")
            
            if content_conditions:
                if processed_query['is_phrase_search']:
                    # For phrase search, require all conditions
                    where_conditions.append(f"({' AND '.join(content_conditions)})")
                else:
                    # For word search, any condition can match
                    where_conditions.append(f"({' OR '.join(content_conditions)})")
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Execute search query
            search_query = f"""
                SELECT d.id, d.candidate_id, d.original_filename, d.file_size,
                       d.upload_date, d.extraction_date,
                       c.first_name, c.last_name,
                       dc.extracted_text, dc.content_length
                FROM Documents d
                JOIN Candidates c ON d.candidate_id = c.id
                JOIN Document_Content dc ON d.id = dc.document_id
                WHERE {where_clause}
                ORDER BY d.upload_date DESC
            """
            
            documents = execute_query(search_query, tuple(query_params))
            
            # Calculate relevance and generate results
            search_results = []
            
            for doc in documents:
                relevance_score, match_count = cls._calculate_relevance_score(
                    doc['extracted_text'], processed_query, doc['content_length'] or 0
                )
                
                if relevance_score > 0:  # Only include documents with matches
                    # Generate highlights
                    highlights = []
                    if search_request.include_highlights:
                        highlights = cls._generate_highlights(
                            doc['extracted_text'], processed_query, 
                            search_request.highlight_length
                        )
                    
                    # Build download URL
                    download_url = f"/api/candidates/{doc['candidate_id']}/files/{doc['id']}/download"
                    
                    search_result = SearchResult(
                        document_id=doc['id'],
                        candidate_id=doc['candidate_id'],
                        candidate_name=f"{doc['first_name']} {doc['last_name']}",
                        original_filename=doc['original_filename'],
                        relevance_score=round(relevance_score, 2),
                        match_count=match_count,
                        highlights=highlights,
                        upload_date=doc['upload_date'],
                        extraction_date=doc['extraction_date'],
                        download_url=download_url,
                        file_size=doc['file_size']
                    )
                    search_results.append(search_result)
            
            # Sort by relevance score (descending)
            search_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Apply pagination
            total_results = len(search_results)
            start_idx = search_request.offset
            end_idx = start_idx + search_request.limit
            paginated_results = search_results[start_idx:end_idx]
            
            # Calculate pagination info
            page = (search_request.offset // search_request.limit) + 1
            total_pages = math.ceil(total_results / search_request.limit) if total_results > 0 else 1
            has_next = end_idx < total_results
            has_previous = search_request.offset > 0
            
            # Calculate search time
            search_time_ms = int((time.time() - start_time) * 1000)
            
            # Record search history
            cls._record_search_history(
                search_request.query, search_request.candidate_id, 
                total_results, search_time_ms
            )
            
            # Generate search suggestions (simple implementation)
            search_suggestions = cls._generate_search_suggestions(search_request.query)
            
            return SearchResponse(
                query=search_request.query,
                candidate_id=search_request.candidate_id,
                total_results=total_results,
                search_time_ms=search_time_ms,
                page=page,
                per_page=search_request.limit,
                total_pages=total_pages,
                has_next=has_next,
                has_previous=has_previous,
                results=paginated_results,
                search_suggestions=search_suggestions
            )
            
        except HTTPException:
            raise
        except Exception as e:
            # Record failed search
            search_time_ms = int((time.time() - start_time) * 1000)
            cls._record_search_history(
                search_request.query, search_request.candidate_id, 
                0, search_time_ms, "failed_search"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Search operation failed: {str(e)}"
            )
    
    @classmethod
    def _generate_search_suggestions(cls, query: str, limit: int = 5) -> List[str]:
        """Generate search suggestions based on query"""
        suggestions = []
        
        try:
            # Get similar queries from history
            similar_queries = execute_query(
                """SELECT DISTINCT query, COUNT(*) as usage_count
                   FROM Search_History 
                   WHERE query LIKE ? AND query != ?
                   GROUP BY query
                   ORDER BY usage_count DESC, query
                   LIMIT ?""",
                (f"%{query}%", query, limit)
            )
            
            suggestions = [row['query'] for row in similar_queries]
            
        except Exception:
            # Return empty suggestions if query fails
            pass
        
        return suggestions
    
    @classmethod
    def get_search_history(
        cls,
        candidate_id: Optional[int] = None,
        limit: int = 50
    ) -> List[SearchHistoryRecord]:
        """Get search history records"""
        try:
            if candidate_id:
                query = """
                    SELECT * FROM Search_History 
                    WHERE candidate_id = ?
                    ORDER BY search_timestamp DESC
                    LIMIT ?
                """
                params = (candidate_id, limit)
            else:
                query = """
                    SELECT * FROM Search_History 
                    ORDER BY search_timestamp DESC
                    LIMIT ?
                """
                params = (limit,)
            
            history_records = execute_query(query, params)
            
            return [SearchHistoryRecord(**record) for record in history_records]
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve search history: {str(e)}"
            )
    
    @classmethod
    def get_search_statistics(cls) -> SearchStatistics:
        """Get search usage statistics"""
        try:
            # Overall statistics
            overall_stats = execute_query("""
                SELECT 
                    COUNT(*) as total_searches,
                    COUNT(DISTINCT query) as unique_queries,
                    AVG(search_time_ms) as avg_search_time
                FROM Search_History
                WHERE search_type = 'content_search'
            """)[0]
            
            # Popular queries
            popular_queries = execute_query("""
                SELECT query, COUNT(*) as usage_count, AVG(results_count) as avg_results
                FROM Search_History 
                WHERE search_type = 'content_search'
                GROUP BY query
                ORDER BY usage_count DESC
                LIMIT 10
            """)
            
            # Search trends (last 7 days)
            search_trends = execute_query("""
                SELECT DATE(search_timestamp) as date, 
                       COUNT(*) as searches,
                       AVG(search_time_ms) as avg_time
                FROM Search_History 
                WHERE search_timestamp >= datetime('now', '-7 days')
                  AND search_type = 'content_search'
                GROUP BY DATE(search_timestamp)
                ORDER BY date DESC
            """)
            
            return SearchStatistics(
                total_searches=overall_stats['total_searches'],
                unique_queries=overall_stats['unique_queries'],
                average_search_time_ms=round(overall_stats['avg_search_time'] or 0, 2),
                popular_queries=[{
                    'query': row['query'],
                    'usage_count': row['usage_count'],
                    'avg_results': round(row['avg_results'], 1)
                } for row in popular_queries],
                search_trends=[{
                    'date': row['date'],
                    'searches': row['searches'],
                    'avg_time_ms': round(row['avg_time'], 1)
                } for row in search_trends],
                generated_at=datetime.now()
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve search statistics: {str(e)}"
            )
    
    @classmethod
    def quick_search(
        cls, 
        query: str, 
        candidate_id: Optional[int] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Simple quick search for basic queries
        
        Args:
            query (str): Search query
            candidate_id (Optional[int]): Filter by candidate
            limit (int): Maximum results
            
        Returns:
            List[Dict[str, Any]]: Basic search results
        """
        search_request = SearchRequest(
            query=query,
            candidate_id=candidate_id,
            limit=limit,
            include_highlights=False
        )
        
        search_response = cls.search_documents(search_request)
        
        # Return simplified results
        return [{
            'document_id': result.document_id,
            'candidate_name': result.candidate_name,
            'filename': result.original_filename,
            'relevance_score': result.relevance_score,
            'match_count': result.match_count
        } for result in search_response.results]