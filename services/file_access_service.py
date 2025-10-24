"""
File Access Service for Credit Agricole Document Management System
Handles file listing, downloading, and content retrieval operations
"""

import os
import mimetypes
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException, status, Response
from fastapi.responses import FileResponse

from database.connection import (
    execute_query, get_candidate_by_id, get_documents_by_candidate
)
from models.pydantic_models import (
    FileListResponse, DocumentInfo, DocumentContent, FileDownloadResponse,
    DocumentFilter, FileStatus
)

class FileAccessService:
    """Service class for file access operations"""
    
    UPLOADS_DIR = "uploads"
    
    @classmethod
    def _build_download_url(cls, candidate_id: int, document_id: int) -> str:
        """Build download URL for a document"""
        return f"/api/candidates/{candidate_id}/files/{document_id}/download"
    
    @classmethod
    def _get_file_path(cls, candidate_id: int, stored_filename: str) -> str:
        """Get full file path for a stored file"""
        return os.path.join(cls.UPLOADS_DIR, f"user_{candidate_id}", stored_filename)
    
    @classmethod
    def list_candidate_files(
        cls, 
        candidate_id: int,
        filters: Optional[DocumentFilter] = None
    ) -> FileListResponse:
        """
        List all files for a candidate with optional filtering
        
        Args:
            candidate_id (int): Candidate ID
            filters (Optional[DocumentFilter]): Filtering options
            
        Returns:
            FileListResponse: List of candidate files
            
        Raises:
            HTTPException: If candidate not found or query fails
        """
        try:
            # Validate candidate exists
            candidate = get_candidate_by_id(candidate_id)
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with ID {candidate_id} not found"
                )
            
            # Build query with filters
            where_conditions = ["candidate_id = ?"]
            query_params = [candidate_id]
            
            if filters:
                if filters.extracted_only is not None:
                    where_conditions.append("is_extracted = ?")
                    query_params.append(filters.extracted_only)
                
                if filters.date_from:
                    where_conditions.append("upload_date >= ?")
                    query_params.append(filters.date_from)
                
                if filters.date_to:
                    where_conditions.append("upload_date <= ?")
                    query_params.append(filters.date_to)
                
                if filters.filename_contains:
                    where_conditions.append("original_filename LIKE ?")
                    query_params.append(f"%{filters.filename_contains}%")
            
            where_clause = " AND ".join(where_conditions)
            
            # Execute query
            query = f"""
                SELECT id, original_filename, stored_filename, file_size, 
                       upload_date, is_extracted, extraction_date
                FROM Documents 
                WHERE {where_clause}
                ORDER BY upload_date DESC
            """
            
            documents = execute_query(query, tuple(query_params))
            
            # Convert to response format
            document_infos = []
            for doc in documents:
                document_info = DocumentInfo(
                    document_id=doc['id'],
                    original_filename=doc['original_filename'],
                    stored_filename=doc['stored_filename'],
                    file_size=doc['file_size'],
                    upload_date=doc['upload_date'],
                    is_extracted=bool(doc['is_extracted']),
                    extraction_date=doc['extraction_date'],
                    download_url=cls._build_download_url(candidate_id, doc['id'])
                )
                document_infos.append(document_info)
            
            return FileListResponse(
                candidate_id=candidate_id,
                file_status=FileStatus(candidate['file_status']),
                total_files=len(document_infos),
                files=document_infos
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list candidate files: {str(e)}"
            )
    
    @classmethod
    def get_document_info(cls, candidate_id: int, document_id: int) -> DocumentInfo:
        """
        Get information about a specific document
        
        Args:
            candidate_id (int): Candidate ID
            document_id (int): Document ID
            
        Returns:
            DocumentInfo: Document information
            
        Raises:
            HTTPException: If document not found or access denied
        """
        try:
            # Validate candidate exists
            candidate = get_candidate_by_id(candidate_id)
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with ID {candidate_id} not found"
                )
            
            # Get document
            documents = execute_query(
                """SELECT id, original_filename, stored_filename, file_size, 
                          upload_date, is_extracted, extraction_date
                   FROM Documents 
                   WHERE id = ? AND candidate_id = ?""",
                (document_id, candidate_id)
            )
            
            if not documents:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with ID {document_id} not found for candidate {candidate_id}"
                )
            
            doc = documents[0]
            return DocumentInfo(
                document_id=doc['id'],
                original_filename=doc['original_filename'],
                stored_filename=doc['stored_filename'],
                file_size=doc['file_size'],
                upload_date=doc['upload_date'],
                is_extracted=bool(doc['is_extracted']),
                extraction_date=doc['extraction_date'],
                download_url=cls._build_download_url(candidate_id, doc['id'])
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get document info: {str(e)}"
            )
    
    @classmethod
    def download_file(cls, candidate_id: int, document_id: int) -> FileResponse:
        """
        Download a specific file
        
        Args:
            candidate_id (int): Candidate ID
            document_id (int): Document ID
            
        Returns:
            FileResponse: File download response
            
        Raises:
            HTTPException: If file not found or access denied
        """
        try:
            # Get document info first (this validates candidate and document exist)
            doc_info = cls.get_document_info(candidate_id, document_id)
            
            # Build file path
            file_path = cls._get_file_path(candidate_id, doc_info.stored_filename)
            
            # Check if file exists on disk
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found on disk"
                )
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/pdf'
            
            # Return file response
            return FileResponse(
                path=file_path,
                filename=doc_info.original_filename,
                media_type=mime_type,
                headers={
                    "Content-Disposition": f"attachment; filename=\"{doc_info.original_filename}\"",
                    "Content-Length": str(doc_info.file_size)
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download file: {str(e)}"
            )
    
    @classmethod
    def get_file_download_info(cls, candidate_id: int, document_id: int) -> FileDownloadResponse:
        """
        Get download information for a file without actually downloading it
        
        Args:
            candidate_id (int): Candidate ID
            document_id (int): Document ID
            
        Returns:
            FileDownloadResponse: Download information
        """
        try:
            # Get document info
            doc_info = cls.get_document_info(candidate_id, document_id)
            
            # Check if file exists on disk
            file_path = cls._get_file_path(candidate_id, doc_info.stored_filename)
            file_exists = os.path.exists(file_path)
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/pdf'
            
            return FileDownloadResponse(
                document_id=document_id,
                original_filename=doc_info.original_filename,
                file_size=doc_info.file_size or 0,
                mime_type=mime_type,
                download_ready=file_exists
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get download info: {str(e)}"
            )
    
    @classmethod
    def get_document_content(cls, candidate_id: int, document_id: int) -> DocumentContent:
        """
        Get extracted content for a document
        
        Args:
            candidate_id (int): Candidate ID
            document_id (int): Document ID
            
        Returns:
            DocumentContent: Document content information
            
        Raises:
            HTTPException: If document not found or content not extracted
        """
        try:
            # Validate document exists and belongs to candidate
            doc_info = cls.get_document_info(candidate_id, document_id)
            
            # Get extracted content
            content_results = execute_query(
                """SELECT extracted_text, content_length, created_at
                   FROM Document_Content 
                   WHERE document_id = ?""",
                (document_id,)
            )
            
            extracted_text = None
            content_length = None
            extraction_date = None
            
            if content_results:
                content = content_results[0]
                extracted_text = content['extracted_text']
                content_length = content['content_length']
                extraction_date = content['created_at']
            elif not doc_info.is_extracted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document content has not been extracted yet"
                )
            
            return DocumentContent(
                document_id=document_id,
                original_filename=doc_info.original_filename,
                extracted_text=extracted_text,
                content_length=content_length,
                is_extracted=doc_info.is_extracted,
                extraction_date=extraction_date or doc_info.extraction_date
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get document content: {str(e)}"
            )
    
    @classmethod
    def get_candidate_file_summary(cls, candidate_id: int) -> Dict[str, Any]:
        """
        Get file summary statistics for a candidate
        
        Args:
            candidate_id (int): Candidate ID
            
        Returns:
            Dict[str, Any]: File summary statistics
        """
        try:
            # Validate candidate exists
            candidate = get_candidate_by_id(candidate_id)
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with ID {candidate_id} not found"
                )
            
            # Get file statistics
            stats_query = """
                SELECT 
                    COUNT(*) as total_files,
                    SUM(CASE WHEN is_extracted = 1 THEN 1 ELSE 0 END) as extracted_files,
                    SUM(file_size) as total_size_bytes,
                    MIN(upload_date) as first_upload,
                    MAX(upload_date) as last_upload
                FROM Documents 
                WHERE candidate_id = ?
            """
            
            stats = execute_query(stats_query, (candidate_id,))
            stats_data = stats[0] if stats else {}
            
            # Get file type breakdown (though we only support PDF for now)
            type_query = """
                SELECT mime_type, COUNT(*) as count
                FROM Documents 
                WHERE candidate_id = ? 
                GROUP BY mime_type
            """
            
            type_breakdown = execute_query(type_query, (candidate_id,))
            
            return {
                "candidate_id": candidate_id,
                "candidate_name": f"{candidate['first_name']} {candidate['last_name']}",
                "file_status": candidate['file_status'],
                "total_files": stats_data.get('total_files', 0),
                "extracted_files": stats_data.get('extracted_files', 0),
                "unextracted_files": stats_data.get('total_files', 0) - stats_data.get('extracted_files', 0),
                "total_size_bytes": stats_data.get('total_size_bytes', 0),
                "total_size_mb": round((stats_data.get('total_size_bytes', 0) / (1024 * 1024)), 2),
                "first_upload": stats_data.get('first_upload'),
                "last_upload": stats_data.get('last_upload'),
                "file_types": {row['mime_type']: row['count'] for row in type_breakdown}
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get file summary: {str(e)}"
            )
    
    @classmethod
    def search_documents(
        cls, 
        search_term: str,
        candidate_id: Optional[int] = None,
        extracted_only: bool = True,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search through document content
        
        Args:
            search_term (str): Search term
            candidate_id (Optional[int]): Filter by specific candidate
            extracted_only (bool): Only search extracted documents
            limit (int): Maximum results to return
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        try:
            # Build search query
            where_conditions = ["dc.extracted_text LIKE ?"]
            query_params = [f"%{search_term}%"]
            
            if candidate_id:
                where_conditions.append("d.candidate_id = ?")
                query_params.append(candidate_id)
            
            if extracted_only:
                where_conditions.append("d.is_extracted = 1")
            
            where_clause = " AND ".join(where_conditions)
            query_params.append(limit)
            
            search_query = f"""
                SELECT d.id, d.candidate_id, d.original_filename, d.upload_date,
                       c.first_name, c.last_name, c.email,
                       dc.content_length, dc.created_at as extraction_date
                FROM Documents d
                JOIN Candidates c ON d.candidate_id = c.id
                JOIN Document_Content dc ON d.id = dc.document_id
                WHERE {where_clause}
                ORDER BY d.upload_date DESC
                LIMIT ?
            """
            
            results = execute_query(search_query, tuple(query_params))
            
            # Add download URLs
            for result in results:
                result['download_url'] = cls._build_download_url(
                    result['candidate_id'], result['id']
                )
            
            return results
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Search failed: {str(e)}"
            )
    
    @classmethod
    def delete_document(cls, candidate_id: int, document_id: int) -> Dict[str, Any]:
        """
        Delete a document and its associated files
        
        Args:
            candidate_id (int): Candidate ID
            document_id (int): Document ID
            
        Returns:
            Dict[str, Any]: Deletion result
            
        Raises:
            HTTPException: If document not found or deletion fails
        """
        try:
            # Get document info first (validates access)
            doc_info = cls.get_document_info(candidate_id, document_id)
            
            # Delete physical file
            file_path = cls._get_file_path(candidate_id, doc_info.stored_filename)
            file_deleted = False
            if os.path.exists(file_path):
                os.remove(file_path)
                file_deleted = True
            
            # Delete database record (CASCADE will handle related records)
            from database.connection import execute_update
            affected_rows = execute_update(
                "DELETE FROM Documents WHERE id = ? AND candidate_id = ?",
                (document_id, candidate_id)
            )
            
            if affected_rows == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete document record"
                )
            
            # Update candidate file status if no more files
            remaining_files = execute_query(
                "SELECT COUNT(*) as count FROM Documents WHERE candidate_id = ?",
                (candidate_id,)
            )
            
            if remaining_files and remaining_files[0]['count'] == 0:
                from services.user_service import UserService
                UserService.update_file_status(candidate_id, FileStatus.NO_FILE)
            
            return {
                "success": True,
                "message": f"Document '{doc_info.original_filename}' deleted successfully",
                "document_id": document_id,
                "file_deleted": file_deleted,
                "database_records_deleted": affected_rows
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document: {str(e)}"
            )