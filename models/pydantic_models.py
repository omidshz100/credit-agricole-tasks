"""
Pydantic models for Credit Agricole Document Management System API
Defines request and response models for all endpoints with proper validation
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Enums for status fields
class FileStatus(str, Enum):
    NO_FILE = "no-file"
    UPLOADED = "uploaded"
    PROCESSING = "processing"

class UploadStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"

class OperationStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"

class ExtractionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ALREADY_EXTRACTED = "already_extracted"

# Base models
class BaseResponse(BaseModel):
    """Base response model with common fields"""
    success: bool
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

# Candidate/User models
class CandidateCreate(BaseModel):
    """Request model for creating a new candidate"""
    first_name: str = Field(..., min_length=1, max_length=100, description="Candidate's first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Candidate's last name")
    email: EmailStr = Field(..., description="Candidate's email address")
    phone: Optional[str] = Field(None, max_length=20, description="Candidate's phone number")
    address: Optional[str] = Field(None, max_length=500, description="Candidate's address")
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise ValueError('Phone number must contain only digits, spaces, +, -, (, )')
        return v

class CandidateUpdate(BaseModel):
    """Request model for updating candidate information"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)

class CandidateResponse(BaseModel):
    """Response model for candidate information"""
    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    address: Optional[str]
    file_status: FileStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Document models
class DocumentInfo(BaseModel):
    """Document information model"""
    document_id: int
    original_filename: str
    stored_filename: str
    file_size: Optional[int]
    upload_date: datetime
    is_extracted: bool
    extraction_date: Optional[datetime]
    download_url: str

class DocumentContent(BaseModel):
    """Document content model"""
    document_id: int
    original_filename: str
    extracted_text: Optional[str]
    content_length: Optional[int]
    is_extracted: bool
    extraction_date: Optional[datetime]

# File upload models
class FileUploadDetail(BaseModel):
    """Individual file upload result"""
    original_filename: str
    stored_filename: Optional[str] = None
    document_id: Optional[int] = None
    file_size: Optional[int] = None
    status: UploadStatus
    message: str
    error_code: Optional[str] = None

class FileUploadSummary(BaseModel):
    """Upload operation summary"""
    total_files: int
    successful: int
    failed: int

class FileUploadResponse(BaseModel):
    """Response model for file upload operations"""
    operation_id: int
    candidate_id: int
    status: OperationStatus
    message: str
    results: List[FileUploadDetail]
    summary: FileUploadSummary
    timestamp: datetime = Field(default_factory=datetime.now)

# File access models
class FileListResponse(BaseModel):
    """Response model for listing candidate files"""
    candidate_id: int
    file_status: FileStatus
    total_files: int
    files: List[DocumentInfo]

class FileDownloadResponse(BaseModel):
    """Response model for file download information"""
    document_id: int
    original_filename: str
    file_size: int
    mime_type: str
    download_ready: bool

# Content extraction models
class ExtractionRequest(BaseModel):
    """Request model for content extraction"""
    document_id: int
    force_re_extract: bool = Field(False, description="Force re-extraction even if already extracted")

class ExtractionResponse(BaseModel):
    """Response model for content extraction operations"""
    operation_id: int
    candidate_id: int
    document_id: int
    status: ExtractionStatus
    message: str
    processing_time_ms: Optional[int] = None
    extracted_content_length: Optional[int] = None
    extraction_date: Optional[datetime] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# History models
class UploadHistoryRecord(BaseModel):
    """Upload history record"""
    id: int
    operation_timestamp: datetime
    total_files_attempted: int
    successful_uploads: int
    failed_uploads: int
    operation_status: OperationStatus
    
class UploadDetailRecord(BaseModel):
    """Upload detail record"""
    original_filename: str
    stored_filename: Optional[str]
    upload_status: UploadStatus
    error_message: Optional[str]
    error_code: Optional[str]
    processing_time_ms: Optional[int]

class ExtractionHistoryRecord(BaseModel):
    """Extraction history record"""
    id: int
    document_id: int
    extraction_timestamp: datetime
    extraction_status: ExtractionStatus
    processing_time_ms: Optional[int]
    extracted_content_length: Optional[int]
    error_message: Optional[str]
    retry_attempt: int

# Database health and status models
class DatabaseHealth(BaseModel):
    """Database health status model"""
    status: str
    timestamp: datetime
    database_path: str
    database_size_bytes: int
    total_tables: int
    table_names: List[str]
    table_counts: Dict[str, int]

class APIStatus(BaseModel):
    """API status model"""
    service_name: str = "Credit Agricole Document Management API"
    version: str = "1.0.0"
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    database_status: Optional[DatabaseHealth] = None

# Error models
class ErrorDetail(BaseModel):
    """Error detail model"""
    error_code: str
    error_message: str
    field: Optional[str] = None

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Validation models
class FileValidationResult(BaseModel):
    """File validation result"""
    filename: str
    is_valid: bool
    file_size: int
    mime_type: str
    errors: List[str] = []

class ValidationSummary(BaseModel):
    """Validation summary for multiple files"""
    total_files: int
    valid_files: int
    invalid_files: int
    results: List[FileValidationResult]

# Search and filter models
class DocumentFilter(BaseModel):
    """Document filtering options"""
    extracted_only: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    filename_contains: Optional[str] = None

class SearchRequest(BaseModel):
    """Advanced search request model"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    candidate_id: Optional[int] = Field(None, description="Search within specific candidate's documents")
    extracted_only: bool = Field(True, description="Search only extracted documents")
    limit: int = Field(20, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Results offset for pagination")
    include_highlights: bool = Field(True, description="Include text highlights in results")
    highlight_length: int = Field(150, ge=50, le=500, description="Length of highlight context")

class SearchHighlight(BaseModel):
    """Search result highlight"""
    text: str = Field(..., description="Highlighted text snippet")
    start_position: int = Field(..., description="Position in document where highlight starts")

class SearchResult(BaseModel):
    """Individual search result"""
    document_id: int
    candidate_id: int
    candidate_name: str
    original_filename: str
    relevance_score: float = Field(..., ge=0, le=100, description="Relevance score (0-100)")
    match_count: int = Field(..., ge=1, description="Number of matches found")
    highlights: List[SearchHighlight] = []
    upload_date: datetime
    extraction_date: Optional[datetime]
    download_url: str
    file_size: Optional[int]

class SearchResponse(BaseModel):
    """Search results response"""
    query: str
    candidate_id: Optional[int]
    total_results: int
    search_time_ms: int
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    total_pages: int
    has_next: bool
    has_previous: bool
    results: List[SearchResult]
    search_suggestions: List[str] = []

class SearchHistoryRecord(BaseModel):
    """Search history record"""
    id: int
    query: str
    candidate_id: Optional[int]
    results_count: int
    search_time_ms: int
    search_timestamp: datetime
    search_type: str

class SearchStatistics(BaseModel):
    """Search usage statistics"""
    total_searches: int
    unique_queries: int
    average_search_time_ms: float
    popular_queries: List[Dict[str, Any]]
    search_trends: List[Dict[str, Any]]
    generated_at: datetime

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")

class PaginatedResponse(BaseModel):
    """Paginated response model"""
    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool
    data: List[Any]

# Success response shortcuts
class SuccessResponse(BaseResponse):
    """Generic success response"""
    success: bool = True

class CreatedResponse(BaseResponse):
    """Resource created response"""
    success: bool = True
    resource_id: int

class UpdatedResponse(BaseResponse):
    """Resource updated response"""
    success: bool = True
    affected_rows: int

class DeletedResponse(BaseResponse):
    """Resource deleted response"""
    success: bool = True
    deleted_count: int