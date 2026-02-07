from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.database import get_db, Project, Network, FormPageRoute, User, Company
from utils.auth_helpers import get_current_user_from_request
from services.encryption_service import encrypt_credential, mask_credential, invalidate_credential_cache

router = APIRouter()


# =============================================================================
# Pydantic Models (Request/Response schemas)
# =============================================================================

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    product_id: int
    project_type: Optional[str] = 'enterprise'


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class NetworkCreate(BaseModel):
    name: str
    url: str
    network_type: str  # "qa", "staging", or "production"
    login_username: Optional[str] = None
    login_password: Optional[str] = None


class NetworkUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    network_type: Optional[str] = None
    login_username: Optional[str] = None
    login_password: Optional[str] = None


# =============================================================================
# Project Endpoints
# =============================================================================

@router.get("/")
async def list_projects(request: Request, db: Session = Depends(get_db)):
    """List all projects for a company"""
    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]
    projects = db.query(Project).filter(Project.company_id == company_id).all()
    
    # Add network count and form page count for each project
    result = []
    for project in projects:
        network_count = db.query(Network).filter(Network.project_id == project.id).count()
        form_page_count = db.query(FormPageRoute).filter(FormPageRoute.project_id == project.id).count()
        
        result.append({
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "company_id": project.company_id,
            "product_id": project.product_id,
            "created_by_user_id": project.created_by_user_id,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "network_count": network_count,
            "form_page_count": form_page_count,
            "project_type": project.project_type
        })
    
    return result


@router.post("/")
async def create_project(project_data: ProjectCreate, request: Request, db: Session = Depends(get_db)):
    """Create a new project"""
    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    # Validate project_type matches company's account_category
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Mapping: form_centric -> enterprise, dynamic -> dynamic_content
    if company.account_category == 'form_centric' and project_data.project_type != 'enterprise':
        raise HTTPException(
            status_code=400,
            detail="Form-centric accounts can only create enterprise (form-based) projects"
        )
    if company.account_category == 'dynamic' and project_data.project_type != 'dynamic_content':
        raise HTTPException(
            status_code=400,
            detail="Dynamic accounts can only create dynamic_content projects"
        )

    project = Project(
        name=project_data.name,
        description=project_data.description,
        company_id=company_id,
        product_id=project_data.product_id,
        created_by_user_id=current_user["user_id"],
        project_type=project_data.project_type
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}")
async def get_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Get a single project with its networks and form pages"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != project.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get networks grouped by type
    networks = db.query(Network).filter(Network.project_id == project_id).all()
    
    networks_by_type = {
        "qa": [],
        "staging": [],
        "production": []
    }
    
    for network in networks:
        network_data = {
            "id": network.id,
            "name": network.name,
            "url": network.url,
            "network_type": network.network_type,
            "login_username": mask_credential(network.login_username, "username") if network.login_username else None,
            "login_password": mask_credential(network.login_password, "password") if network.login_password else None,
            "created_by_user_id": network.created_by_user_id,
            "created_at": network.created_at,
            "updated_at": network.updated_at
        }
        if network.network_type in networks_by_type:
            networks_by_type[network.network_type].append(network_data)
    
    # Get form pages
    form_pages = db.query(FormPageRoute).filter(FormPageRoute.project_id == project_id).all()
    
    form_pages_data = [
        {
            "id": fp.id,
            "form_name": fp.form_name,
            "url": fp.url,
            "network_id": fp.network_id,
            "navigation_steps": fp.navigation_steps,
            "is_root": fp.is_root,
            "created_at": fp.created_at
        }
        for fp in form_pages
    ]
    
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "company_id": project.company_id,
        "product_id": project.product_id,
        "created_by_user_id": project.created_by_user_id,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "networks": networks_by_type,
        "form_pages": form_pages_data
    }


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update a project's name or description"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != project.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    
    return project


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Delete a project.
    - Admin can delete any project
    - Regular user can only delete projects they created
    - Returns warning about cascading deletes (networks, form pages)
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != project.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check permissions
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Admin can delete any project, regular user only their own
    if user.role != "admin" and project.created_by_user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=403,
            detail="You can only delete projects you created"
        )
    
    # Count what will be deleted
    network_count = db.query(Network).filter(Network.project_id == project_id).count()
    form_page_count = db.query(FormPageRoute).filter(FormPageRoute.project_id == project_id).count()
    
    # Delete form pages first (they reference networks)
    db.query(FormPageRoute).filter(FormPageRoute.project_id == project_id).delete()
    
    # Delete networks
    db.query(Network).filter(Network.project_id == project_id).delete()
    
    # Delete project
    db.delete(project)
    db.commit()
    
    return {
        "message": "Project deleted successfully",
        "deleted": {
            "project_id": project_id,
            "networks_deleted": network_count,
            "form_pages_deleted": form_page_count
        }
    }


# =============================================================================
# Network Endpoints
# =============================================================================

@router.post("/{project_id}/networks")
async def create_network(
    project_id: int,
    network_data: NetworkCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Add a network to a project.
    - URL must be unique within the project
    - network_type must be "qa", "staging", or "production"
    """
    # Check project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != project.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate network_type
    if network_data.network_type not in ["qa", "staging", "production"]:
        raise HTTPException(
            status_code=400,
            detail="network_type must be 'qa', 'staging', or 'production'"
        )
    
    # Check URL uniqueness within project
    existing_network = db.query(Network).filter(
        Network.project_id == project_id,
        Network.url == network_data.url
    ).first()
    
    if existing_network:
        raise HTTPException(
            status_code=400,
            detail=f"A network with this URL already exists in this project (in {existing_network.network_type} section)"
        )
    
    # Create network
    network = Network(
        project_id=project_id,
        company_id=project.company_id,
        product_id=project.product_id,
        name=network_data.name,
        url=network_data.url,
        network_type=network_data.network_type,
        login_username=encrypt_credential(network_data.login_username, project.company_id) if network_data.login_username else None,
        login_password=encrypt_credential(network_data.login_password, project.company_id) if network_data.login_password else None,
        created_by_user_id=current_user["user_id"]
    )
    
    db.add(network)
    db.commit()
    db.refresh(network)
    
    return network


@router.put("/{project_id}/networks/{network_id}")
async def update_network(
    project_id: int,
    network_id: int,
    network_data: NetworkUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update a network's details"""
    network = db.query(Network).filter(
        Network.id == network_id,
        Network.project_id == project_id
    ).first()
    if not network:
        raise HTTPException(status_code=404, detail="Network not found in this project")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != network.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # If URL is being changed, check uniqueness
    if network_data.url is not None and network_data.url != network.url:
        existing_network = db.query(Network).filter(
            Network.project_id == project_id,
            Network.url == network_data.url,
            Network.id != network_id
        ).first()
        
        if existing_network:
            raise HTTPException(
                status_code=400,
                detail=f"A network with this URL already exists in this project (in {existing_network.network_type} section)"
            )
        network.url = network_data.url
    
    # Validate network_type if provided
    if network_data.network_type is not None:
        if network_data.network_type not in ["qa", "staging", "production"]:
            raise HTTPException(
                status_code=400,
                detail="network_type must be 'qa', 'staging', or 'production'"
            )
        network.network_type = network_data.network_type
    
    # Update other fields
    if network_data.name is not None:
        network.name = network_data.name
    if network_data.login_username is not None:
        network.login_username = encrypt_credential(network_data.login_username,
                                                    network.company_id) if network_data.login_username else None
    if network_data.login_password is not None:
        network.login_password = encrypt_credential(network_data.login_password,
                                                    network.company_id) if network_data.login_password else None
    # Invalidate credential cache if credentials changed
    if network_data.login_username is not None or network_data.login_password is not None:
        invalidate_credential_cache(network.company_id, network.id)
    
    network.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(network)
    
    return network


@router.delete("/{project_id}/networks/{network_id}")
async def delete_network(
    project_id: int,
    network_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a network from a project"""
    network = db.query(Network).filter(
        Network.id == network_id,
        Network.project_id == project_id
    ).first()
    if not network:
        raise HTTPException(status_code=404, detail="Network not found in this project")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != network.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Count form pages that will be affected
    form_page_count = db.query(FormPageRoute).filter(
        FormPageRoute.network_id == network_id
    ).count()
    
    # Delete associated form pages first
    db.query(FormPageRoute).filter(FormPageRoute.network_id == network_id).delete()
    
    # Delete network
    db.delete(network)
    db.commit()
    
    return {
        "message": "Network deleted successfully",
        "deleted": {
            "network_id": network_id,
            "form_pages_deleted": form_page_count
        }
    }


@router.get("/{project_id}/networks")
async def list_networks(project_id: int, request: Request, db: Session = Depends(get_db)):
    """List all networks for a project, grouped by type"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != project.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    networks = db.query(Network).filter(Network.project_id == project_id).all()
    
    networks_by_type = {
        "qa": [],
        "staging": [],
        "production": []
    }
    
    for network in networks:
        network_data = {
            "id": network.id,
            "name": network.name,
            "url": network.url,
            "network_type": network.network_type,
            "login_username": mask_credential(network.login_username, "username") if network.login_username else None,
            "login_password": mask_credential(network.login_password, "password") if network.login_password else None,
            "created_by_user_id": network.created_by_user_id,
            "created_at": network.created_at,
            "updated_at": network.updated_at
        }
        if network.network_type in networks_by_type:
            networks_by_type[network.network_type].append(network_data)
    
    return networks_by_type


# =============================================================================
# Form Pages Endpoint
# =============================================================================

@router.get("/{project_id}/form-pages")
async def list_form_pages(project_id: int, request: Request, db: Session = Depends(get_db)):
    """List all form pages for a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != project.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    form_pages = db.query(FormPageRoute).filter(
        FormPageRoute.project_id == project_id
    ).all()
    
    return [
        {
            "id": fp.id,
            "form_name": fp.form_name,
            "url": fp.url,
            "network_id": fp.network_id,
            "navigation_steps": fp.navigation_steps,
            "id_fields": fp.id_fields,
            "is_root": fp.is_root,
            "parent_form_route_id": fp.parent_form_route_id,
            "verification_attempts": fp.verification_attempts,
            "last_verified_at": fp.last_verified_at,
            "created_at": fp.created_at,
            "updated_at": fp.updated_at
        }
        for fp in form_pages
    ]
