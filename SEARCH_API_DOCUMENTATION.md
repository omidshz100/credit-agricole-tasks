# Enhanced Search API Documentation
## Credit Agricole Document Management System

### Overview
The enhanced search system provides intelligent document content search with relevance ranking, text highlighting, analytics, and comprehensive search history tracking.

### 🚀 Key Features

- **Intelligent Relevance Scoring**: TF-IDF inspired algorithm with document length normalization
- **Text Highlighting**: Automatic extraction of relevant text snippets with search term highlighting
- **Phrase Search**: Support for exact phrase matching using quotes ("exact phrase")
- **Word Exclusion**: Exclude specific terms using minus operator (-unwanted)
- **Candidate Filtering**: Search within specific candidate's documents
- **Search Analytics**: Comprehensive tracking and statistics
- **Performance Optimized**: Database indexes for fast search operations

### 📝 API Endpoints

#### 1. Advanced Document Search
```http
POST /api/search/documents
```

**Request Body:**
```json
{
  "query": "software engineer iOS",
  "candidate_id": 2,
  "limit": 20,
  "offset": 0,
  "include_highlights": true,
  "highlight_length": 150,
  "extracted_only": true
}
```

**Response:**
```json
{
  "query": "software engineer iOS",
  "candidate_id": 2,
  "total_results": 3,
  "search_time_ms": 15,
  "page": 1,
  "per_page": 20,
  "total_pages": 1,
  "has_next": false,
  "has_previous": false,
  "results": [
    {
      "document_id": 5,
      "candidate_id": 2,
      "candidate_name": "John Doe",
      "original_filename": "John_Doe_CV.pdf",
      "relevance_score": 85.3,
      "match_count": 4,
      "highlights": [
        {
          "text": "...experienced software engineer with expertise in iOS development...",
          "start_position": 245
        }
      ],
      "upload_date": "2024-10-24T10:30:00",
      "extraction_date": "2024-10-24T10:35:00",
      "download_url": "/api/candidates/2/files/5/download",
      "file_size": 156789
    }
  ],
  "search_suggestions": [
    "software development",
    "iOS developer"
  ]
}
```

#### 2. Quick Search
```http
GET /api/search/documents/quick?query=python&candidate_id=2&limit=10
```

**Response:**
```json
[
  {
    "document_id": 3,
    "candidate_name": "Jane Smith",
    "filename": "resume.pdf",
    "relevance_score": 92.1,
    "match_count": 6
  }
]
```

#### 3. Search History
```http
GET /api/search/history?candidate_id=2&limit=50
```

**Response:**
```json
[
  {
    "id": 15,
    "query": "python django",
    "candidate_id": 2,
    "results_count": 3,
    "search_time_ms": 12,
    "search_timestamp": "2024-10-24T14:30:00",
    "search_type": "content_search"
  }
]
```

#### 4. Search Statistics & Analytics
```http
GET /api/search/statistics
```

**Response:**
```json
{
  "total_searches": 245,
  "unique_queries": 89,
  "average_search_time_ms": 18.5,
  "popular_queries": [
    {
      "query": "software engineer",
      "usage_count": 23,
      "avg_results": 4.2
    }
  ],
  "search_trends": [
    {
      "date": "2024-10-24",
      "searches": 34,
      "avg_time_ms": 15.2
    }
  ],
  "generated_at": "2024-10-24T16:45:00"
}
```

### 🔍 Search Query Syntax

#### Basic Search
```
javascript developer
```
Searches for documents containing both "javascript" and "developer"

#### Phrase Search
```
"senior software engineer"
```
Searches for the exact phrase "senior software engineer"

#### Exclusion Search
```
python -django
```
Searches for "python" but excludes documents containing "django"

#### Mixed Search
```
"full stack" javascript -junior
```
Searches for exact phrase "full stack" and "javascript", excluding "junior"

### 📊 Relevance Scoring

The search algorithm uses a sophisticated scoring system:

1. **Phrase Matches**: Higher weight (10x multiplier)
2. **Term Frequency**: More occurrences = higher score
3. **Document Length**: Normalized to prevent bias toward longer documents
4. **Word Boundaries**: Exact word matches preferred
5. **Exclusion Penalty**: Heavy penalty (90% reduction) for excluded terms

**Score Range**: 0-100 (higher is more relevant)

### 🎯 Highlighting System

- **Context Length**: Configurable highlight snippet length
- **Smart Boundaries**: Adjusts to word boundaries for readability
- **Multiple Highlights**: Up to 3 highlights per document
- **Merge Distance**: Nearby highlights are intelligently merged

### 📈 Analytics & Insights

#### Search History Tracking
- Every search is logged with timestamp and performance metrics
- Failed searches are tracked separately
- Candidate-specific search patterns

#### Performance Metrics
- Search execution time in milliseconds
- Result count tracking
- Query complexity analysis

#### Usage Statistics
- Most popular search terms
- Search frequency trends
- Average result counts per query type

### 🔧 Configuration Options

#### Search Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | **required** | Search terms or phrases |
| `candidate_id` | integer | null | Filter by specific candidate |
| `limit` | integer | 20 | Results per page (1-100) |
| `offset` | integer | 0 | Results to skip for pagination |
| `include_highlights` | boolean | false | Include text highlights |
| `highlight_length` | integer | 200 | Characters per highlight |
| `extracted_only` | boolean | true | Search only extracted documents |

#### Performance Tuning

- **Database Indexes**: Automatic indexing on `extracted_text` and search queries
- **Stop Words**: Common words filtered out for better relevance
- **Minimum Word Length**: Words shorter than 2 characters ignored
- **Cache Optimization**: Frequently searched terms may be cached

### 🚨 Error Handling

#### Common Error Scenarios

```json
{
  "detail": "Search query must contain at least one valid search term",
  "status_code": 400
}
```

```json
{
  "detail": "Candidate with ID 999 not found",
  "status_code": 404
}
```

```json
{
  "detail": "Search operation failed: Database connection error",
  "status_code": 500
}
```

### 🔄 Migration from Legacy Search

The old search endpoint is still available for backward compatibility:

```http
GET /api/search/documents/legacy?search_term=python&candidate_id=2
```

**Migration Path:**
1. Update clients to use `POST /api/search/documents`
2. Replace `search_term` parameter with `query` in request body
3. Update response handling for new structured format
4. Leverage new features like highlights and relevance scoring

### 💡 Best Practices

#### Efficient Searching
1. **Use Specific Terms**: More specific queries return better results
2. **Leverage Phrases**: Use quotes for exact phrase matching
3. **Filter by Candidate**: Reduces search scope and improves performance
4. **Pagination**: Use appropriate page sizes for better UX

#### Query Optimization
1. **Avoid Over-Broad Terms**: Terms like "the", "and" are filtered out
2. **Use Exclusions Wisely**: Exclude irrelevant terms to focus results
3. **Combine Techniques**: Mix phrases and individual terms for best results

#### Performance Considerations
1. **Limit Results**: Set appropriate limits for faster response times
2. **Skip Highlights**: Disable highlights for bulk/API operations
3. **Monitor Analytics**: Use search statistics to optimize common queries

### 🔧 Advanced Usage Examples

#### Complex Search Query
```json
{
  "query": "\"machine learning\" python -junior -intern",
  "candidate_id": null,
  "limit": 15,
  "include_highlights": true,
  "highlight_length": 120,
  "extracted_only": true
}
```

#### Bulk Search Analysis
```python
# Python example for analyzing search patterns
import requests

# Get search statistics
stats = requests.get("http://localhost:8000/api/search/statistics")
popular_queries = stats.json()["popular_queries"]

for query_info in popular_queries[:5]:
    query = query_info["query"]
    
    # Perform search with each popular query
    search_data = {
        "query": query,
        "limit": 10,
        "include_highlights": False
    }
    
    results = requests.post(
        "http://localhost:8000/api/search/documents",
        json=search_data
    )
    
    print(f"Query '{query}': {results.json()['total_results']} documents")
```

### 📚 Integration Examples

#### JavaScript/TypeScript
```typescript
interface SearchRequest {
  query: string;
  candidate_id?: number;
  limit?: number;
  offset?: number;
  include_highlights?: boolean;
  highlight_length?: number;
  extracted_only?: boolean;
}

async function searchDocuments(searchParams: SearchRequest) {
  const response = await fetch('/api/search/documents', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(searchParams)
  });
  
  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }
  
  return await response.json();
}

// Usage
const results = await searchDocuments({
  query: 'software engineer',
  include_highlights: true,
  limit: 20
});
```

#### Python Client
```python
import requests
from typing import Optional, List, Dict

class DocumentSearchClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def search(
        self,
        query: str,
        candidate_id: Optional[int] = None,
        limit: int = 20,
        include_highlights: bool = False
    ) -> Dict:
        """Perform document search"""
        search_data = {
            "query": query,
            "candidate_id": candidate_id,
            "limit": limit,
            "include_highlights": include_highlights
        }
        
        response = requests.post(
            f"{self.base_url}/api/search/documents",
            json=search_data
        )
        response.raise_for_status()
        return response.json()
    
    def get_search_history(self, limit: int = 50) -> List[Dict]:
        """Get search history"""
        response = requests.get(
            f"{self.base_url}/api/search/history",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()

# Usage
client = DocumentSearchClient()
results = client.search("python developer", include_highlights=True)
```

---

## Summary

The enhanced search system provides a comprehensive, production-ready solution for document content search with:

✅ **Intelligent Ranking**: Advanced relevance scoring algorithm  
✅ **Rich Highlighting**: Context-aware text snippets  
✅ **Flexible Queries**: Support for phrases, exclusions, and filters  
✅ **Analytics**: Complete search tracking and statistics  
✅ **Performance**: Optimized database queries with indexes  
✅ **Scalability**: Pagination and configurable result limits  
✅ **Error Handling**: Comprehensive error responses  
✅ **Backward Compatibility**: Legacy endpoint support  

This search system is ready for production use and can handle complex search requirements for the Credit Agricole document management system.