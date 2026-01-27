# models/test_page_models.py
# Minimal TestPageRoute model for dynamic content testing

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class TestPageRoute(Base):
    """
    User-defined test page for dynamic content testing.
    """
    __tablename__ = "test_page_routes"

    id = Column(Integer, primary_key=True, index=True)

    # Ownership
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=False)
    network_id = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"), nullable=False)

    # Test Definition
    url = Column(String(500), nullable=False)
    test_name = Column(String(200), nullable=False)
    test_case_description = Column(Text, nullable=False)

    # Status
    status = Column(String(50), default="not_mapped")
    verification_file = Column(JSON, nullable=True)
    verification_file_content = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    mapper_sessions = relationship("FormMapperSession", back_populates="test_page_route")
    map_results = relationship("FormMapResult", back_populates="test_page_route")
    reference_images = relationship("TestPageReferenceImage", back_populates="test_page_route",
                                    cascade="all, delete-orphan")

class TestPageReferenceImage(Base):
    """Reference images for visual verification of test pages"""
    __tablename__ = "test_page_reference_images"

    id = Column(Integer, primary_key=True, index=True)
    test_page_route_id = Column(Integer, ForeignKey("test_page_routes.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, nullable=False)
    status = Column(String(20), default="pending")
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    s3_key = Column(String(500), nullable=False)
    s3_bucket = Column(String(100), nullable=False)
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    content_type = Column(String(50), nullable=True)
    width_px = Column(Integer, nullable=True)
    height_px = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    test_page_route = relationship("TestPageRoute", back_populates="reference_images")