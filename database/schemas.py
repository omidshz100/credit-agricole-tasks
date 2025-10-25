"""
Database schema definitions for Credit Agricole Document Management System
This file contains all table creation scripts that extend the existing attendance system
"""

import sqlite3
from typing import Optional

def get_database_path() -> str:
    """Get the database file path"""
    return "Credit-Agricole.db"

def create_all_tables(db_path: Optional[str] = None) -> bool:
    """
    Create all new tables for the document management system
    Preserves existing Attendance table and adds new tables
    
    Returns:
        bool: True if all tables created successfully, False otherwise
    """
    if db_path is None:
        db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Candidates table - stores candidate profile information
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                address TEXT,
                file_status TEXT DEFAULT 'no-file' CHECK (file_status IN ('no-file', 'uploaded', 'processing')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Documents table - stores file metadata and extraction status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                mime_type TEXT DEFAULT 'application/pdf',
                is_extracted BOOLEAN DEFAULT FALSE,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                extraction_date TIMESTAMP NULL,
                FOREIGN KEY (candidate_id) REFERENCES Candidates(id) ON DELETE CASCADE
            )
        """)
        
        # 3. Document_Content table - stores extracted text content
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Document_Content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER UNIQUE NOT NULL,
                extracted_text TEXT,
                content_length INTEGER,
                extraction_method TEXT DEFAULT 'pdf_text_extraction',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES Documents(id) ON DELETE CASCADE
            )
        """)
        
        # 4. File_Upload_History table - tracks upload operations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS File_Upload_History (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                operation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_files_attempted INTEGER NOT NULL,
                successful_uploads INTEGER DEFAULT 0,
                failed_uploads INTEGER DEFAULT 0,
                operation_status TEXT CHECK (operation_status IN ('success', 'partial_success', 'failed')),
                request_ip TEXT,
                user_agent TEXT,
                error_summary TEXT,
                FOREIGN KEY (candidate_id) REFERENCES Candidates(id) ON DELETE CASCADE
            )
        """)
        
        # 5. File_Upload_Details table - per-file upload tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS File_Upload_Details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_history_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT,
                document_id INTEGER NULL,
                file_size INTEGER,
                upload_status TEXT CHECK (upload_status IN ('success', 'failed')),
                error_message TEXT,
                error_code TEXT,
                processing_time_ms INTEGER,
                FOREIGN KEY (upload_history_id) REFERENCES File_Upload_History(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES Documents(id) ON DELETE SET NULL
            )
        """)
        
        # 6. Extraction_History table - tracks content extraction operations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Extraction_History (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                extraction_status TEXT CHECK (extraction_status IN ('success', 'failed', 'already_extracted')),
                processing_time_ms INTEGER,
                extracted_content_length INTEGER,
                error_message TEXT,
                retry_attempt INTEGER DEFAULT 1,
                extraction_method TEXT DEFAULT 'pdf_text_extraction',
                FOREIGN KEY (candidate_id) REFERENCES Candidates(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES Documents(id) ON DELETE CASCADE
            )
        """)
        
        # 7. Search_History table - tracks search operations for analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Search_History (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                candidate_id INTEGER NULL,
                results_count INTEGER DEFAULT 0,
                search_time_ms INTEGER,
                search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                search_type TEXT DEFAULT 'content_search',
                FOREIGN KEY (candidate_id) REFERENCES Candidates(id) ON DELETE SET NULL
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_email ON Candidates(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_candidate_id ON Documents(candidate_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_extracted ON Documents(is_extracted)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_upload_history_candidate ON File_Upload_History(candidate_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_extraction_history_candidate ON Extraction_History(candidate_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_extraction_history_document ON Extraction_History(document_id)")
        
        # Search performance indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_document_content_text ON Document_Content(extracted_text)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_query ON Search_History(query)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_timestamp ON Search_History(search_timestamp)")
        
        conn.commit()
        conn.close()
        
        print("✅ All database tables created successfully!")
        print("📊 New tables added to Credit-Agricole.db:")
        print("   - Candidates (candidate profiles)")
        print("   - Documents (file metadata)")
        print("   - Document_Content (extracted text)")
        print("   - File_Upload_History (upload tracking)")
        print("   - File_Upload_Details (per-file details)")
        print("   - Extraction_History (extraction tracking)")
        print("   - Search_History (search analytics)")
        print("🔍 Existing Attendance table preserved")
        print("🚀 Search performance indexes added")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_tables_exist(db_path: Optional[str] = None) -> dict:
    """
    Check which tables exist in the database
    
    Returns:
        dict: Table existence status
    """
    if db_path is None:
        db_path = get_database_path()
    
    tables_to_check = [
        'Attendance',  # Existing table
        'Candidates',
        'Documents', 
        'Document_Content',
        'File_Upload_History',
        'File_Upload_Details',
        'Extraction_History',
        'Search_History'
    ]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        table_status = {}
        for table in tables_to_check:
            table_status[table] = table in existing_tables
            
        return table_status
        
    except sqlite3.Error as e:
        print(f"❌ Error checking tables: {e}")
        return {}

if __name__ == "__main__":
    # Run this script directly to create tables
    print("🚀 Creating database tables for Document Management System...")
    
    # Check existing tables first
    print("\n📋 Checking existing tables...")
    table_status = check_tables_exist()
    for table, exists in table_status.items():
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f"   {table}: {status}")
    
    # Create new tables
    print("\n🔨 Creating new tables...")
    success = create_all_tables()
    
    if success:
        print("\n🎉 Database setup complete!")
        print("💡 Test with your terminal method:")
        print('   sqlite3 "Credit-Agricole.db" ".schema"')
        print('   sqlite3 "Credit-Agricole.db" "SELECT name FROM sqlite_master WHERE type=\'table\';"')
    else:
        print("\n❌ Database setup failed!")