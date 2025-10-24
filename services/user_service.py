"""
User Service for Credit Agricole Document Management System
Handles candidate profile management operations (Create, Read, Update, Delete)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from database.connection import execute_query, execute_insert, execute_update, get_candidate_by_id, get_candidate_by_email
from models.pydantic_models import (
    CandidateCreate, CandidateUpdate, CandidateResponse, 
    FileStatus, CreatedResponse, UpdatedResponse, DeletedResponse
)

class UserService:
    """Service class for managing candidate/user operations"""
    
    @staticmethod
    def create_candidate(candidate_data: CandidateCreate) -> CandidateResponse:
        """
        Create a new candidate profile
        
        Args:
            candidate_data (CandidateCreate): Candidate information
            
        Returns:
            CandidateResponse: Created candidate information
            
        Raises:
            HTTPException: If email already exists or creation fails
        """
        try:
            # Check if email already exists
            existing_candidate = get_candidate_by_email(candidate_data.email)
            if existing_candidate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Candidate with email {candidate_data.email} already exists"
                )
            
            # Insert new candidate
            candidate_id = execute_insert(
                """INSERT INTO Candidates 
                   (first_name, last_name, email, phone, address, file_status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    candidate_data.first_name,
                    candidate_data.last_name,
                    candidate_data.email,
                    candidate_data.phone,
                    candidate_data.address,
                    FileStatus.NO_FILE.value,
                    datetime.now(),
                    datetime.now()
                )
            )
            
            # Retrieve and return the created candidate
            created_candidate = get_candidate_by_id(candidate_id)
            if not created_candidate:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve created candidate"
                )
            
            return CandidateResponse(**created_candidate)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create candidate: {str(e)}"
            )
    
    @staticmethod
    def get_candidate(candidate_id: int) -> CandidateResponse:
        """
        Get candidate by ID
        
        Args:
            candidate_id (int): Candidate ID
            
        Returns:
            CandidateResponse: Candidate information
            
        Raises:
            HTTPException: If candidate not found
        """
        try:
            candidate = get_candidate_by_id(candidate_id)
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with ID {candidate_id} not found"
                )
            
            return CandidateResponse(**candidate)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve candidate: {str(e)}"
            )
    
    @staticmethod
    def get_candidate_by_email_service(email: str) -> CandidateResponse:
        """
        Get candidate by email
        
        Args:
            email (str): Candidate email
            
        Returns:
            CandidateResponse: Candidate information
            
        Raises:
            HTTPException: If candidate not found
        """
        try:
            candidate = get_candidate_by_email(email)
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with email {email} not found"
                )
            
            return CandidateResponse(**candidate)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve candidate: {str(e)}"
            )
    
    @staticmethod
    def update_candidate(candidate_id: int, update_data: CandidateUpdate) -> CandidateResponse:
        """
        Update candidate information
        
        Args:
            candidate_id (int): Candidate ID
            update_data (CandidateUpdate): Updated candidate information
            
        Returns:
            CandidateResponse: Updated candidate information
            
        Raises:
            HTTPException: If candidate not found or update fails
        """
        try:
            # Check if candidate exists
            existing_candidate = get_candidate_by_id(candidate_id)
            if not existing_candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with ID {candidate_id} not found"
                )
            
            # Build update query for only provided fields
            update_fields = []
            update_values = []
            
            if update_data.first_name is not None:
                update_fields.append("first_name = ?")
                update_values.append(update_data.first_name)
            
            if update_data.last_name is not None:
                update_fields.append("last_name = ?")
                update_values.append(update_data.last_name)
            
            if update_data.email is not None:
                # Check if new email already exists (for different candidate)
                email_check = get_candidate_by_email(update_data.email)
                if email_check and email_check['id'] != candidate_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Email {update_data.email} is already in use"
                    )
                update_fields.append("email = ?")
                update_values.append(update_data.email)
            
            if update_data.phone is not None:
                update_fields.append("phone = ?")
                update_values.append(update_data.phone)
            
            if update_data.address is not None:
                update_fields.append("address = ?")
                update_values.append(update_data.address)
            
            if not update_fields:
                # No fields to update, return current candidate
                return CandidateResponse(**existing_candidate)
            
            # Add updated_at timestamp
            update_fields.append("updated_at = ?")
            update_values.append(datetime.now())
            update_values.append(candidate_id)  # for WHERE clause
            
            # Execute update
            update_query = f"UPDATE Candidates SET {', '.join(update_fields)} WHERE id = ?"
            affected_rows = execute_update(update_query, tuple(update_values))
            
            if affected_rows == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update candidate"
                )
            
            # Return updated candidate
            updated_candidate = get_candidate_by_id(candidate_id)
            return CandidateResponse(**updated_candidate)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update candidate: {str(e)}"
            )
    
    @staticmethod
    def delete_candidate(candidate_id: int) -> DeletedResponse:
        """
        Delete candidate and all associated data
        
        Args:
            candidate_id (int): Candidate ID
            
        Returns:
            DeletedResponse: Deletion confirmation
            
        Raises:
            HTTPException: If candidate not found or deletion fails
        """
        try:
            # Check if candidate exists
            existing_candidate = get_candidate_by_id(candidate_id)
            if not existing_candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with ID {candidate_id} not found"
                )
            
            # Delete candidate (CASCADE will handle related records)
            affected_rows = execute_update(
                "DELETE FROM Candidates WHERE id = ?",
                (candidate_id,)
            )
            
            if affected_rows == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete candidate"
                )
            
            return DeletedResponse(
                success=True,
                message=f"Candidate {existing_candidate['first_name']} {existing_candidate['last_name']} deleted successfully",
                deleted_count=affected_rows
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete candidate: {str(e)}"
            )
    
    @staticmethod
    def list_candidates(
        page: int = 1, 
        per_page: int = 20, 
        email_filter: Optional[str] = None,
        file_status_filter: Optional[FileStatus] = None
    ) -> Dict[str, Any]:
        """
        List candidates with pagination and filtering
        
        Args:
            page (int): Page number (1-based)
            per_page (int): Items per page
            email_filter (Optional[str]): Filter by email substring
            file_status_filter (Optional[FileStatus]): Filter by file status
            
        Returns:
            Dict[str, Any]: Paginated candidate list
        """
        try:
            # Build WHERE clause for filters
            where_conditions = []
            where_values = []
            
            if email_filter:
                where_conditions.append("email LIKE ?")
                where_values.append(f"%{email_filter}%")
            
            if file_status_filter:
                where_conditions.append("file_status = ?")
                where_values.append(file_status_filter.value)
            
            where_clause = ""
            if where_conditions:
                where_clause = f"WHERE {' AND '.join(where_conditions)}"
            
            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM Candidates {where_clause}"
            count_result = execute_query(count_query, tuple(where_values))
            total_items = count_result[0]['total'] if count_result else 0
            
            # Calculate pagination
            offset = (page - 1) * per_page
            total_pages = (total_items + per_page - 1) // per_page
            
            # Get paginated results
            data_query = f"""
                SELECT * FROM Candidates 
                {where_clause}
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """
            candidates = execute_query(
                data_query, 
                tuple(where_values + [per_page, offset])
            )
            
            # Convert to response models
            candidate_responses = [CandidateResponse(**candidate) for candidate in candidates]
            
            return {
                "page": page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
                "data": candidate_responses
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list candidates: {str(e)}"
            )
    
    @staticmethod
    def update_file_status(candidate_id: int, new_status: FileStatus) -> UpdatedResponse:
        """
        Update candidate's file status
        
        Args:
            candidate_id (int): Candidate ID
            new_status (FileStatus): New file status
            
        Returns:
            UpdatedResponse: Update confirmation
            
        Raises:
            HTTPException: If candidate not found or update fails
        """
        try:
            # Check if candidate exists
            existing_candidate = get_candidate_by_id(candidate_id)
            if not existing_candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with ID {candidate_id} not found"
                )
            
            # Update file status
            affected_rows = execute_update(
                "UPDATE Candidates SET file_status = ?, updated_at = ? WHERE id = ?",
                (new_status.value, datetime.now(), candidate_id)
            )
            
            if affected_rows == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update file status"
                )
            
            return UpdatedResponse(
                success=True,
                message=f"File status updated to {new_status.value}",
                affected_rows=affected_rows
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update file status: {str(e)}"
            )