"""
File Upload Service for Credit Agricole Document Management System
Handles multiple PDF file uploads with validation, storage, and history tracking
"""

import os
import shutil
import time
import mimetypes
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from fastapi import HTTPException, status, UploadFile
from pathlib import Path

from database.connection import (
    execute_query, execute_insert, execute_update, get_candidate_by_id
)
from models.pydantic_models import (
    FileUploadResponse, FileUploadDetail, FileUploadSummary, 
    OperationStatus, UploadStatus, FileStatus
)
from services.user_service import UserService

class FileUploadService:
    """Service class for handling file upload operations"""
    
    # Configuration constants
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    ALLOWED_MIME_TYPES = ['application/pdf']
    ALLOWED_EXTENSIONS = ['.pdf']
    UPLOADS_DIR = "uploads"
    MAX_FILES_PER_REQUEST = 10
    
    @classmethod
    def _ensure_uploads_directory(cls) -> None:
        """Ensure uploads directory exists"""
        if not os.path.exists(cls.UPLOADS_DIR):
            os.makedirs(cls.UPLOADS_DIR)
            # Create .gitkeep file
            with open(os.path.join(cls.UPLOADS_DIR, ".gitkeep"), "w") as f:
                f.write("# Keep this directory in git\n")
    
    @classmethod
    def _get_user_upload_dir(cls, candidate_id: int) -> str:
        """Get user-specific upload directory"""
        user_dir = os.path.join(cls.UPLOADS_DIR, f"user_{candidate_id}")
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        return user_dir
    
    @classmethod
    def _validate_file(cls, file: UploadFile) -> Tuple[bool, List[str]]:
        """
        Validate uploaded file
        
        Args:
            file (UploadFile): Uploaded file object
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in cls.ALLOWED_EXTENSIONS:
            errors.append(f"Invalid file extension. Only {', '.join(cls.ALLOWED_EXTENSIONS)} allowed")
        
        # Check file size
        if hasattr(file, 'size') and file.size:
            if file.size > cls.MAX_FILE_SIZE:
                size_mb = file.size / (1024 * 1024)
                max_mb = cls.MAX_FILE_SIZE / (1024 * 1024)
                errors.append(f"File size {size_mb:.1f}MB exceeds maximum {max_mb}MB")
        
        # Check MIME type
        content_type = file.content_type
        if content_type not in cls.ALLOWED_MIME_TYPES:
            errors.append(f"Invalid file type. Only PDF files are allowed")
        
        # Check filename
        if not file.filename or len(file.filename.strip()) == 0:
            errors.append("Filename cannot be empty")
        
        return len(errors) == 0, errors
    
    @classmethod
    def _generate_stored_filename(cls, candidate_id: int, document_id: int, original_filename: str) -> str:
        """
        Generate stored filename using our naming convention
        
        Args:
            candidate_id (int): Candidate ID
            document_id (int): Document ID
            original_filename (str): Original filename
            
        Returns:
            str: Generated filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(original_filename).suffix.lower()
        return f"user_{candidate_id}_doc_{document_id}_{timestamp}{file_ext}"
    
    @classmethod
    def _save_file(cls, file: UploadFile, file_path: str) -> int:
        """
        Save uploaded file to disk
        
        Args:
            file (UploadFile): Uploaded file
            file_path (str): Target file path
            
        Returns:
            int: File size in bytes
            
        Raises:
            Exception: If file save fails
        """
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Get actual file size
            return os.path.getsize(file_path)
            
        except Exception as e:
            # Clean up partial file if save failed
            if os.path.exists(file_path):
                os.remove(file_path)
            raise Exception(f"Failed to save file: {str(e)}")
    
    @classmethod
    def _create_upload_history_record(
        cls, 
        candidate_id: int, 
        total_files: int,
        request_info: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Create upload history record
        
        Args:
            candidate_id (int): Candidate ID
            total_files (int): Total files attempted
            request_info (Optional[Dict]): Request metadata
            
        Returns:
            int: Upload history ID
        """
        history_id = execute_insert(
            """INSERT INTO File_Upload_History 
               (candidate_id, operation_timestamp, total_files_attempted, 
                successful_uploads, failed_uploads, operation_status, 
                request_ip, user_agent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id,
                datetime.now(),
                total_files,
                0,  # Will be updated later
                0,  # Will be updated later
                OperationStatus.FAILED.value,  # Will be updated later
                request_info.get('ip') if request_info else None,
                request_info.get('user_agent') if request_info else None
            )
        )
        return history_id
    
    @classmethod
    def _update_upload_history(
        cls, 
        history_id: int, 
        successful: int, 
        failed: int, 
        error_summary: Optional[str] = None
    ) -> None:
        """Update upload history record with final results"""
        if failed == 0:
            operation_status = OperationStatus.SUCCESS.value
        elif successful == 0:
            operation_status = OperationStatus.FAILED.value
        else:
            operation_status = OperationStatus.PARTIAL_SUCCESS.value
        
        execute_update(
            """UPDATE File_Upload_History 
               SET successful_uploads = ?, failed_uploads = ?, 
                   operation_status = ?, error_summary = ?
               WHERE id = ?""",
            (successful, failed, operation_status, error_summary, history_id)
        )
    
    @classmethod
    def _create_upload_detail_record(
        cls,
        history_id: int,
        original_filename: str,
        stored_filename: Optional[str] = None,
        document_id: Optional[int] = None,
        file_size: Optional[int] = None,
        upload_status: UploadStatus = UploadStatus.FAILED,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        processing_time: Optional[int] = None
    ) -> int:
        """Create upload detail record"""
        return execute_insert(
            """INSERT INTO File_Upload_Details 
               (upload_history_id, original_filename, stored_filename, 
                document_id, file_size, upload_status, error_message, 
                error_code, processing_time_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                history_id, original_filename, stored_filename,
                document_id, file_size, upload_status.value,
                error_message, error_code, processing_time
            )
        )
    
    @classmethod
    def _create_document_record(
        cls,
        candidate_id: int,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_size: int
    ) -> int:
        """Create document record in database"""
        return execute_insert(
            """INSERT INTO Documents 
               (candidate_id, original_filename, stored_filename, 
                file_path, file_size, mime_type, is_extracted, upload_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id, original_filename, stored_filename,
                file_path, file_size, 'application/pdf', False, datetime.now()
            )
        )
    
    @classmethod
    def upload_files(
        cls, 
        candidate_id: int, 
        files: List[UploadFile],
        request_info: Optional[Dict[str, str]] = None
    ) -> FileUploadResponse:
        """
        Upload multiple files for a candidate
        
        Args:
            candidate_id (int): Candidate ID
            files (List[UploadFile]): List of uploaded files
            request_info (Optional[Dict]): Request metadata (IP, user agent, etc.)
            
        Returns:
            FileUploadResponse: Upload operation results
            
        Raises:
            HTTPException: If candidate not found or upload fails
        """
        start_time = time.time()
        
        try:
            # Validate candidate exists
            candidate = get_candidate_by_id(candidate_id)
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with ID {candidate_id} not found"
                )
            
            # Validate file count
            if len(files) > cls.MAX_FILES_PER_REQUEST:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Too many files. Maximum {cls.MAX_FILES_PER_REQUEST} files per request"
                )
            
            if len(files) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No files provided"
                )
            
            # Ensure upload directories exist
            cls._ensure_uploads_directory()
            user_upload_dir = cls._get_user_upload_dir(candidate_id)
            
            # Create upload history record
            history_id = cls._create_upload_history_record(
                candidate_id, len(files), request_info
            )
            
            # Process each file
            upload_results = []
            successful_uploads = 0
            failed_uploads = 0
            error_messages = []
            
            for file in files:
                file_start_time = time.time()
                result = cls._process_single_file(
                    file, candidate_id, user_upload_dir, history_id
                )
                file_processing_time = int((time.time() - file_start_time) * 1000)
                result['processing_time_ms'] = file_processing_time
                
                upload_results.append(result)
                
                if result['status'] == UploadStatus.SUCCESS:
                    successful_uploads += 1
                else:
                    failed_uploads += 1
                    if result.get('error_message'):
                        error_messages.append(f"{result['original_filename']}: {result['error_message']}")
            
            # Update upload history
            error_summary = "; ".join(error_messages) if error_messages else None
            cls._update_upload_history(
                history_id, successful_uploads, failed_uploads, error_summary
            )
            
            # Update candidate file status if any files uploaded successfully
            if successful_uploads > 0:
                UserService.update_file_status(candidate_id, FileStatus.UPLOADED)
            
            # Determine overall operation status
            if failed_uploads == 0:
                operation_status = OperationStatus.SUCCESS
                message = f"All {successful_uploads} files uploaded successfully"
            elif successful_uploads == 0:
                operation_status = OperationStatus.FAILED
                message = f"All {failed_uploads} files failed to upload"
            else:
                operation_status = OperationStatus.PARTIAL_SUCCESS
                message = f"{successful_uploads} files uploaded, {failed_uploads} failed"
            
            # Convert results to response models
            response_results = [
                FileUploadDetail(**result) for result in upload_results
            ]
            
            return FileUploadResponse(
                operation_id=history_id,
                candidate_id=candidate_id,
                status=operation_status,
                message=message,
                results=response_results,
                summary=FileUploadSummary(
                    total_files=len(files),
                    successful=successful_uploads,
                    failed=failed_uploads
                ),
                timestamp=datetime.now()
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File upload operation failed: {str(e)}"
            )
    
    @classmethod
    def _process_single_file(
        cls, 
        file: UploadFile, 
        candidate_id: int, 
        user_upload_dir: str, 
        history_id: int
    ) -> Dict[str, Any]:
        """
        Process a single uploaded file
        
        Args:
            file (UploadFile): File to process
            candidate_id (int): Candidate ID
            user_upload_dir (str): User upload directory
            history_id (int): Upload history ID
            
        Returns:
            Dict[str, Any]: Processing result
        """
        result = {
            'original_filename': file.filename,
            'stored_filename': None,
            'document_id': None,
            'file_size': None,
            'status': UploadStatus.FAILED,
            'message': '',
            'error_code': None
        }
        
        try:
            # Validate file
            is_valid, errors = cls._validate_file(file)
            if not is_valid:
                result['message'] = "; ".join(errors)
                result['error_code'] = 'VALIDATION_FAILED'
                cls._create_upload_detail_record(
                    history_id, file.filename, error_message=result['message'],
                    error_code=result['error_code']
                )
                return result
            
            # Create temporary document record to get ID for filename
            document_id = cls._create_document_record(
                candidate_id, file.filename, "temp", "temp", 0
            )
            
            # Generate stored filename
            stored_filename = cls._generate_stored_filename(
                candidate_id, document_id, file.filename
            )
            file_path = os.path.join(user_upload_dir, stored_filename)
            
            # Save file
            file_size = cls._save_file(file, file_path)
            
            # Update document record with correct information
            execute_update(
                """UPDATE Documents 
                   SET stored_filename = ?, file_path = ?, file_size = ?
                   WHERE id = ?""",
                (stored_filename, user_upload_dir, file_size, document_id)
            )
            
            # Create successful upload detail record
            cls._create_upload_detail_record(
                history_id, file.filename, stored_filename, document_id,
                file_size, UploadStatus.SUCCESS
            )
            
            result.update({
                'stored_filename': stored_filename,
                'document_id': document_id,
                'file_size': file_size,
                'status': UploadStatus.SUCCESS,
                'message': 'File uploaded successfully'
            })
            
        except Exception as e:
            # Clean up document record if it was created
            if result.get('document_id'):
                execute_update("DELETE FROM Documents WHERE id = ?", (result['document_id'],))
            
            result['message'] = str(e)
            result['error_code'] = 'UPLOAD_FAILED'
            
            cls._create_upload_detail_record(
                history_id, file.filename, error_message=result['message'],
                error_code=result['error_code']
            )
        
        return result
    
    @classmethod
    def get_upload_history(
        cls, 
        candidate_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get upload history records
        
        Args:
            candidate_id (Optional[int]): Filter by candidate ID
            limit (int): Maximum records to return
            
        Returns:
            List[Dict[str, Any]]: Upload history records
        """
        try:
            if candidate_id:
                query = """
                    SELECT fuh.*, c.first_name, c.last_name, c.email
                    FROM File_Upload_History fuh
                    JOIN Candidates c ON fuh.candidate_id = c.id
                    WHERE fuh.candidate_id = ?
                    ORDER BY fuh.operation_timestamp DESC
                    LIMIT ?
                """
                params = (candidate_id, limit)
            else:
                query = """
                    SELECT fuh.*, c.first_name, c.last_name, c.email
                    FROM File_Upload_History fuh
                    JOIN Candidates c ON fuh.candidate_id = c.id
                    ORDER BY fuh.operation_timestamp DESC
                    LIMIT ?
                """
                params = (limit,)
            
            return execute_query(query, params)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve upload history: {str(e)}"
            )
    
    @classmethod
    def get_upload_details(cls, history_id: int) -> List[Dict[str, Any]]:
        """
        Get detailed upload information for a specific upload operation
        
        Args:
            history_id (int): Upload history ID
            
        Returns:
            List[Dict[str, Any]]: Upload detail records
        """
        try:
            return execute_query(
                """SELECT * FROM File_Upload_Details 
                   WHERE upload_history_id = ? 
                   ORDER BY id""",
                (history_id,)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve upload details: {str(e)}"
            )