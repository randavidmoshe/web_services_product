# models/test_page_models.py
# Minimal TestPageRoute model for dynamic content testing

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
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

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    mapper_sessions = relationship("FormMapperSession", back_populates="test_page_route")
    map_results = relationship("FormMapResult", back_populates="test_page_route")