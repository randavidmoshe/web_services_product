# form_mapper_config_models.py
# Pydantic models for Form Mapper company configuration

from pydantic import BaseModel, Field
from typing import Optional


class FormMapperConfig(BaseModel):
    """
    Form Mapper configuration - per company.
    All users of a company inherit these settings.
    Managed by super admin.
    """
    test_cases_file: str = Field(
        default="test_cases1.json",
        description="JSON file containing test case definitions"
    )
    
    enable_ui_verification: bool = Field(
        default=True,
        description="Enable AI visual verification of UI elements"
    )
    
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for failed steps"
    )

    ai_parse_max_retries: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum retry attempts for AI JSON parsing failures"
    )
    
    use_detect_fields_change: bool = Field(
        default=True,
        description="Detect when form fields change between steps"
    )
    
    use_full_dom: bool = Field(
        default=True,
        description="Extract complete DOM (recommended)"
    )
    
    use_optimized_dom: bool = Field(
        default=False,
        description="Use optimized/compressed DOM extraction"
    )
    
    use_forms_dom: bool = Field(
        default=False,
        description="Extract only form-related DOM elements"
    )
    
    include_js_in_dom: bool = Field(
        default=True,
        description="Include JavaScript in DOM extraction"
    )
    
    enable_junction_discovery: bool = Field(
        default=True,
        description="Explore multiple paths at form junctions"
    )
    
    max_junction_paths: int = Field(
        default=7,
        ge=1,
        le=50,
        description="Maximum number of junction paths to explore"
    )

    max_options_for_junction: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Skip junction if it has more than this many options"
    )

    max_options_to_test: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Maximum number of options to test per junction"
    )

    use_ai_dont_regenerate: bool = Field(
        default=True,
        description="Use AI hint (dont_regenerate) to skip regeneration for non-field-changing actions"
    )

    use_ai_path_evaluation: bool = Field(
        default=True,
        description="Use AI to determine next junction path instead of algorithmic approach"
    )

    ai_discover_all_path_combinations: bool = Field(
        default=False,
        description="When True, test all combinations of junction options. When False, just ensure each option is tested once"
    )

    # Retention settings
    screenshots_retention_days: int = Field(
        default=90,
        ge=7,
        le=365,
        description="Days to keep screenshots in S3 before auto-delete"
    )

    logs_hot_retention_days: int = Field(
        default=14,
        ge=1,
        le=90,
        description="Days to keep logs in database before archiving to S3"
    )

    logs_cold_retention_days: int = Field(
        default=90,
        ge=14,
        le=365,
        description="Days to keep archived logs in S3 before auto-delete"
    )

    visual_verify_max_wait_seconds: int = Field(
        default=180,
        ge=30,
        le=600,
        description="Maximum seconds to wait for page to be ready during visual verification"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "test_cases_file": "test_cases1.json",
                "enable_ui_verification": True,
                "max_retries": 3,
                "use_detect_fields_change": True,
                "use_full_dom": True,
                "use_optimized_dom": False,
                "use_forms_dom": False,
                "include_js_in_dom": True,
                "enable_junction_discovery": True,
                "max_junction_paths": 7,
                "max_options_for_junction": 8,
                "max_options_to_test": 4,
                "use_ai_dont_regenerate": True,
                "use_ai_path_evaluation": True,
                "ai_discover_all_path_combinations": False,
                "screenshots_retention_days": 90,
                "logs_hot_retention_days": 14,
                "logs_cold_retention_days": 90
            }
        }


class FormMapperConfigUpdate(BaseModel):
    """Partial update model - all fields optional"""
    test_cases_file: Optional[str] = None
    enable_ui_verification: Optional[bool] = None
    max_retries: Optional[int] = Field(default=None, ge=1, le=10)
    ai_parse_max_retries: Optional[int] = Field(default=None, ge=1, le=5)
    use_detect_fields_change: Optional[bool] = None
    use_full_dom: Optional[bool] = None
    use_optimized_dom: Optional[bool] = None
    use_forms_dom: Optional[bool] = None
    include_js_in_dom: Optional[bool] = None
    enable_junction_discovery: Optional[bool] = None
    max_junction_paths: Optional[int] = Field(default=None, ge=1, le=50)
    max_options_for_junction: Optional[int] = Field(default=None, ge=1, le=50)
    max_options_to_test: Optional[int] = Field(default=None, ge=1, le=20)
    use_ai_dont_regenerate: Optional[bool] = None
    use_ai_path_evaluation: Optional[bool] = None
    ai_discover_all_path_combinations: Optional[bool] = None
    screenshots_retention_days: Optional[int] = Field(default=None, ge=7, le=365)
    logs_hot_retention_days: Optional[int] = Field(default=None, ge=1, le=90)
    logs_cold_retention_days: Optional[int] = Field(default=None, ge=14, le=365)
    visual_verify_max_wait_seconds: Optional[int] = Field(default=None, ge=30, le=600)


# Default config as dict
DEFAULT_FORM_MAPPER_CONFIG = {
    "test_cases_file": "test_cases1.json",
    "enable_ui_verification": True,
    "max_retries": 3,
    "ai_parse_max_retries": 2,
    "use_detect_fields_change": True,
    "use_full_dom": True,
    "use_optimized_dom": False,
    "use_forms_dom": False,
    "include_js_in_dom": True,
    "enable_junction_discovery": True,
    "max_junction_paths": 7,
    "max_options_for_junction": 8,
    "max_options_to_test": 4,
    "use_ai_dont_regenerate": True,
    "use_ai_path_evaluation": True,
    "ai_discover_all_path_combinations": False,
    "screenshots_retention_days": 90,
    "logs_hot_retention_days": 14,
    "logs_cold_retention_days": 90,
    "visual_verify_max_wait_seconds": 180,
}




def get_company_config(db_session, company_id: int) -> FormMapperConfig:
    """
    Get Form Mapper config for a company.
    Returns defaults if not set.
    """
    from models.database import Company
    
    company = db_session.query(Company).filter(Company.id == company_id).first()
    
    if not company or not company.form_mapper_config:
        return FormMapperConfig()
    
    # Merge with defaults (in case new fields were added)
    config_dict = {**DEFAULT_FORM_MAPPER_CONFIG}
    if isinstance(company.form_mapper_config, dict):
        config_dict.update(company.form_mapper_config)
    
    return FormMapperConfig(**config_dict)


def update_company_config(db_session, company_id: int, updates: FormMapperConfigUpdate) -> FormMapperConfig:
    """
    Update Form Mapper config for a company.
    Only updates provided fields.
    """
    from models.database import Company
    
    company = db_session.query(Company).filter(Company.id == company_id).first()
    
    if not company:
        raise ValueError(f"Company {company_id} not found")
    
    # Get current config or defaults
    current_config = company.form_mapper_config if company.form_mapper_config else DEFAULT_FORM_MAPPER_CONFIG.copy()
    
    # Apply updates (only non-None values)
    update_dict = updates.dict(exclude_none=True)
    current_config.update(update_dict)
    
    # Save
    company.form_mapper_config = current_config
    db_session.commit()
    
    return FormMapperConfig(**current_config)
