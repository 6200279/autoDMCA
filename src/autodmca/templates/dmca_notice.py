"""
DMCA Notice Templates

Legally compliant DMCA takedown notice templates following 17 U.S.C. § 512(c)(3).
Supports both standard notices and follow-up communications with anonymity protection.
"""

from typing import Dict, Any, Optional
from datetime import datetime

# Standard DMCA Notice Template (17 U.S.C. § 512(c)(3) compliant)
DMCA_NOTICE_TEMPLATE = """
Subject: DMCA Takedown Notice - Copyright Infringement Claim

To Whom It May Concern:

This is a formal notice of copyright infringement submitted pursuant to the Digital Millennium Copyright Act (DMCA), 17 U.S.C. § 512(c)(3)(A).

I am writing on behalf of the copyright owner {{ creator_name }}{% if agent_representation %}, as their authorized agent,{% endif %} to request the removal of copyrighted material that is being infringed upon.

**IDENTIFICATION OF COPYRIGHTED WORK:**

The copyrighted work that is being infringed is:
Title: {{ original_work_title }}
Description: {{ original_work_description }}
{% if copyright_registration %}Registration Number: {{ copyright_registration }}
{% endif %}{% if creation_date %}Date of Creation: {{ creation_date }}
{% endif %}{% if publication_date %}Date of Publication: {{ publication_date }}
{% endif %}{% if original_work_urls %}Original Work Location(s):
{% for url in original_work_urls %}- {{ url }}
{% endfor %}{% endif %}

**IDENTIFICATION OF INFRINGING MATERIAL:**

The infringing material is located at the following URL(s):
- {{ infringing_url }}

Description of infringing material: {{ infringement_description }}
{% if screenshot_url %}
Evidence of infringement: {{ screenshot_url }}
{% endif %}
**STATEMENT OF GOOD FAITH BELIEF:**

I have a good faith belief that the use of the copyrighted material described above is not authorized by the copyright owner, its agent, or the law.

**STATEMENT OF ACCURACY:**

I swear, under penalty of perjury, that the information in this notification is accurate and that I am authorized to act on behalf of the owner of an exclusive right that is allegedly infringed.

**CONTACT INFORMATION:**

{% if use_anonymity and agent_contact %}
{{ agent_contact.name }}
{{ agent_contact.title }}
{% if agent_contact.organization %}{{ agent_contact.organization }}
{% endif %}{{ agent_contact.get_formatted_address() }}
Email: {{ agent_contact.email }}
{% if agent_contact.phone %}Phone: {{ agent_contact.phone }}
{% endif %}
{% else %}
{{ creator_name }}
{% if creator_business_name %}{{ creator_business_name }}
{% endif %}{{ creator_address }}
Email: {{ creator_email }}
{% if creator_phone %}Phone: {{ creator_phone }}
{% endif %}
{% endif %}

**ELECTRONIC SIGNATURE:**

{{ signature_name }}
Date: {{ current_date }}

**REQUEST FOR CONFIRMATION:**

Please confirm receipt of this notice and provide updates on the status of this takedown request. We appreciate your cooperation in this matter and look forward to the prompt removal of the infringing content.

If you have any questions regarding this notice, please contact us at the email address provided above.

Thank you for your attention to this matter.

---
This notice is sent in good faith and in compliance with the Digital Millennium Copyright Act (DMCA). Misuse of this process may result in liability for damages, including costs and attorney fees.
"""


# Follow-up Notice Template
DMCA_FOLLOWUP_TEMPLATE = """
Subject: Follow-up: DMCA Takedown Notice - {{ original_work_title }}

To Whom It May Concern:

This is a follow-up to our DMCA takedown notice originally sent on {{ original_notice_date }} regarding copyright infringement at the following URL:

{{ infringing_url }}

**ORIGINAL REQUEST SUMMARY:**
We requested the removal of copyrighted material belonging to {{ creator_name }}, specifically:
- Title: {{ original_work_title }}
- Description: {{ original_work_description }}

**CURRENT STATUS:**
We have not received confirmation that the infringing content has been removed, nor have we received any response to our original notice. The content appears to still be accessible at the URL mentioned above.

**LEGAL REQUIREMENTS:**
Under the DMCA (17 U.S.C. § 512(c)(3)), service providers are required to expeditiously remove or disable access to infringing material upon receipt of a proper takedown notice. Failure to do so may result in loss of safe harbor protections under the DMCA.

**NEXT STEPS:**
We kindly request that you:
1. Remove or disable access to the infringing content immediately
2. Confirm the removal via email to the address below
3. Provide a timeline for when the content will be permanently removed

If the content is not removed within {{ response_deadline_days }} days of this notice, we may be compelled to:
- File complaints with search engines to delist the infringing URLs
- Report this matter to your upstream internet service provider
- Consider other legal remedies available under copyright law

**CONTACT INFORMATION:**
{% if use_anonymity and agent_contact %}
{{ agent_contact.name }}
{{ agent_contact.title }}
{% if agent_contact.organization %}{{ agent_contact.organization }}
{% endif %}Email: {{ agent_contact.email }}
{% if agent_contact.phone %}Phone: {{ agent_contact.phone }}
{% endif %}
{% else %}
{{ creator_name }}
Email: {{ creator_email }}
{% if creator_phone %}Phone: {{ creator_phone }}
{% endif %}
{% endif %}

We appreciate your prompt attention to this matter and look forward to your cooperation.

Best regards,

{{ signature_name }}
Date: {{ current_date }}

---
This is follow-up notice #{{ followup_number }} regarding this matter.
"""


# Final Notice Template (before escalation)
DMCA_FINAL_NOTICE_TEMPLATE = """
Subject: FINAL NOTICE: DMCA Takedown - Legal Action Pending

To Whom It May Concern:

This is our final notice regarding the copyright infringement claim we originally submitted on {{ original_notice_date }}.

**INFRINGEMENT DETAILS:**
URL: {{ infringing_url }}
Copyrighted Work: {{ original_work_title }}
Copyright Owner: {{ creator_name }}

**NOTICE HISTORY:**
- Original notice sent: {{ original_notice_date }}
{% for followup_date in followup_dates %}- Follow-up sent: {{ followup_date }}
{% endfor %}

**FAILURE TO COMPLY:**
Despite our repeated requests, the infringing content remains accessible, and we have not received any response or confirmation of removal. This failure to act may constitute:

1. Willful copyright infringement under 17 U.S.C. § 501
2. Loss of DMCA safe harbor protections under 17 U.S.C. § 512
3. Potential liability for statutory damages up to $150,000 per work infringed

**FINAL OPPORTUNITY:**
This serves as your final opportunity to remove the infringing content before we pursue additional remedies, which may include:

- Filing complaints with major search engines to delist your content
- Reporting to payment processors and advertising networks
- Filing complaints with domain registrars and hosting providers
- Pursuing legal action for copyright infringement
- Seeking injunctive relief and monetary damages

**IMMEDIATE ACTION REQUIRED:**
You have {{ final_deadline_days }} days from the date of this notice to:
1. Remove or disable the infringing content
2. Confirm removal in writing
3. Implement measures to prevent future infringement

**CONTACT FOR RESOLUTION:**
{% if use_anonymity and agent_contact %}
{{ agent_contact.name }}
{{ agent_contact.title }}
Email: {{ agent_contact.email }}
{% if agent_contact.phone %}Phone: {{ agent_contact.phone }}
{% endif %}
{% else %}
{{ creator_name }}
Email: {{ creator_email }}
{% if creator_phone %}Phone: {{ creator_phone }}
{% endif %}
{% endif %}

Failure to respond to this final notice will be considered an indication of your intent to continue the infringement, and we will proceed accordingly.

{{ signature_name }}
Date: {{ current_date }}

---
LEGAL WARNING: This notice is sent pursuant to the Digital Millennium Copyright Act. False claims may result in liability for damages, including costs and attorneys' fees under 17 U.S.C. § 512(f).
"""


# Search Engine Delisting Request Template
SEARCH_DELISTING_TEMPLATE = """
I am requesting the removal of search results that link to content infringing upon copyrighted material owned by {{ creator_name }}.

**COPYRIGHTED WORK INFORMATION:**
Title: {{ original_work_title }}
Description: {{ original_work_description }}
{% if original_work_urls %}Original Location: {{ original_work_urls[0] }}
{% endif %}
**INFRINGING URLS TO BE REMOVED FROM SEARCH RESULTS:**
{% for url in infringing_urls %}{{ url }}
{% endfor %}

**STATEMENT:**
I have a good faith belief that the use of the described material is not authorized by the copyright owner, its agent, or the law.

I swear, under penalty of perjury, that the information in this request is accurate and that I am authorized to act on behalf of the copyright owner.

{% if use_anonymity and agent_contact %}
Name: {{ agent_contact.name }}
Title: {{ agent_contact.title }}
Email: {{ agent_contact.email }}
Address: {{ agent_contact.get_formatted_address() }}
{% else %}
Name: {{ creator_name }}
Email: {{ creator_email }}
Address: {{ creator_address }}
{% endif %}

Electronic Signature: {{ signature_name }}
Date: {{ current_date }}
"""


class DMCANoticeTemplate:
    """
    DMCA notice template handler with legal compliance validation.
    """
    
    @staticmethod
    def get_standard_notice() -> str:
        """Get the standard DMCA takedown notice template."""
        return DMCA_NOTICE_TEMPLATE.strip()
    
    @staticmethod  
    def get_followup_notice() -> str:
        """Get the follow-up notice template."""
        return DMCA_FOLLOWUP_TEMPLATE.strip()
    
    @staticmethod
    def get_final_notice() -> str:
        """Get the final notice template before escalation."""
        return DMCA_FINAL_NOTICE_TEMPLATE.strip()
    
    @staticmethod
    def get_search_delisting_template() -> str:
        """Get the search engine delisting request template."""
        return SEARCH_DELISTING_TEMPLATE.strip()
    
    @staticmethod
    def validate_template_variables(template: str, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate that all required template variables are provided.
        
        Returns:
            Dict of missing or invalid variables with error descriptions.
        """
        import re
        from jinja2 import Environment, meta
        
        errors = {}
        
        # Extract template variables
        env = Environment()
        parsed = env.parse(template)
        required_vars = meta.find_undeclared_variables(parsed)
        
        # Check for missing required variables
        for var in required_vars:
            if var not in variables:
                errors[var] = f"Required variable '{var}' is missing"
                continue
            
            value = variables[var]
            
            # Validate specific variable types
            if var.endswith('_email') and value:
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(value)):
                    errors[var] = f"Invalid email format: {value}"
            
            elif var.endswith('_url') and value:
                if not str(value).startswith(('http://', 'https://')):
                    errors[var] = f"Invalid URL format: {value}"
            
            elif var.endswith('_date') and value:
                if not isinstance(value, (str, datetime)):
                    errors[var] = f"Invalid date format: {value}"
        
        # Check for DMCA-specific requirements
        if 'creator_name' not in variables or not variables['creator_name']:
            errors['creator_name'] = "Creator name is required for DMCA compliance"
        
        if 'original_work_title' not in variables or not variables['original_work_title']:
            errors['original_work_title'] = "Original work title is required"
        
        if 'infringing_url' not in variables or not variables['infringing_url']:
            errors['infringing_url'] = "Infringing URL is required"
        
        return errors


class DMCAFollowupTemplate:
    """
    Follow-up and escalation templates for DMCA notices.
    """
    
    @staticmethod
    def get_first_followup() -> str:
        """Get the first follow-up template (polite reminder)."""
        return DMCA_FOLLOWUP_TEMPLATE.strip()
    
    @staticmethod
    def get_second_followup() -> str:
        """Get the second follow-up template (more urgent)."""
        # More urgent version of the follow-up
        return DMCA_FOLLOWUP_TEMPLATE.replace(
            "We kindly request",
            "We urgently request"
        ).replace(
            "we may be compelled to:",
            "we will proceed to:"
        ).strip()
    
    @staticmethod
    def get_final_notice() -> str:
        """Get the final notice before legal escalation."""
        return DMCA_FINAL_NOTICE_TEMPLATE.strip()
    
    @staticmethod
    def get_escalation_warning() -> str:
        """Get a pre-legal escalation warning template."""
        return """
This matter will be referred to our legal counsel for further action if the infringing content is not removed within the specified timeframe. Such action may include filing a federal lawsuit for copyright infringement, seeking monetary damages, and requesting injunctive relief.

We prefer to resolve this matter cooperatively and avoid litigation. Please contact us immediately to discuss removal of the infringing content.
        """.strip()


# Email subject line templates
SUBJECT_TEMPLATES = {
    'initial': 'DMCA Takedown Notice - Copyright Infringement Claim',
    'followup_1': 'DMCA Follow-up: Removal Request for {title}',
    'followup_2': 'URGENT: DMCA Takedown Notice - {title}',
    'final': 'FINAL NOTICE: DMCA Takedown - Legal Action Pending',
    'search_delisting': 'Copyright Removal Request - {title}',
}

def get_subject_line(notice_type: str, **kwargs) -> str:
    """
    Generate appropriate subject line for DMCA notices.
    
    Args:
        notice_type: Type of notice (initial, followup_1, etc.)
        **kwargs: Template variables for subject line
    
    Returns:
        Formatted subject line
    """
    template = SUBJECT_TEMPLATES.get(notice_type, SUBJECT_TEMPLATES['initial'])
    return template.format(**kwargs)