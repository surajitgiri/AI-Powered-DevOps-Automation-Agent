from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db

router = APIRouter()

@router.get("/database")
def check_database(db: Session = Depends(get_db)):
    try:

        result = db.execute(text("SELECT 1")).scalar()

        return {
            "status": "success",
            "database": "connected",
            "result": result
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=5000,
            detail=f"Database connection failed: {str(e)}"
        )