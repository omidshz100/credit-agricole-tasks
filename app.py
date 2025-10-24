"""
Credit Agricole Document Management System API
Main FastAPI application with all endpoints for candidate and document management
"""

import os
from fastapi import FastAPI, HTTPException, status, UploadFile, File, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import http_exception_handler
from typing import List, Optional, Dict, Any
from datetime import datetime

# Import our services and models
from database.connection import check_database_health, create_uploads_directory
from database.schemas import create_all_tables, check_tables_exist
from models.pydantic_models import (
    # Candidate models
    CandidateCreate, CandidateUpdate, CandidateResponse,
    # File models
    FileUploadResponse, FileListResponse, DocumentInfo, DocumentContent,
    FileDownloadResponse, ExtractionRequest, ExtractionResponse,
    # Utility models
    APIStatus, ErrorResponse, DocumentFilter, PaginationParams,
    SuccessResponse, CreatedResponse, UpdatedResponse, DeletedResponse
)
from services.user_service import UserService
from services.file_upload_service import FileUploadService
from services.file_access_service import FileAccessService
from services.extraction_service import ExtractionService

# Initialize FastAPI app
app = FastAPI(
    title="Credit Agricole Document Management API",
    description="Document management system for candidate files with content extraction",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print("🚀 Starting Credit Agricole Document Management API...")
    
    # Check if database tables exist, create if missing
    table_status = check_tables_exist()
    missing_tables = [table for table, exists in table_status.items() if not exists and table != 'Attendance']
    
    if missing_tables:
        print(f"📊 Creating missing tables: {', '.join(missing_tables)}")
        create_all_tables()
    else:
        print("✅ All database tables exist")
    
    # Ensure uploads directory exists
    create_uploads_directory()
    print("📁 Uploads directory ready")
    
    # Check database health
    health = check_database_health()
    if health.get('status') == 'healthy':
        print(f"✅ Database healthy - {health.get('total_tables', 0)} tables found")
    else:
        print(f"⚠️ Database health check failed: {health.get('error', 'Unknown error')}")
    
    print("🎉 API startup complete!")

# Global exception handler
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

# Helper function to get request info
def get_request_info(request: Request) -> Dict[str, str]:
    """Extract request information for logging"""
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown")
    }

# ============================================================================
# HEALTH CHECK AND STATUS ENDPOINTS
# ============================================================================

@app.get("/", response_model=APIStatus)
async def root():
    """API status and health check"""
    try:
        db_health = check_database_health()
        return APIStatus(
            service_name="Credit Agricole Document Management API",
            version="1.0.0",
            status="healthy" if db_health.get('status') == 'healthy' else "degraded",
            timestamp=datetime.now(),
            database_status=db_health if db_health.get('status') == 'healthy' else None
        )
    except Exception as e:
        return APIStatus(
            status="unhealthy",
            timestamp=datetime.now()
        )

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return check_database_health()

# ============================================================================
# CANDIDATE/USER MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/candidates", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(candidate_data: CandidateCreate):
    """Create a new candidate profile"""
    return UserService.create_candidate(candidate_data)

@app.get("/api/candidates/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(candidate_id: int):
    """Get candidate by ID"""
    return UserService.get_candidate(candidate_id)

@app.get("/api/candidates", response_model=Dict[str, Any])
async def list_candidates(
    page: int = 1,
    per_page: int = 20,
    email_filter: Optional[str] = None,
    file_status_filter: Optional[str] = None
):
    """List candidates with pagination and filtering"""
    from models.pydantic_models import FileStatus
    
    # Convert file_status_filter string to enum if provided
    file_status_enum = None
    if file_status_filter:
        try:
            file_status_enum = FileStatus(file_status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file_status_filter. Must be one of: {[e.value for e in FileStatus]}"
            )
    
    return UserService.list_candidates(page, per_page, email_filter, file_status_enum)

@app.put("/api/candidates/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(candidate_id: int, update_data: CandidateUpdate):
    """Update candidate information"""
    return UserService.update_candidate(candidate_id, update_data)

@app.delete("/api/candidates/{candidate_id}", response_model=DeletedResponse)
async def delete_candidate(candidate_id: int):
    """Delete candidate and all associated data"""
    return UserService.delete_candidate(candidate_id)

# ============================================================================
# FILE UPLOAD ENDPOINTS
# ============================================================================

@app.post("/api/candidates/{candidate_id}/upload-files", response_model=FileUploadResponse)
async def upload_files(
    candidate_id: int,
    request: Request,
    files: List[UploadFile] = File(...)
):
    """Upload multiple PDF files for a candidate"""
    request_info = get_request_info(request)
    return FileUploadService.upload_files(candidate_id, files, request_info)

@app.get("/api/upload-history")
async def get_upload_history(
    candidate_id: Optional[int] = None,
    limit: int = 50
):
    """Get upload history records"""
    return FileUploadService.get_upload_history(candidate_id, limit)

@app.get("/api/upload-history/{history_id}/details")
async def get_upload_details(history_id: int):
    """Get detailed upload information for a specific upload operation"""
    return FileUploadService.get_upload_details(history_id)

# ============================================================================
# FILE ACCESS ENDPOINTS
# ============================================================================

@app.get("/api/candidates/{candidate_id}/files", response_model=FileListResponse)
async def list_candidate_files(
    candidate_id: int,
    extracted_only: Optional[bool] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    filename_contains: Optional[str] = None
):
    """List all files for a candidate with optional filtering"""
    filters = DocumentFilter(
        extracted_only=extracted_only,
        date_from=date_from,
        date_to=date_to,
        filename_contains=filename_contains
    ) if any([extracted_only is not None, date_from, date_to, filename_contains]) else None
    
    return FileAccessService.list_candidate_files(candidate_id, filters)

@app.get("/api/candidates/{candidate_id}/files/{document_id}", response_model=DocumentInfo)
async def get_document_info(candidate_id: int, document_id: int):
    """Get information about a specific document"""
    return FileAccessService.get_document_info(candidate_id, document_id)

@app.get("/api/candidates/{candidate_id}/files/{document_id}/download")
async def download_file(candidate_id: int, document_id: int):
    """Download a specific file"""
    return FileAccessService.download_file(candidate_id, document_id)

@app.get("/api/candidates/{candidate_id}/files/{document_id}/download-info", response_model=FileDownloadResponse)
async def get_file_download_info(candidate_id: int, document_id: int):
    """Get download information for a file without downloading"""
    return FileAccessService.get_file_download_info(candidate_id, document_id)

@app.get("/api/candidates/{candidate_id}/files/{document_id}/content", response_model=DocumentContent)
async def get_document_content(candidate_id: int, document_id: int):
    """Get extracted content for a document"""
    return FileAccessService.get_document_content(candidate_id, document_id)

@app.get("/api/candidates/{candidate_id}/files-summary")
async def get_candidate_file_summary(candidate_id: int):
    """Get file summary statistics for a candidate"""
    return FileAccessService.get_candidate_file_summary(candidate_id)

@app.delete("/api/candidates/{candidate_id}/files/{document_id}")
async def delete_document(candidate_id: int, document_id: int):
    """Delete a document and its associated files"""
    return FileAccessService.delete_document(candidate_id, document_id)

# ============================================================================
# CONTENT EXTRACTION ENDPOINTS
# ============================================================================

@app.post("/api/candidates/{candidate_id}/extract-document", response_model=ExtractionResponse)
async def extract_document_content(candidate_id: int, request: ExtractionRequest):
    """Extract content from a specific document"""
    return ExtractionService.extract_document_content(candidate_id, request)

@app.get("/api/extraction-history")
async def get_extraction_history(
    candidate_id: Optional[int] = None,
    document_id: Optional[int] = None,
    limit: int = 50
):
    """Get extraction history records"""
    return ExtractionService.get_extraction_history(candidate_id, document_id, limit)

@app.get("/api/extraction-statistics")
async def get_extraction_statistics():
    """Get extraction statistics across all documents"""
    return ExtractionService.get_extraction_statistics()

@app.post("/api/candidates/{candidate_id}/documents/{document_id}/retry-extraction", response_model=ExtractionResponse)
async def retry_failed_extraction(candidate_id: int, document_id: int, retry_attempt: int = 1):
    """Retry extraction for a failed document"""
    return ExtractionService.retry_failed_extraction(candidate_id, document_id, retry_attempt)

# ============================================================================
# SEARCH ENDPOINTS
# ============================================================================

@app.get("/api/search/documents")
async def search_documents(
    search_term: str,
    candidate_id: Optional[int] = None,
    extracted_only: bool = True,
    limit: int = 50
):
    """Search through document content"""
    return FileAccessService.search_documents(search_term, candidate_id, extracted_only, limit)

# ============================================================================
# ADMIN/UTILITY ENDPOINTS
# ============================================================================

@app.get("/api/admin/database-tables")
async def get_database_tables():
    """Get database table information"""
    return check_tables_exist()

@app.post("/api/admin/create-tables")
async def create_database_tables():
    """Create missing database tables"""
    try:
        success = create_all_tables()
        if success:
            return SuccessResponse(message="Database tables created successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create database tables"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating tables: {str(e)}"
        )

# ============================================================================
# MAIN APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("🏃‍♂️ Running Credit Agricole Document Management API directly...")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("📊 Database Status: http://localhost:8000/")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )