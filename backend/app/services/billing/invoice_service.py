"""
Invoice Management Service for AutoDMCA

Provides comprehensive invoice management functionality:
- Invoice retrieval and generation
- PDF invoice generation
- Invoice preview for plan changes
- Email delivery integration
- Invoice analytics and reporting
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import stripe
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from app.core.config import settings
from app.db.models.billing import Invoice, InvoiceItem, Subscription
from app.db.models.user import User
from app.services.billing.stripe_service import StripeService
from app.services.notifications.alert_system import alert_system

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class InvoiceService:
    """
    Comprehensive invoice management service
    
    Features:
    - Invoice CRUD operations
    - PDF generation with company branding
    - Preview invoices for plan changes
    - Email delivery integration
    - Invoice analytics and reporting
    """
    
    def __init__(self):
        self.stripe_service = StripeService()
        
    async def get_invoice_by_id(self, db: AsyncSession, invoice_id: int) -> Optional[Invoice]:
        """Get invoice by ID"""
        try:
            result = await db.execute(
                select(Invoice).where(Invoice.id == invoice_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to get invoice {invoice_id}: {e}")
            return None
    
    async def get_invoices_for_user(
        self, 
        db: AsyncSession, 
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> List[Invoice]:
        """Get invoices for a user"""
        try:
            result = await db.execute(
                select(Invoice)
                .where(Invoice.user_id == user_id)
                .order_by(desc(Invoice.created_at))
                .limit(limit)
                .offset(offset)
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get invoices for user {user_id}: {e}")
            return []
    
    async def create_invoice_from_stripe(
        self,
        db: AsyncSession,
        stripe_invoice_id: str,
        user_id: int
    ) -> Optional[Invoice]:
        """Create invoice record from Stripe invoice"""
        try:
            # Retrieve Stripe invoice
            stripe_invoice = stripe.Invoice.retrieve(stripe_invoice_id)
            
            # Create invoice record
            invoice = Invoice(
                user_id=user_id,
                stripe_invoice_id=stripe_invoice_id,
                invoice_number=stripe_invoice.number or f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{user_id}",
                amount_due=Decimal(str(stripe_invoice.amount_due / 100)),  # Convert from cents
                amount_paid=Decimal(str(stripe_invoice.amount_paid / 100)),
                currency=stripe_invoice.currency.upper(),
                status=stripe_invoice.status,
                due_date=datetime.fromtimestamp(stripe_invoice.due_date) if stripe_invoice.due_date else None,
                invoice_pdf_url=stripe_invoice.invoice_pdf,
                hosted_invoice_url=stripe_invoice.hosted_invoice_url
            )
            
            # Add invoice items
            for line_item in stripe_invoice.lines.data:
                invoice_item = InvoiceItem(
                    description=line_item.description or "Subscription",
                    quantity=line_item.quantity or 1,
                    unit_amount=Decimal(str(line_item.amount / 100)),
                    total_amount=Decimal(str(line_item.amount / 100))
                )
                invoice.items.append(invoice_item)
            
            db.add(invoice)
            await db.commit()
            await db.refresh(invoice)
            
            logger.info(f"Created invoice record: {invoice.id} from Stripe: {stripe_invoice_id}")
            return invoice
            
        except Exception as e:
            logger.error(f"Failed to create invoice from Stripe {stripe_invoice_id}: {e}")
            await db.rollback()
            return None
    
    async def generate_preview_invoice(
        self, 
        db: AsyncSession, 
        user_id: int,
        subscription_id: Optional[int] = None,
        new_plan_price_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate preview invoice for plan changes or upcoming billing"""
        try:
            # Get user's subscription
            if subscription_id:
                result = await db.execute(
                    select(Subscription).where(Subscription.id == subscription_id)
                )
                subscription = result.scalar_one_or_none()
            else:
                result = await db.execute(
                    select(Subscription)
                    .where(Subscription.user_id == user_id)
                    .where(Subscription.status.in_(['active', 'trialing']))
                )
                subscription = result.scalar_one_or_none()
            
            if not subscription:
                return {"error": "No active subscription found"}
            
            # Generate preview invoice via Stripe
            preview_params = {
                'customer': subscription.stripe_customer_id,
                'subscription': subscription.stripe_subscription_id
            }
            
            # If changing plan, include new price
            if new_plan_price_id:
                preview_params['subscription_items'] = [{
                    'id': subscription.stripe_subscription_id,
                    'price': new_plan_price_id
                }]
            
            upcoming_invoice = stripe.Invoice.upcoming(**preview_params)
            
            # Format preview data
            preview = {
                "subtotal": upcoming_invoice.subtotal / 100,
                "tax": upcoming_invoice.tax / 100 if upcoming_invoice.tax else 0,
                "total": upcoming_invoice.total / 100,
                "currency": upcoming_invoice.currency.upper(),
                "period_start": datetime.fromtimestamp(upcoming_invoice.period_start).isoformat(),
                "period_end": datetime.fromtimestamp(upcoming_invoice.period_end).isoformat(),
                "items": []
            }
            
            # Add line items
            for line_item in upcoming_invoice.lines.data:
                preview["items"].append({
                    "description": line_item.description,
                    "quantity": line_item.quantity,
                    "unit_amount": line_item.amount / 100,
                    "period": {
                        "start": datetime.fromtimestamp(line_item.period.start).isoformat(),
                        "end": datetime.fromtimestamp(line_item.period.end).isoformat()
                    }
                })
            
            return preview
            
        except Exception as e:
            logger.error(f"Failed to generate preview invoice: {e}")
            return {"error": str(e)}
    
    async def download_invoice_pdf(self, db: AsyncSession, invoice_id: int, user_id: int) -> Optional[bytes]:
        """Generate or retrieve invoice PDF"""
        try:
            # Get invoice
            invoice = await self.get_invoice_by_id(db, invoice_id)
            
            if not invoice or invoice.user_id != user_id:
                return None
            
            # If Stripe PDF is available, fetch it
            if invoice.invoice_pdf_url:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(invoice.invoice_pdf_url) as response:
                        if response.status == 200:
                            return await response.read()
            
            # Generate custom PDF
            pdf_buffer = io.BytesIO()
            return self._generate_custom_pdf(invoice, pdf_buffer)
            
        except Exception as e:
            logger.error(f"Failed to download invoice PDF {invoice_id}: {e}")
            return None
    
    def _generate_custom_pdf(self, invoice: Invoice, buffer: io.BytesIO) -> bytes:
        """Generate custom branded PDF invoice"""
        try:
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Company header
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.HexColor('#2563eb')
            )
            
            story.append(Paragraph("AutoDMCA", title_style))
            story.append(Paragraph("Content Protection Services", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Invoice details
            invoice_style = ParagraphStyle(
                'InvoiceHeader',
                parent=styles['Heading2'],
                fontSize=18,
                spaceAfter=20
            )
            
            story.append(Paragraph(f"Invoice #{invoice.invoice_number}", invoice_style))
            story.append(Paragraph(f"Date: {invoice.created_at.strftime('%B %d, %Y')}", styles['Normal']))
            
            if invoice.due_date:
                story.append(Paragraph(f"Due Date: {invoice.due_date.strftime('%B %d, %Y')}", styles['Normal']))
            
            story.append(Spacer(1, 20))
            
            # Invoice items table
            table_data = [['Description', 'Quantity', 'Unit Price', 'Total']]
            
            for item in invoice.items:
                table_data.append([
                    item.description,
                    str(item.quantity),
                    f"${item.unit_amount:.2f}",
                    f"${item.total_amount:.2f}"
                ])
            
            # Add totals
            table_data.append(['', '', 'Subtotal:', f"${invoice.amount_due:.2f}"])
            
            if invoice.currency != 'USD':
                table_data.append(['', '', 'Currency:', invoice.currency])
            
            table = Table(table_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -3), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -2), (-1, -1), colors.lightgrey),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 30))
            
            # Payment status
            status_color = colors.green if invoice.status == 'paid' else colors.red
            status_style = ParagraphStyle(
                'StatusStyle',
                parent=styles['Normal'],
                textColor=status_color,
                fontSize=14,
                fontName='Helvetica-Bold'
            )
            
            story.append(Paragraph(f"Status: {invoice.status.upper()}", status_style))
            
            # Footer
            story.append(Spacer(1, 50))
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.grey
            )
            
            story.append(Paragraph("Thank you for your business!", footer_style))
            story.append(Paragraph("AutoDMCA - Protecting Your Content", footer_style))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            return buffer.read()
            
        except Exception as e:
            logger.error(f"Failed to generate custom PDF: {e}")
            return None
    
    async def send_invoice_email(
        self, 
        db: AsyncSession, 
        invoice_id: int,
        user_email: Optional[str] = None
    ) -> bool:
        """Send invoice via email"""
        try:
            # Get invoice
            invoice = await self.get_invoice_by_id(db, invoice_id)
            if not invoice:
                return False
            
            # Get user email if not provided
            if not user_email:
                result = await db.execute(
                    select(User).where(User.id == invoice.user_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    return False
                user_email = user.email
            
            # Generate PDF
            pdf_data = await self.download_invoice_pdf(db, invoice_id, invoice.user_id)
            if not pdf_data:
                return False
            
            # Send via alert system (which has email capabilities)
            await alert_system.send_alert(
                user_id=invoice.user_id,
                alert_type='invoice_ready',
                title=f"Invoice {invoice.invoice_number} Available",
                message=f"Your invoice for ${invoice.amount_due:.2f} is ready for download.",
                data={
                    "invoice_id": invoice_id,
                    "invoice_number": invoice.invoice_number,
                    "amount": str(invoice.amount_due),
                    "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                    "download_url": f"/api/v1/billing/invoices/{invoice_id}/pdf"
                },
                channels=['email']
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send invoice email {invoice_id}: {e}")
            return False
    
    async def get_invoice_analytics(
        self, 
        db: AsyncSession, 
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get invoice analytics and reporting"""
        try:
            # Build base query
            query = select(Invoice)
            
            if user_id:
                query = query.where(Invoice.user_id == user_id)
            
            if start_date:
                query = query.where(Invoice.created_at >= start_date)
            
            if end_date:
                query = query.where(Invoice.created_at <= end_date)
            
            result = await db.execute(query)
            invoices = result.scalars().all()
            
            # Calculate analytics
            total_invoices = len(invoices)
            total_amount = sum(invoice.amount_due for invoice in invoices)
            paid_invoices = [inv for inv in invoices if inv.status == 'paid']
            unpaid_invoices = [inv for inv in invoices if inv.status in ['open', 'draft']]
            
            analytics = {
                "total_invoices": total_invoices,
                "total_amount": float(total_amount),
                "paid_invoices": len(paid_invoices),
                "unpaid_invoices": len(unpaid_invoices),
                "payment_rate": (len(paid_invoices) / total_invoices * 100) if total_invoices > 0 else 0,
                "average_invoice_amount": float(total_amount / total_invoices) if total_invoices > 0 else 0,
                "revenue": sum(float(inv.amount_paid) for inv in paid_invoices),
                "outstanding": sum(float(inv.amount_due - inv.amount_paid) for inv in unpaid_invoices)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get invoice analytics: {e}")
            return {}


# Global invoice service instance
invoice_service = InvoiceService()


__all__ = [
    'InvoiceService',
    'invoice_service'
]