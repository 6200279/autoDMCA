/**
 * DMCA Legal Guidelines and Compliance Requirements
 * 
 * This file contains comprehensive legal information about DMCA takedown notices
 * and compliance requirements as specified in 17 U.S.C. § 512(c)(3).
 * 
 * DISCLAIMER: This information is for educational purposes only and does not 
 * constitute legal advice. Always consult with a qualified attorney for 
 * legal matters specific to your situation.
 */

export interface LegalRequirement {
  section: string;
  title: string;
  description: string;
  legalText: string;
  mandatoryElements: string[];
  commonMistakes: string[];
  bestPractices: string[];
}

export interface JurisdictionRequirement {
  country: string;
  framework: string;
  specificRequirements: string[];
  additionalConsiderations: string[];
  relevantStatutes: string[];
}

export interface PlatformRequirement {
  platform: string;
  specificRequirements: string[];
  submissionProcess: string;
  responseTimeExpected: string;
  escalationProcess: string[];
}

// DMCA Section 512(c)(3) Requirements
export const DMCA_SECTION_512_REQUIREMENTS: LegalRequirement[] = [
  {
    section: "17 U.S.C. § 512(c)(3)(A)(i)",
    title: "Physical or Electronic Signature",
    description: "A physical or electronic signature of a person authorized to act on behalf of the owner of an exclusive right that is allegedly infringed.",
    legalText: "A physical or electronic signature of a person authorized to act on behalf of the owner of an exclusive right that is allegedly infringed;",
    mandatoryElements: [
      "Physical signature on paper document, or",
      "Electronic signature (typed name, digital signature, etc.)",
      "Clear indication of authorization to act on behalf of copyright owner"
    ],
    commonMistakes: [
      "Missing signature entirely",
      "Using initials instead of full signature",
      "Not indicating authorization when acting as agent"
    ],
    bestPractices: [
      "Use full legal name for signature",
      "If acting as agent, clearly state authorization",
      "Consider using digital signature tools for enhanced security"
    ]
  },
  {
    section: "17 U.S.C. § 512(c)(3)(A)(ii)",
    title: "Identification of Copyrighted Work",
    description: "Identification of the copyrighted work claimed to have been infringed, or, if multiple copyrighted works at a single online site are covered by a single notification, a representative list of such works at that site.",
    legalText: "identification of the copyrighted work claimed to have been infringed or, if multiple copyrighted works at a single online site are covered by a single notification, a representative list of such works at that site;",
    mandatoryElements: [
      "Clear description of the copyrighted work",
      "Title of the work (if applicable)",
      "Date of creation or publication",
      "Copyright registration number (if available)",
      "For multiple works: representative list"
    ],
    commonMistakes: [
      "Vague descriptions like 'my content'",
      "Not providing enough detail to identify the work",
      "Failing to list multiple works when claiming bulk infringement"
    ],
    bestPractices: [
      "Be as specific as possible in describing the work",
      "Include URLs to original work if available online",
      "Provide copyright registration information when available",
      "For photographs: include titles, dates, and technical details"
    ]
  },
  {
    section: "17 U.S.C. § 512(c)(3)(A)(iii)",
    title: "Identification of Infringing Material",
    description: "Identification of the material that is claimed to be infringing or to be the subject of infringing activity and that is to be removed or access to which is to be disabled, and information reasonably sufficient to permit the service provider to locate the material.",
    legalText: "identification of the material that is claimed to be infringing or to be the subject of infringing activity and that is to be removed or access to which is to be disabled and information reasonably sufficient to permit the service provider to locate the material;",
    mandatoryElements: [
      "Specific URL or location of infringing material",
      "Sufficient detail to locate the material",
      "Description of how the material infringes",
      "Platform-specific identifiers when available"
    ],
    commonMistakes: [
      "Providing only domain names instead of specific URLs",
      "Insufficient information to locate the content",
      "Not explaining how the material infringes"
    ],
    bestPractices: [
      "Provide exact URLs to infringing content",
      "Include screenshots or other evidence",
      "For social media: include post IDs, usernames, timestamps",
      "Describe the infringing activity clearly"
    ]
  },
  {
    section: "17 U.S.C. § 512(c)(3)(A)(iv)",
    title: "Contact Information",
    description: "Information reasonably sufficient to permit the service provider to contact the complaining party, such as an address, telephone number, and, if available, an electronic mail address at which the complaining party may be contacted.",
    legalText: "information reasonably sufficient to permit the service provider to contact the complaining party, such as an address, telephone number, and, if available, an electronic mail address at which the complaining party may be contacted;",
    mandatoryElements: [
      "Full legal name",
      "Physical mailing address",
      "Telephone number",
      "Email address (if available)"
    ],
    commonMistakes: [
      "Using only email without physical address",
      "Providing incomplete contact information",
      "Using fake or temporary contact details"
    ],
    bestPractices: [
      "Provide complete, accurate contact information",
      "Use business address for professional appearance",
      "Ensure all contact methods are monitored",
      "Consider using a legal representative's contact info"
    ]
  },
  {
    section: "17 U.S.C. § 512(c)(3)(A)(v)",
    title: "Good Faith Statement",
    description: "A statement that the complaining party has a good faith belief that use of the material in the manner complained of is not authorized by the copyright owner, its agent, or the law.",
    legalText: "a statement that the complaining party has a good faith belief that use of the material in the manner complained of is not authorized by the copyright owner, its agent, or the law;",
    mandatoryElements: [
      "Express statement of good faith belief",
      "Reference to unauthorized use",
      "Clear indication that use is not authorized by owner, agent, or law"
    ],
    commonMistakes: [
      "Omitting the good faith statement entirely",
      "Using weak language like 'I think' or 'I believe'",
      "Not addressing authorization by owner, agent, or law"
    ],
    bestPractices: [
      "Use strong, definitive language",
      "Include all three categories: owner, agent, law",
      "Consider fair use and other potential defenses",
      "Document efforts to contact infringer when appropriate"
    ]
  },
  {
    section: "17 U.S.C. § 512(c)(3)(A)(vi)",
    title: "Accuracy and Perjury Statement",
    description: "A statement that the information in the notification is accurate, and under penalty of perjury, that the complaining party is authorized to act on behalf of the owner of an exclusive right that is allegedly infringed.",
    legalText: "a statement that the information in the notification is accurate, and under penalty of perjury, that the complaining party is authorized to act on behalf of the owner of an exclusive right that is allegedly infringed.",
    mandatoryElements: [
      "Statement that information is accurate",
      "Under penalty of perjury language",
      "Authorization to act on behalf of copyright owner",
      "Reference to exclusive right that is infringed"
    ],
    commonMistakes: [
      "Omitting 'under penalty of perjury' language",
      "Not stating that information is accurate",
      "Failing to address authorization when acting as agent",
      "Not specifying the exclusive right"
    ],
    bestPractices: [
      "Use exact perjury language from statute",
      "Ensure all information is actually accurate",
      "If acting as agent, have written authorization",
      "Understand the penalties for perjury (criminal and civil)"
    ]
  }
];

// International Jurisdiction Requirements
export const INTERNATIONAL_REQUIREMENTS: JurisdictionRequirement[] = [
  {
    country: "United States",
    framework: "Digital Millennium Copyright Act (DMCA)",
    specificRequirements: [
      "Must comply with 17 U.S.C. § 512(c)(3)",
      "Safe harbor provisions apply",
      "Counter-notification process available under § 512(g)"
    ],
    additionalConsiderations: [
      "Fair use doctrine may apply",
      "First Amendment considerations",
      "State law claims may also be available"
    ],
    relevantStatutes: [
      "17 U.S.C. § 512 (DMCA Safe Harbor)",
      "17 U.S.C. § 106 (Exclusive Rights)",
      "17 U.S.C. § 107 (Fair Use)"
    ]
  },
  {
    country: "European Union",
    framework: "EU Copyright Directive (2001/29/EC) & DSA",
    specificRequirements: [
      "Notice must be sufficiently precise and adequately substantiated",
      "Must respect fundamental rights including freedom of expression",
      "Platform must act expeditiously on valid notices"
    ],
    additionalConsiderations: [
      "GDPR compliance required for personal data",
      "National implementations may vary",
      "Digital Services Act (DSA) obligations"
    ],
    relevantStatutes: [
      "Directive 2001/29/EC (InfoSoc Directive)",
      "Directive 2000/31/EC (E-Commerce Directive)",
      "Digital Services Act (DSA)"
    ]
  },
  {
    country: "United Kingdom",
    framework: "Copyright, Designs and Patents Act 1988",
    specificRequirements: [
      "Notice must identify copyrighted work",
      "Must show prima facie case of infringement",
      "Platform must act expeditiously"
    ],
    additionalConsiderations: [
      "UK GDPR compliance",
      "Human Rights Act considerations",
      "Common law remedies available"
    ],
    relevantStatutes: [
      "Copyright, Designs and Patents Act 1988",
      "Electronic Commerce (EC Directive) Regulations 2002",
      "UK GDPR"
    ]
  },
  {
    country: "Canada",
    framework: "Copyright Act (R.S.C. 1985, c. C-42)",
    specificRequirements: [
      "Notice and notice system (not notice and takedown)",
      "Must identify copyrighted work and infringement location",
      "Platform forwards notice to user, no automatic removal"
    ],
    additionalConsiderations: [
      "PIPEDA privacy law compliance",
      "Charter of Rights and Freedoms",
      "Provincial privacy laws may apply"
    ],
    relevantStatutes: [
      "Copyright Act (R.S.C. 1985, c. C-42)",
      "Personal Information Protection and Electronic Documents Act (PIPEDA)",
      "Charter of Rights and Freedoms"
    ]
  },
  {
    country: "Australia",
    framework: "Copyright Act 1968",
    specificRequirements: [
      "Notice must comply with safe harbor provisions",
      "Must identify copyrighted work and infringing material",
      "Good faith belief requirement"
    ],
    additionalConsiderations: [
      "Privacy Act 1988 compliance",
      "Australian Consumer Law",
      "Telecommunications Act requirements"
    ],
    relevantStatutes: [
      "Copyright Act 1968",
      "Privacy Act 1988",
      "Telecommunications Act 1997"
    ]
  }
];

// Platform-Specific Requirements
export const PLATFORM_REQUIREMENTS: PlatformRequirement[] = [
  {
    platform: "Google",
    specificRequirements: [
      "Must use Google's online copyright removal form",
      "Requires Google account for submission",
      "Must provide specific URLs for each infringing item",
      "Screenshots or evidence may be required"
    ],
    submissionProcess: "Online form at https://www.google.com/webmasters/tools/legal-removal-request",
    responseTimeExpected: "24-48 hours for evaluation",
    escalationProcess: [
      "Submit additional documentation if rejected",
      "Contact legal support for complex cases",
      "Consider court order for non-compliance"
    ]
  },
  {
    platform: "Instagram",
    specificRequirements: [
      "Must have Instagram account or use online form",
      "Requires direct link to infringing post",
      "Must provide link to original copyrighted work",
      "Photo identification of infringement location"
    ],
    submissionProcess: "Instagram Help Center copyright form",
    responseTimeExpected: "24-72 hours",
    escalationProcess: [
      "Appeal through Instagram if rejected",
      "Contact Meta's legal team",
      "Submit repeat infringer notice if applicable"
    ]
  },
  {
    platform: "TikTok",
    specificRequirements: [
      "Must provide TikTok video URL",
      "Requires timestamp of infringing content",
      "Must have proof of original work ownership",
      "Account information of infringer"
    ],
    submissionProcess: "TikTok Copyright Webform",
    responseTimeExpected: "2-5 business days",
    escalationProcess: [
      "Submit counter-notification response",
      "Escalate to TikTok legal team",
      "Consider repeat infringer program"
    ]
  },
  {
    platform: "YouTube",
    specificRequirements: [
      "Must have YouTube account for Content ID",
      "Requires specific video URL and timestamp",
      "Must provide evidence of ownership",
      "May require copyright registration"
    ],
    submissionProcess: "YouTube Studio Copyright Match Tool or webform",
    responseTimeExpected: "1-2 business days",
    escalationProcess: [
      "Use Content ID system for automation",
      "Submit repeat infringer complaints",
      "Legal escalation through Partner Program"
    ]
  },
  {
    platform: "OnlyFans",
    specificRequirements: [
      "Must provide specific profile URL",
      "Requires detailed content description",
      "Must show original work ownership",
      "May require age verification for viewing"
    ],
    submissionProcess: "OnlyFans DMCA Agent contact",
    responseTimeExpected: "3-7 business days",
    escalationProcess: [
      "Follow up with legal team",
      "Provide additional evidence",
      "Consider payment processor notification"
    ]
  }
];

// Legal Best Practices
export const LEGAL_BEST_PRACTICES = {
  beforeSending: [
    "Ensure you own or control the copyright",
    "Document the original work creation date",
    "Take screenshots of infringing content",
    "Research fair use and other potential defenses",
    "Check if content is licensed or authorized",
    "Consider alternative dispute resolution"
  ],
  documentation: [
    "Maintain detailed records of all notices sent",
    "Keep proof of copyright ownership",
    "Document platform responses and actions taken",
    "Track removal dates and compliance",
    "Save evidence before it may be removed",
    "Maintain correspondence with infringers"
  ],
  followUp: [
    "Monitor for compliance within reasonable time",
    "Send follow-up notices if content not removed",
    "Document non-compliance for repeat infringer claims",
    "Consider escalation to legal action if necessary",
    "Track counter-notifications and respond appropriately",
    "Maintain professional communication throughout"
  ],
  avoidance: [
    "Never send notices for content you don't own",
    "Don't use DMCA notices for non-copyright issues",
    "Avoid automated systems without human review",
    "Don't threaten legal action unless prepared to follow through",
    "Never provide false information in notices",
    "Don't ignore valid counter-notifications"
  ]
};

// Penalties and Consequences
export const LEGAL_PENALTIES = {
  falseClaims: {
    description: "Knowingly materially misrepresenting infringement",
    statute: "17 U.S.C. § 512(f)",
    penalties: [
      "Damages suffered by alleged infringer",
      "Attorney's fees and costs",
      "Potential perjury charges (criminal)",
      "Sanctions in federal court proceedings"
    ]
  },
  perjury: {
    description: "Making false statements under penalty of perjury",
    statute: "18 U.S.C. § 1621",
    penalties: [
      "Up to 5 years imprisonment",
      "Substantial fines",
      "Criminal record",
      "Civil liability for damages"
    ]
  },
  abuse: {
    description: "Systematic abuse of DMCA process",
    statute: "Various state and federal laws",
    penalties: [
      "Injunctive relief preventing further notices",
      "Monetary sanctions",
      "Attorney's fees",
      "Defamation or tortious interference claims"
    ]
  }
};

// Template Quality Scoring Criteria
export const TEMPLATE_QUALITY_CRITERIA = {
  legal_completeness: {
    weight: 40,
    criteria: [
      "Contains all six required elements",
      "Uses proper legal language",
      "Includes penalty of perjury statement",
      "Addresses authorization properly"
    ]
  },
  clarity: {
    weight: 25,
    criteria: [
      "Clear, professional language",
      "Specific rather than vague descriptions",
      "Proper grammar and spelling",
      "Logical organization and flow"
    ]
  },
  effectiveness: {
    weight: 20,
    criteria: [
      "Provides sufficient detail for action",
      "Anticipates common responses",
      "Includes relevant evidence requests",
      "Professional tone throughout"
    ]
  },
  platform_optimization: {
    weight: 15,
    criteria: [
      "Addresses platform-specific requirements",
      "Appropriate length for platform",
      "Uses platform terminology correctly",
      "Includes platform-specific identifiers"
    ]
  }
};

/**
 * Calculate template quality score based on defined criteria
 */
export const calculateTemplateQualityScore = (
  template: string,
  platform?: string
): { score: number; breakdown: Record<string, number>; suggestions: string[] } => {
  const breakdown: Record<string, number> = {};
  const suggestions: string[] = [];

  // Legal completeness scoring
  let legalScore = 0;
  const requiredElements = [
    /signature/i,
    /(copyrighted?\s+work|original\s+work)/i,
    /(infringing?\s+(material|content|url))/i,
    /(contact|email|address|phone)/i,
    /good\s+faith\s+belief/i,
    /penalty\s+of\s+perjury/i
  ];

  requiredElements.forEach((pattern, index) => {
    if (pattern.test(template)) {
      legalScore += 100 / requiredElements.length;
    } else {
      const elements = [
        'signature requirement',
        'copyrighted work identification',
        'infringing material identification',
        'contact information',
        'good faith statement',
        'perjury statement'
      ];
      suggestions.push(`Missing ${elements[index]}`);
    }
  });

  breakdown.legal_completeness = legalScore;

  // Clarity scoring
  let clarityScore = 100;
  if (template.length < 200) {
    clarityScore -= 20;
    suggestions.push('Template may be too brief');
  }
  if (template.length > 2000) {
    clarityScore -= 10;
    suggestions.push('Template may be too lengthy');
  }
  if ((template.match(/\b(this|that|it)\b/gi) || []).length > 5) {
    clarityScore -= 15;
    suggestions.push('Reduce use of vague pronouns');
  }

  breakdown.clarity = Math.max(0, clarityScore);

  // Effectiveness scoring
  let effectivenessScore = 50;
  if (/respectfully|kindly|please/i.test(template)) {
    effectivenessScore += 20;
  } else {
    suggestions.push('Consider adding more courteous language');
  }
  if (/specific|detailed|exact/i.test(template)) {
    effectivenessScore += 15;
  }
  if (/deadline|timeframe|expeditious/i.test(template)) {
    effectivenessScore += 15;
  } else {
    suggestions.push('Consider including response timeline expectations');
  }

  breakdown.effectiveness = Math.min(100, effectivenessScore);

  // Platform optimization scoring
  let platformScore = 80; // Base score
  if (platform) {
    const platformKeywords = {
      'Instagram': ['post', 'instagram', 'photo', 'story'],
      'TikTok': ['video', 'tiktok', 'clip', 'sound'],
      'YouTube': ['video', 'youtube', 'channel', 'content id'],
      'OnlyFans': ['profile', 'content', 'subscription', 'creator'],
      'Google': ['search', 'results', 'indexing', 'webmaster']
    };

    const keywords = platformKeywords[platform as keyof typeof platformKeywords] || [];
    const foundKeywords = keywords.filter(keyword => 
      new RegExp(keyword, 'i').test(template)
    ).length;

    if (foundKeywords === 0) {
      platformScore -= 30;
      suggestions.push(`Consider adding ${platform}-specific terminology`);
    } else if (foundKeywords < keywords.length / 2) {
      platformScore -= 15;
    }
  }

  breakdown.platform_optimization = platformScore;

  // Calculate weighted final score
  const weights = TEMPLATE_QUALITY_CRITERIA;
  const finalScore = Math.round(
    (breakdown.legal_completeness * weights.legal_completeness.weight +
     breakdown.clarity * weights.clarity.weight +
     breakdown.effectiveness * weights.effectiveness.weight +
     breakdown.platform_optimization * weights.platform_optimization.weight) / 100
  );

  return {
    score: finalScore,
    breakdown,
    suggestions: suggestions.slice(0, 5) // Limit to top 5 suggestions
  };
};