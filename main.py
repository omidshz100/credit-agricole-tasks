from fastapi import FastAPI, HTTPException
import sqlite3
from typing import Optional
from pydantic import BaseModel

# Create FastAPI app instance
app = FastAPI(title="Credit Agricole Employee API", description="API to retrieve employee data by ID or SSN")

# Database path
DB_PATH = "Credit-Agricole.db"

# Pydantic model for Employee response
class Employee(BaseModel):
    id: int
    name: str
    lastname: str
    ssn: Optional[str] = None
    nationality: Optional[str] = None

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # This allows us to access columns by name
        return conn
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Credit Agricole Employee API",
        "endpoints": {
            "/employee/id/{employee_id}": "Get employee by ID",
            "/employee/ssn/{ssn}": "Get employee by SSN",
            "/docs": "API documentation"
        }
    }

@app.get("/employee/id/{employee_id}", response_model=Employee)
async def get_employee_by_id(employee_id: int):
    """
    Retrieve employee information by employee ID
    
    Args:
        employee_id (int): The unique employee ID
        
    Returns:
        Employee: Employee information including id, name, lastname, ssn, and nationality
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, lastname, ssn, nationality FROM Employees WHERE id = ?",
            (employee_id,)
        )
        row = cursor.fetchone()
        
        if row is None:
            raise HTTPException(status_code=404, detail=f"Employee with ID {employee_id} not found")
        
        # Convert row to dictionary
        employee_data = dict(row)
        return Employee(**employee_data)
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.get("/employee/ssn/{ssn}", response_model=Employee)
async def get_employee_by_ssn(ssn: str):
    """
    Retrieve employee information by Social Security Number (SSN)
    
    Args:
        ssn (str): The employee's Social Security Number
        
    Returns:
        Employee: Employee information including id, name, lastname, ssn, and nationality
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, lastname, ssn, nationality FROM Employees WHERE ssn = ?",
            (ssn,)
        )
        row = cursor.fetchone()
        
        if row is None:
            raise HTTPException(status_code=404, detail=f"Employee with SSN {ssn} not found")
        
        # Convert row to dictionary
        employee_data = dict(row)
        return Employee(**employee_data)
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

# Optional: Endpoint to get all employees (for testing purposes)
@app.get("/employees")
async def get_all_employees():
    """
    Retrieve all employees (for testing purposes)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, lastname, ssn, nationality FROM Employees")
        rows = cursor.fetchall()
        
        employees = [dict(row) for row in rows]
        return {"employees": employees, "count": len(employees)}
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)