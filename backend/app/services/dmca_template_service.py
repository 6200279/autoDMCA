from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime
import re
import json

from app.db.models.dmca_template import DMCATemplate, TemplateType
from app.db.models.template_category import TemplateCategory
from app.schemas.dmca_template import (
    DMCATemplateCreate,
    DMCATemplateUpdate, 
    TemplateCategoryCreate,
    TemplateCategoryUpdate,
    TemplateVariables,
    TemplatePreviewResponse
)


class DMCATemplateService:
    """Service for managing DMCA templates and categories."""

    @staticmethod
    def get_template(db: Session, template_id: int) -> Optional[DMCATemplate]:
        """Get template by ID."""
        return db.query(DMCATemplate).filter(DMCATemplate.id == template_id).first()

    @staticmethod
    def get_templates(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        category_id: Optional[int] = None,
        template_type: Optional[TemplateType] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[DMCATemplate]:
        """Get templates with filtering."""
        query = db.query(DMCATemplate)
        
        if category_id is not None:
            query = query.filter(DMCATemplate.category_id == category_id)
        
        if template_type is not None:
            query = query.filter(DMCATemplate.template_type == template_type)
        
        if is_active is not None:
            query = query.filter(DMCATemplate.is_active == is_active)
        
        if search:
            search_filter = or_(
                DMCATemplate.name.ilike(f"%{search}%"),
                DMCATemplate.description.ilike(f"%{search}%"),
                DMCATemplate.body_template.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        return query.order_by(DMCATemplate.usage_count.desc(), DMCATemplate.created_at.desc())\
                   .offset(skip).limit(limit).all()

    @staticmethod
    def count_templates(
        db: Session,
        category_id: Optional[int] = None,
        template_type: Optional[TemplateType] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> int:
        """Count templates with filtering."""
        query = db.query(func.count(DMCATemplate.id))
        
        if category_id is not None:
            query = query.filter(DMCATemplate.category_id == category_id)
        
        if template_type is not None:
            query = query.filter(DMCATemplate.template_type == template_type)
        
        if is_active is not None:
            query = query.filter(DMCATemplate.is_active == is_active)
        
        if search:
            search_filter = or_(
                DMCATemplate.name.ilike(f"%{search}%"),
                DMCATemplate.description.ilike(f"%{search}%"),
                DMCATemplate.body_template.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        return query.scalar()

    @staticmethod
    def create_template(db: Session, template: DMCATemplateCreate) -> DMCATemplate:
        """Create new template."""
        # Extract and validate variables from template content
        available_vars = DMCATemplateService._extract_template_variables(
            template.subject_template + " " + template.body_template
        )
        
        db_template = DMCATemplate(
            **template.dict(),
            available_variables=json.dumps(available_vars) if available_vars else None,
            usage_count=0
        )
        
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        
        return db_template

    @staticmethod
    def update_template(
        db: Session, 
        template_id: int, 
        template_update: DMCATemplateUpdate
    ) -> Optional[DMCATemplate]:
        """Update existing template."""
        db_template = DMCATemplateService.get_template(db, template_id)
        if not db_template:
            return None
        
        update_data = template_update.dict(exclude_unset=True)
        
        # If template content is being updated, re-extract variables
        if 'subject_template' in update_data or 'body_template' in update_data:
            subject = update_data.get('subject_template', db_template.subject_template)
            body = update_data.get('body_template', db_template.body_template)
            available_vars = DMCATemplateService._extract_template_variables(f"{subject} {body}")
            update_data['available_variables'] = json.dumps(available_vars) if available_vars else None
        
        for field, value in update_data.items():
            setattr(db_template, field, value)
        
        db.commit()
        db.refresh(db_template)
        
        return db_template

    @staticmethod
    def delete_template(db: Session, template_id: int) -> bool:
        """Delete template (soft delete by deactivating)."""
        db_template = DMCATemplateService.get_template(db, template_id)
        if not db_template:
            return False
        
        db_template.is_active = False
        db.commit()
        
        return True

    @staticmethod
    def get_default_templates(db: Session, template_type: Optional[TemplateType] = None) -> List[DMCATemplate]:
        """Get default templates."""
        query = db.query(DMCATemplate).filter(
            and_(DMCATemplate.is_default == True, DMCATemplate.is_active == True)
        )
        
        if template_type:
            query = query.filter(DMCATemplate.template_type == template_type)
        
        return query.all()

    @staticmethod
    def increment_usage(db: Session, template_id: int) -> bool:
        """Increment template usage count."""
        db_template = DMCATemplateService.get_template(db, template_id)
        if not db_template:
            return False
        
        db_template.usage_count += 1
        db.commit()
        
        return True

    @staticmethod
    def preview_template(
        db: Session,
        template_id: int,
        variables: Optional[TemplateVariables] = None
    ) -> Optional[TemplatePreviewResponse]:
        """Preview template with variables substitution."""
        template = DMCATemplateService.get_template(db, template_id)
        if not template:
            return None
        
        if variables is None:
            variables = TemplateVariables()
        
        var_dict = variables.dict()
        
        # Render subject and body
        subject = DMCATemplateService._render_template(template.subject_template, var_dict)
        body = DMCATemplateService._render_template(template.body_template, var_dict)
        
        # Find missing variables
        missing_vars = DMCATemplateService._find_missing_variables(
            template.subject_template + " " + template.body_template,
            var_dict
        )
        
        return TemplatePreviewResponse(
            subject=subject,
            body=body,
            missing_variables=missing_vars
        )

    @staticmethod
    def _extract_template_variables(template_content: str) -> List[str]:
        """Extract variable placeholders from template content."""
        # Find variables in format {{variable_name}} or {variable_name}
        pattern = r'\{(\w+)\}'
        matches = re.findall(pattern, template_content)
        return list(set(matches))

    @staticmethod
    def _render_template(template: str, variables: Dict[str, Any]) -> str:
        """Render template with variable substitution."""
        rendered = template
        for key, value in variables.items():
            if value is not None:
                # Replace both {{key}} and {key} formats
                rendered = rendered.replace(f"{{{key}}}", str(value))
                rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
        return rendered

    @staticmethod
    def _find_missing_variables(template_content: str, variables: Dict[str, Any]) -> List[str]:
        """Find variables that are in template but not provided in variables dict."""
        template_vars = DMCATemplateService._extract_template_variables(template_content)
        provided_vars = set(k for k, v in variables.items() if v is not None)
        return list(set(template_vars) - provided_vars)


class TemplateCategoryService:
    """Service for managing template categories."""

    @staticmethod
    def get_category(db: Session, category_id: int) -> Optional[TemplateCategory]:
        """Get category by ID."""
        return db.query(TemplateCategory).filter(TemplateCategory.id == category_id).first()

    @staticmethod
    def get_categories(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[TemplateCategory]:
        """Get categories."""
        query = db.query(TemplateCategory)
        
        if is_active is not None:
            query = query.filter(TemplateCategory.is_active == is_active)
        
        return query.order_by(TemplateCategory.display_order, TemplateCategory.name)\
                   .offset(skip).limit(limit).all()

    @staticmethod
    def create_category(db: Session, category: TemplateCategoryCreate) -> TemplateCategory:
        """Create new category."""
        db_category = TemplateCategory(**category.dict())
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category

    @staticmethod
    def update_category(
        db: Session,
        category_id: int,
        category_update: TemplateCategoryUpdate
    ) -> Optional[TemplateCategory]:
        """Update existing category."""
        db_category = TemplateCategoryService.get_category(db, category_id)
        if not db_category:
            return None
        
        update_data = category_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_category, field, value)
        
        db.commit()
        db.refresh(db_category)
        
        return db_category

    @staticmethod
    def delete_category(db: Session, category_id: int) -> bool:
        """Delete category (soft delete)."""
        db_category = TemplateCategoryService.get_category(db, category_id)
        if not db_category:
            return False
        
        # Check if category has templates
        template_count = db.query(func.count(DMCATemplate.id))\
            .filter(DMCATemplate.category_id == category_id).scalar()
        
        if template_count > 0:
            # Don't delete categories with templates, just deactivate
            db_category.is_active = False
        else:
            db.delete(db_category)
        
        db.commit()
        return True

    @staticmethod
    def get_category_with_template_count(db: Session, category_id: int) -> Optional[Dict[str, Any]]:
        """Get category with template count."""
        category = TemplateCategoryService.get_category(db, category_id)
        if not category:
            return None
        
        template_count = db.query(func.count(DMCATemplate.id))\
            .filter(DMCATemplate.category_id == category_id).scalar()
        
        return {
            "category": category,
            "template_count": template_count
        }