from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.database import get_db, Project

router = APIRouter()

@router.get("/")
async def list_projects(company_id: int, db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.company_id == company_id).all()
    return projects

@router.post("/")
async def create_project(name: str, company_id: int, product_id: int, user_id: int, db: Session = Depends(get_db)):
    project = Project(
        name=name,
        company_id=company_id,
        product_id=product_id,
        created_by_user_id=user_id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
