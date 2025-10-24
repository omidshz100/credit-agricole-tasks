"""
Extraction Service for Credit Agricole Document Management System
Handles PDF content extraction with history tracking
"""

import time
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime
from fastapi import HTTPException, status
from io import BytesIO

# PDF processing libraries will be imported dynamically
# This allows the service to work even if libraries are not installed
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PyPDF2 = None
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    pdfplumber = None
    PDFPLUMBER_AVAILABLE = False

from database.connection import (
    execute_query, execute_insert, execute_update, get_candidate_by_id
)
from models.pydantic_models import (
    ExtractionRequest, ExtractionResponse, ExtractionStatus
)
from services.file_access_service import FileAccessService

class ExtractionService:
    """Service class for PDF content extraction operations"""
    
    # Configuration
    MAX_EXTRACTION_TIME_MS = 30000  # 30 seconds
    MIN_CONTENT_LENGTH = 10  # Minimum characters to consider valid extraction
    
    @classmethod
    def _extract_text_with_pypdf2(cls, file_path: str) -> Tuple[str, str]:
        """
        Extract text using PyPDF2 library
        
        Args:
            file_path (str): Path to PDF file
            
        Returns:
            Tuple[str, str]: (extracted_text, method_used)
        """
        if not PYPDF2_AVAILABLE:
            raise Exception("PyPDF2 library not available")
            
        try:
            extracted_text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n\n"
            
            return extracted_text.strip(), "pypdf2"
            
        except Exception as e:
            raise Exception(f"PyPDF2 extraction failed: {str(e)}")
    
    @classmethod
    def _extract_text_with_pdfplumber(cls, file_path: str) -> Tuple[str, str]:
        """
        Extract text using pdfplumber library (fallback method)
        
        Args:
            file_path (str): Path to PDF file
            
        Returns:
            Tuple[str, str]: (extracted_text, method_used)
        """
        if not PDFPLUMBER_AVAILABLE:
            raise Exception("pdfplumber library not available")
            
        try:
            extracted_text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n\n"
            
            return extracted_text.strip(), "pdfplumber"
            
        except Exception as e:
            raise Exception(f"pdfplumber extraction failed: {str(e)}")
    
    @classmethod
    def _extract_text_basic(cls, file_path: str) -> Tuple[str, str]:
        """
        Basic text extraction fallback when PDF libraries are not available
        
        Args:
            file_path (str): Path to PDF file
            
        Returns:
            Tuple[str, str]: (extracted_text, method_used)
        """
        # This is a placeholder for basic extraction
        # In a real implementation, you might use other methods or return a message
        return f"PDF extraction requires PyPDF2 or pdfplumber libraries. File: {file_path}", "basic_fallback"
    
    @classmethod
    def _extract_text_from_pdf(cls, file_path: str) -> Tuple[str, str]:
        """
        Extract text from PDF using multiple methods with fallback
        
        Args:
            file_path (str): Path to PDF file
            
        Returns:
            Tuple[str, str]: (extracted_text, method_used)
            
        Raises:
            Exception: If all extraction methods fail
        """
        # Check if any PDF libraries are available
        if not PYPDF2_AVAILABLE and not PDFPLUMBER_AVAILABLE:
            return cls._extract_text_basic(file_path)
        
        # Try PyPDF2 first (faster)
        if PYPDF2_AVAILABLE:
            try:
                text, method = cls._extract_text_with_pypdf2(file_path)
                if len(text) >= cls.MIN_CONTENT_LENGTH:
                    return text, method
            except Exception:
                pass  # Try next method
        
        # Try pdfplumber as fallback (more reliable but slower)
        if PDFPLUMBER_AVAILABLE:
            try:
                text, method = cls._extract_text_with_pdfplumber(file_path)
                if len(text) >= cls.MIN_CONTENT_LENGTH:
                    return text, method
            except Exception:
                pass  # Try next method if we add more
        
        # If we get here, all methods failed
        raise Exception("All PDF extraction methods failed to extract meaningful content")
    
    @classmethod
    def _create_extraction_history_record(
        cls,
        candidate_id: int,
        document_id: int,
        extraction_status: ExtractionStatus,
        processing_time_ms: Optional[int] = None,
        extracted_content_length: Optional[int] = None,
        error_message: Optional[str] = None,
        extraction_method: str = "pdf_text_extraction",
        retry_attempt: int = 1
    ) -> int:
        """
        Create extraction history record
        
        Args:
            candidate_id (int): Candidate ID
            document_id (int): Document ID
            extraction_status (ExtractionStatus): Status of extraction
            processing_time_ms (Optional[int]): Processing time in milliseconds
            extracted_content_length (Optional[int]): Length of extracted content
            error_message (Optional[str]): Error message if failed
            extraction_method (str): Method used for extraction
            retry_attempt (int): Retry attempt number
            
        Returns:
            int: Extraction history ID
        """
        history_id = execute_insert(
            """INSERT INTO Extraction_History 
               (candidate_id, document_id, extraction_timestamp, extraction_status,
                processing_time_ms, extracted_content_length, error_message, 
                retry_attempt, extraction_method)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id, document_id, datetime.now(), extraction_status.value,
                processing_time_ms, extracted_content_length, error_message,
                retry_attempt, extraction_method
            )
        )
        return history_id
    
    @classmethod
    def _store_extracted_content(
        cls,
        document_id: int,
        extracted_text: str,
        extraction_method: str
    ) -> None:
        """
        Store extracted content in database
        
        Args:
            document_id (int): Document ID
            extracted_text (str): Extracted text content
            extraction_method (str): Method used for extraction
        """
        # Check if content already exists
        existing_content = execute_query(
            "SELECT id FROM Document_Content WHERE document_id = ?",
            (document_id,)
        )
        
        content_length = len(extracted_text)
        
        if existing_content:
            # Update existing record
            execute_update(
                """UPDATE Document_Content 
                   SET extracted_text = ?, content_length = ?, 
                       extraction_method = ?, created_at = ?
                   WHERE document_id = ?""",
                (extracted_text, content_length, extraction_method, datetime.now(), document_id)
            )
        else:
            # Create new record
            execute_insert(
                """INSERT INTO Document_Content 
                   (document_id, extracted_text, content_length, 
                    extraction_method, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (document_id, extracted_text, content_length, extraction_method, datetime.now())
            )
    
    @classmethod
    def _update_document_extraction_status(cls, document_id: int, extracted: bool) -> None:
        """
        Update document extraction status
        
        Args:
            document_id (int): Document ID
            extracted (bool): Whether extraction was successful
        """
        extraction_date = datetime.now() if extracted else None
        execute_update(
            "UPDATE Documents SET is_extracted = ?, extraction_date = ? WHERE id = ?",
            (extracted, extraction_date, document_id)
        )
    
    @classmethod
    def extract_document_content(
        cls, 
        candidate_id: int, 
        request: ExtractionRequest
    ) -> ExtractionResponse:
        """
        Extract content from a specific document
        
        Args:
            candidate_id (int): Candidate ID
            request (ExtractionRequest): Extraction request parameters
            
        Returns:
            ExtractionResponse: Extraction operation result
            
        Raises:
            HTTPException: If document not found or extraction fails
        """
        start_time = time.time()
        document_id = request.document_id
        
        try:
            # Validate candidate exists
            candidate = get_candidate_by_id(candidate_id)
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with ID {candidate_id} not found"
                )
            
            # Get document info and validate it belongs to the candidate
            try:
                doc_info = FileAccessService.get_document_info(candidate_id, document_id)
            except HTTPException as e:
                if e.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Document with ID {document_id} not found for candidate {candidate_id}"
                    )
                raise
            
            # Check if already extracted and not forcing re-extraction
            if doc_info.is_extracted and not request.force_re_extract:
                # Create history record for "already extracted" status
                history_id = cls._create_extraction_history_record(
                    candidate_id, document_id, ExtractionStatus.ALREADY_EXTRACTED,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                
                return ExtractionResponse(
                    operation_id=history_id,
                    candidate_id=candidate_id,
                    document_id=document_id,
                    status=ExtractionStatus.ALREADY_EXTRACTED,
                    message="Document already extracted. Use force_re_extract=true to re-extract.",
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    extraction_date=doc_info.extraction_date
                )
            
            # Get file path
            file_path = FileAccessService._get_file_path(candidate_id, doc_info.stored_filename)
            
            # Check if file exists on disk
            import os
            if not os.path.exists(file_path):
                error_msg = "PDF file not found on disk"
                history_id = cls._create_extraction_history_record(
                    candidate_id, document_id, ExtractionStatus.FAILED,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    error_message=error_msg
                )
                
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_msg
                )
            
            # Perform extraction
            try:
                extracted_text, extraction_method = cls._extract_text_from_pdf(file_path)
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                # Check if extraction timed out
                if processing_time_ms > cls.MAX_EXTRACTION_TIME_MS:
                    error_msg = f"Extraction timed out after {processing_time_ms}ms"
                    history_id = cls._create_extraction_history_record(
                        candidate_id, document_id, ExtractionStatus.FAILED,
                        processing_time_ms=processing_time_ms,
                        error_message=error_msg
                    )
                    
                    raise HTTPException(
                        status_code=status.HTTP_408_REQUEST_TIMEOUT,
                        detail=error_msg
                    )
                
                # Store extracted content
                cls._store_extracted_content(document_id, extracted_text, extraction_method)
                
                # Update document status
                cls._update_document_extraction_status(document_id, True)
                
                # Create successful history record
                content_length = len(extracted_text)
                history_id = cls._create_extraction_history_record(
                    candidate_id, document_id, ExtractionStatus.SUCCESS,
                    processing_time_ms=processing_time_ms,
                    extracted_content_length=content_length,
                    extraction_method=extraction_method
                )
                
                return ExtractionResponse(
                    operation_id=history_id,
                    candidate_id=candidate_id,
                    document_id=document_id,
                    status=ExtractionStatus.SUCCESS,
                    message=f"Content extracted successfully using {extraction_method}",
                    processing_time_ms=processing_time_ms,
                    extracted_content_length=content_length,
                    extraction_date=datetime.now()
                )
                
            except Exception as extraction_error:
                processing_time_ms = int((time.time() - start_time) * 1000)
                error_msg = str(extraction_error)
                
                # Create failed history record
                history_id = cls._create_extraction_history_record(
                    candidate_id, document_id, ExtractionStatus.FAILED,
                    processing_time_ms=processing_time_ms,
                    error_message=error_msg
                )
                
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"PDF content extraction failed: {error_msg}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            # Create failed history record
            try:
                history_id = cls._create_extraction_history_record(
                    candidate_id, document_id, ExtractionStatus.FAILED,
                    processing_time_ms=processing_time_ms,
                    error_message=error_msg
                )
            except:
                pass  # Don't fail the response if history recording fails
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Extraction operation failed: {error_msg}"
            )
    
    @classmethod
    def get_extraction_history(
        cls,
        candidate_id: Optional[int] = None,
        document_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get extraction history records
        
        Args:
            candidate_id (Optional[int]): Filter by candidate ID
            document_id (Optional[int]): Filter by document ID
            limit (int): Maximum records to return
            
        Returns:
            List[Dict[str, Any]]: Extraction history records
        """
        try:
            where_conditions = []
            query_params = []
            
            if candidate_id:
                where_conditions.append("eh.candidate_id = ?")
                query_params.append(candidate_id)
            
            if document_id:
                where_conditions.append("eh.document_id = ?")
                query_params.append(document_id)
            
            where_clause = ""
            if where_conditions:
                where_clause = f"WHERE {' AND '.join(where_conditions)}"
            
            query_params.append(limit)
            
            query = f"""
                SELECT eh.*, c.first_name, c.last_name, c.email, 
                       d.original_filename
                FROM Extraction_History eh
                JOIN Candidates c ON eh.candidate_id = c.id
                JOIN Documents d ON eh.document_id = d.id
                {where_clause}
                ORDER BY eh.extraction_timestamp DESC
                LIMIT ?
            """
            
            return execute_query(query, tuple(query_params))
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve extraction history: {str(e)}"
            )
    
    @classmethod
    def get_extraction_statistics(cls) -> Dict[str, Any]:
        """
        Get extraction statistics across all documents
        
        Returns:
            Dict[str, Any]: Extraction statistics
        """
        try:
            # Overall statistics
            overall_stats = execute_query("""
                SELECT 
                    COUNT(*) as total_extractions,
                    SUM(CASE WHEN extraction_status = 'success' THEN 1 ELSE 0 END) as successful_extractions,
                    SUM(CASE WHEN extraction_status = 'failed' THEN 1 ELSE 0 END) as failed_extractions,
                    AVG(CASE WHEN extraction_status = 'success' THEN processing_time_ms END) as avg_processing_time_ms,
                    AVG(CASE WHEN extraction_status = 'success' THEN extracted_content_length END) as avg_content_length
                FROM Extraction_History
            """)[0]
            
            # Method breakdown
            method_stats = execute_query("""
                SELECT extraction_method, COUNT(*) as count,
                       AVG(processing_time_ms) as avg_time_ms
                FROM Extraction_History 
                WHERE extraction_status = 'success'
                GROUP BY extraction_method
                ORDER BY count DESC
            """)
            
            # Recent activity (last 7 days)
            recent_activity = execute_query("""
                SELECT DATE(extraction_timestamp) as date, 
                       COUNT(*) as extractions,
                       SUM(CASE WHEN extraction_status = 'success' THEN 1 ELSE 0 END) as successful
                FROM Extraction_History 
                WHERE extraction_timestamp >= datetime('now', '-7 days')
                GROUP BY DATE(extraction_timestamp)
                ORDER BY date DESC
            """)
            
            # Documents needing extraction
            pending_extractions = execute_query("""
                SELECT COUNT(*) as count
                FROM Documents 
                WHERE is_extracted = 0
            """)[0]
            
            return {
                "overall": overall_stats,
                "success_rate": (
                    (overall_stats['successful_extractions'] / overall_stats['total_extractions'] * 100)
                    if overall_stats['total_extractions'] > 0 else 0
                ),
                "method_breakdown": {row['extraction_method']: row for row in method_stats},
                "recent_activity": recent_activity,
                "pending_extractions": pending_extractions['count'],
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve extraction statistics: {str(e)}"
            )
    
    @classmethod
    def retry_failed_extraction(
        cls,
        candidate_id: int,
        document_id: int,
        retry_attempt: int = 1
    ) -> ExtractionResponse:
        """
        Retry extraction for a failed document
        
        Args:
            candidate_id (int): Candidate ID
            document_id (int): Document ID
            retry_attempt (int): Retry attempt number
            
        Returns:
            ExtractionResponse: Retry extraction result
        """
        # Create extraction request with force re-extract
        request = ExtractionRequest(
            document_id=document_id,
            force_re_extract=True
        )
        
        # Perform extraction with retry attempt tracking
        try:
            response = cls.extract_document_content(candidate_id, request)
            
            # Update retry attempt in history if successful
            if response.status == ExtractionStatus.SUCCESS:
                execute_update(
                    "UPDATE Extraction_History SET retry_attempt = ? WHERE id = ?",
                    (retry_attempt, response.operation_id)
                )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Retry extraction failed: {str(e)}"
            )