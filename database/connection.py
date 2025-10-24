"""
Database connection and utility functions for Credit Agricole Document Management System
Handles SQLite database connections with proper error handling and connection pooling
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from datetime import datetime

# Database configuration
DATABASE_PATH = "Credit-Agricole.db"
DEFAULT_TIMEOUT = 30.0  # seconds

class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass

def get_database_connection(db_path: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT) -> sqlite3.Connection:
    """
    Get a SQLite database connection with proper configuration
    
    Args:
        db_path (Optional[str]): Path to database file, defaults to Credit-Agricole.db
        timeout (float): Connection timeout in seconds
        
    Returns:
        sqlite3.Connection: Configured database connection
        
    Raises:
        DatabaseError: If connection fails
    """
    if db_path is None:
        db_path = DATABASE_PATH
    
    try:
        # Check if database file exists
        if not os.path.exists(db_path):
            raise DatabaseError(f"Database file not found: {db_path}")
        
        # Create connection with proper configuration
        conn = sqlite3.connect(
            db_path,
            timeout=timeout,
            check_same_thread=False  # Allow multi-threaded access
        )
        
        # Configure connection for better performance and functionality
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
        conn.execute("PRAGMA synchronous = NORMAL")  # Better performance
        
        return conn
        
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to connect to database: {e}")
    except Exception as e:
        raise DatabaseError(f"Unexpected error connecting to database: {e}")

@contextmanager
def get_db_cursor(db_path: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
    """
    Context manager for database operations with automatic connection handling
    
    Args:
        db_path (Optional[str]): Path to database file
        timeout (float): Connection timeout in seconds
        
    Yields:
        sqlite3.Cursor: Database cursor for operations
        
    Example:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM Candidates")
            results = cursor.fetchall()
    """
    conn = None
    try:
        conn = get_database_connection(db_path, timeout)
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise DatabaseError(f"Database operation failed: {e}")
    finally:
        if conn:
            conn.close()

def execute_query(query: str, params: tuple = (), db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dictionaries
    
    Args:
        query (str): SQL SELECT query
        params (tuple): Query parameters
        db_path (Optional[str]): Database file path
        
    Returns:
        List[Dict[str, Any]]: Query results
        
    Example:
        results = execute_query("SELECT * FROM Candidates WHERE email = ?", ("john@example.com",))
    """
    try:
        with get_db_cursor(db_path) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert sqlite3.Row objects to dictionaries
            return [dict(row) for row in rows]
            
    except Exception as e:
        raise DatabaseError(f"Query execution failed: {e}")

def execute_insert(query: str, params: tuple = (), db_path: Optional[str] = None) -> int:
    """
    Execute an INSERT query and return the last inserted row ID
    
    Args:
        query (str): SQL INSERT query
        params (tuple): Query parameters
        db_path (Optional[str]): Database file path
        
    Returns:
        int: Last inserted row ID
        
    Example:
        candidate_id = execute_insert(
            "INSERT INTO Candidates (first_name, last_name, email) VALUES (?, ?, ?)",
            ("John", "Doe", "john@example.com")
        )
    """
    try:
        with get_db_cursor(db_path) as cursor:
            cursor.execute(query, params)
            return cursor.lastrowid
            
    except Exception as e:
        raise DatabaseError(f"Insert operation failed: {e}")

def execute_update(query: str, params: tuple = (), db_path: Optional[str] = None) -> int:
    """
    Execute an UPDATE or DELETE query and return the number of affected rows
    
    Args:
        query (str): SQL UPDATE/DELETE query
        params (tuple): Query parameters
        db_path (Optional[str]): Database file path
        
    Returns:
        int: Number of affected rows
        
    Example:
        affected = execute_update(
            "UPDATE Candidates SET file_status = ? WHERE id = ?",
            ("uploaded", 123)
        )
    """
    try:
        with get_db_cursor(db_path) as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
            
    except Exception as e:
        raise DatabaseError(f"Update operation failed: {e}")

def check_database_health() -> Dict[str, Any]:
    """
    Check database health and return status information
    
    Returns:
        Dict[str, Any]: Database health status
    """
    try:
        with get_db_cursor() as cursor:
            # Check if database is accessible
            cursor.execute("SELECT 1")
            
            # Get table counts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            table_counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_counts[table] = count
            
            # Get database file size
            db_size = os.path.getsize(DATABASE_PATH) if os.path.exists(DATABASE_PATH) else 0
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "database_path": DATABASE_PATH,
                "database_size_bytes": db_size,
                "total_tables": len(tables),
                "table_names": tables,
                "table_counts": table_counts
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

def create_uploads_directory() -> bool:
    """
    Create uploads directory structure for file storage
    
    Returns:
        bool: True if directory created/exists, False otherwise
    """
    try:
        uploads_dir = "uploads"
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
            # Create .gitkeep file to preserve directory in git
            with open(os.path.join(uploads_dir, ".gitkeep"), "w") as f:
                f.write("# Keep this directory in git\n")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create uploads directory: {e}")
        return False

# Utility functions for common database operations
def get_candidate_by_id(candidate_id: int) -> Optional[Dict[str, Any]]:
    """Get candidate by ID"""
    results = execute_query("SELECT * FROM Candidates WHERE id = ?", (candidate_id,))
    return results[0] if results else None

def get_candidate_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get candidate by email"""
    results = execute_query("SELECT * FROM Candidates WHERE email = ?", (email,))
    return results[0] if results else None

def get_documents_by_candidate(candidate_id: int) -> List[Dict[str, Any]]:
    """Get all documents for a candidate"""
    return execute_query("SELECT * FROM Documents WHERE candidate_id = ? ORDER BY upload_date", (candidate_id,))

if __name__ == "__main__":
    # Test database connection and health
    print("🔍 Testing database connection...")
    
    try:
        health = check_database_health()
        print(f"✅ Database status: {health['status']}")
        print(f"📊 Database size: {health.get('database_size_bytes', 0)} bytes")
        print(f"📋 Tables found: {health.get('total_tables', 0)}")
        
        if health.get('table_names'):
            print("📝 Table list:")
            for table in health['table_names']:
                count = health.get('table_counts', {}).get(table, 0)
                print(f"   - {table}: {count} records")
        
        # Create uploads directory
        if create_uploads_directory():
            print("📁 Uploads directory ready")
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")