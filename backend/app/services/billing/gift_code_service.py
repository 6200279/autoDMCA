import secrets
import string
import hashlib
import hmac
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.db.models.gift_subscription import GiftCode, GiftSubscription, GiftStatus

logger = logging.getLogger(__name__)


class GiftCodeService:
    """Service for generating and validating secure gift codes."""
    
    def __init__(self):
        # Use a mix of characters that are easily readable and avoid confusion
        # Excludes: 0, O, I, 1, l to avoid confusion
        self.code_alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        self.code_length = 16
        self.max_attempts_per_hour = 10
        self.code_expiry_days = 90
    
    def generate_gift_code(self) -> str:
        """Generate a secure, unique gift code."""
        # Generate the base code
        code = ''.join(secrets.choice(self.code_alphabet) for _ in range(self.code_length))
        
        # Format with dashes for readability: XXXX-XXXX-XXXX-XXXX
        formatted_code = '-'.join([code[i:i+4] for i in range(0, len(code), 4)])
        
        return formatted_code
    
    def generate_unique_code(self, max_attempts: int = 10) -> str:
        """Generate a unique gift code that doesn't exist in the database."""
        from app.db.session import SessionLocal
        
        for attempt in range(max_attempts):
            code = self.generate_gift_code()
            
            # Check if code already exists
            with SessionLocal() as db:
                existing_code = db.query(GiftCode).filter(GiftCode.code == code).first()
                if not existing_code:
                    return code
        
        raise ValueError("Failed to generate unique gift code after maximum attempts")
    
    def validate_code_format(self, code: str) -> bool:
        """Validate the format of a gift code."""
        if not code:
            return False
        
        # Remove any whitespace and convert to uppercase
        clean_code = code.strip().upper()
        
        # Check if it matches the expected format: XXXX-XXXX-XXXX-XXXX
        if len(clean_code) != 19:  # 16 chars + 3 dashes
            return False
        
        # Split by dashes and validate each segment
        segments = clean_code.split('-')
        if len(segments) != 4:
            return False
        
        for segment in segments:
            if len(segment) != 4:
                return False
            for char in segment:
                if char not in self.code_alphabet:
                    return False
        
        return True
    
    def normalize_code(self, code: str) -> str:
        """Normalize a gift code to standard format."""
        if not code:
            return ""
        
        # Remove whitespace, convert to uppercase
        clean_code = ''.join(code.split()).upper()
        
        # Remove existing dashes
        clean_code = clean_code.replace('-', '')
        
        # Add dashes in the correct positions
        if len(clean_code) == 16:
            return '-'.join([clean_code[i:i+4] for i in range(0, 16, 4)])
        
        return clean_code
    
    def create_security_hash(self, code: str, user_ip: str = None) -> str:
        """Create a security hash for the gift code."""
        message = f"{code}:{user_ip or 'unknown'}:{settings.SECRET_KEY}"
        return hmac.new(
            settings.SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
    
    def verify_security_hash(self, code: str, provided_hash: str, user_ip: str = None) -> bool:
        """Verify the security hash for a gift code."""
        expected_hash = self.create_security_hash(code, user_ip)
        return hmac.compare_digest(expected_hash, provided_hash)
    
    def calculate_expiry_date(self, days: Optional[int] = None) -> datetime:
        """Calculate the expiry date for a gift code."""
        expiry_days = days or self.code_expiry_days
        return datetime.now(timezone.utc) + timedelta(days=expiry_days)
    
    def validate_redemption_eligibility(
        self, 
        gift_code: GiftCode,
        user_ip: str = None,
        user_email: str = None
    ) -> Tuple[bool, str]:
        """
        Validate if a gift code is eligible for redemption.
        Returns (is_valid, error_message).
        """
        try:
            # Basic code validation
            if not gift_code.is_valid():
                return False, "Gift code is not valid or has already been used"
            
            # Check gift subscription
            gift_subscription = gift_code.gift_subscription
            if not gift_subscription:
                return False, "Invalid gift code - no associated subscription found"
            
            # Check if gift has expired
            if gift_subscription.is_expired():
                return False, "Gift code has expired"
            
            # Check if gift is already redeemed
            if gift_subscription.status == GiftStatus.REDEEMED:
                return False, "Gift code has already been redeemed"
            
            # Check if gift is cancelled
            if gift_subscription.status == GiftStatus.CANCELLED:
                return False, "Gift code has been cancelled"
            
            # Check payment status
            if not gift_subscription.gift_transaction:
                return False, "Gift payment has not been processed"
            
            if gift_subscription.gift_transaction.status != "completed":
                return False, "Gift payment is not complete"
            
            # Check recipient email if provided
            if user_email and gift_subscription.recipient_email.lower() != user_email.lower():
                return False, "Gift code is not valid for this email address"
            
            # Rate limiting check
            if self._check_rate_limiting(gift_code, user_ip):
                return False, "Too many redemption attempts. Please try again later"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error validating gift code redemption: {str(e)}")
            return False, "An error occurred while validating the gift code"
    
    def _check_rate_limiting(self, gift_code: GiftCode, user_ip: str = None) -> bool:
        """Check if the user has exceeded rate limiting for redemption attempts."""
        if not user_ip:
            return False
        
        # Check if too many attempts from this IP in the last hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # In a real implementation, you might want to use Redis for this
        # For now, we'll use the database
        from app.db.session import SessionLocal
        
        with SessionLocal() as db:
            recent_attempts = db.query(GiftCode).filter(
                GiftCode.last_attempt_ip == user_ip,
                GiftCode.last_attempt_at >= one_hour_ago
            ).count()
            
            return recent_attempts >= self.max_attempts_per_hour
    
    def record_redemption_attempt(
        self, 
        gift_code: GiftCode,
        user_ip: str = None,
        success: bool = False
    ) -> None:
        """Record a redemption attempt for security tracking."""
        try:
            gift_code.increment_attempt(user_ip)
            
            if success:
                gift_code.redeem()
                logger.info(f"Gift code {gift_code.code} successfully redeemed")
            else:
                logger.warning(f"Failed redemption attempt for gift code {gift_code.code} from IP {user_ip}")
                
        except Exception as e:
            logger.error(f"Error recording redemption attempt: {str(e)}")
    
    def generate_redemption_url(self, gift_code: str, base_url: str = None) -> str:
        """Generate a redemption URL for a gift code."""
        base_url = base_url or settings.FRONTEND_URL
        return f"{base_url}/gift/redeem?code={gift_code}"
    
    def create_gift_code_data(
        self,
        gift_subscription_id: int,
        user_ip: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """Create the data structure for a new gift code."""
        code = self.generate_unique_code()
        
        return {
            "code": code,
            "gift_subscription_id": gift_subscription_id,
            "is_active": True,
            "max_redemptions": 1,
            "current_redemptions": 0,
            "redemption_attempts": 0,
            "ip_address": user_ip,
            "user_agent": user_agent,
        }
    
    def mask_gift_code(self, code: str, show_last: int = 4) -> str:
        """Mask a gift code for display purposes."""
        if not code or len(code) < show_last:
            return "****-****-****-****"
        
        # Normalize the code first
        normalized = self.normalize_code(code)
        if len(normalized) != 19:  # Expected format length
            return "****-****-****-****"
        
        # Show only the last segment
        segments = normalized.split('-')
        masked_segments = ['****' for _ in segments[:-1]] + [segments[-1]]
        return '-'.join(masked_segments)
    
    def get_code_strength_score(self, code: str) -> int:
        """Calculate a strength score for the gift code (for internal use)."""
        if not self.validate_code_format(code):
            return 0
        
        score = 50  # Base score for valid format
        
        # Check character diversity
        clean_code = code.replace('-', '')
        unique_chars = len(set(clean_code))
        score += min(unique_chars * 3, 30)  # Max 30 points for diversity
        
        # Check if code follows expected patterns (avoid sequential)
        has_sequence = any(
            ord(clean_code[i]) == ord(clean_code[i+1]) - 1 
            for i in range(len(clean_code) - 1)
        )
        if not has_sequence:
            score += 20
        
        return min(score, 100)


# Create singleton instance
gift_code_service = GiftCodeService()