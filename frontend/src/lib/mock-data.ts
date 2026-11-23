/**
 * SupportPilot AI — Comprehensive Realistic Mock Data
 * Used across the dashboard, tickets, live chat, human inbox, and analytics.
 */

export interface MockTicket {
  id: string;
  ticketNumber: string;
  subject: string;
  description: string;
  customerName: string;
  customerEmail: string;
  customerAvatar?: string;
  status: "open" | "assigned" | "in_progress" | "pending_review" | "escalated" | "resolved" | "closed";
  priority: "low" | "medium" | "high" | "urgent";
  channel: "email" | "chat" | "api" | "portal";
  category: "Billing" | "Technical" | "Account" | "Security" | "Feature Request" | "API Integration";
  assignedTo?: {
    id: string;
    name: string;
    avatar: string;
    role: string;
  };
  aiSuggestedResponse?: string;
  aiConfidenceScore?: number;
  aiQualityScore?: number;
  aiDeflected?: boolean;
  createdAt: string;
  updatedAt: string;
  slaBreachHours?: number;
  tags: string[];
  messages: Array<{
    id: string;
    sender: "customer" | "agent" | "ai" | "system";
    senderName: string;
    content: string;
    timestamp: string;
    isInternal?: boolean;
    citations?: string[];
  }>;
}

export interface AgentActivity {
  id: string;
  agentName: "Classifier Agent" | "Retriever Agent" | "Generator Agent" | "Evaluator Agent";
  action: string;
  ticketId: string;
  ticketSubject: string;
  status: "completed" | "processing" | "flagged" | "failed";
  latencyMs: number;
  tokensUsed: number;
  confidence: number;
  timestamp: string;
  details: string;
}

export const MOCK_TICKETS: MockTicket[] = [
  {
    id: "tkt_001",
    ticketNumber: "SP-4892",
    subject: "Stripe webhook failing with 401 Unauthorized after key rotation",
    description: "We rotated our production API keys this morning following our quarterly security audit. Since then, incoming customer subscription renewals via Stripe are timing out or returning 401. This is blocking invoice generation for ~120 enterprise accounts.",
    customerName: "Sarah Jenkins",
    customerEmail: "s.jenkins@cloudscale.io",
    status: "escalated",
    priority: "urgent",
    channel: "api",
    category: "Technical",
    assignedTo: {
      id: "usr_01",
      name: "Marcus Vance",
      avatar: "MV",
      role: "Senior Escalations Engineer",
    },
    aiSuggestedResponse: "Hi Sarah,\n\nI understand how critical this renewal blocker is. When rotating webhook keys, the webhook endpoint secret must be updated concurrently in both the Stripe Dashboard and your SupportPilot Webhook settings (`Settings > Webhooks > Stripe Endpoint Secret`).\n\nPlease confirm if the new signing secret starts with `whsec_` and whether old webhooks are being retried. I can also temporarily extend grace-period invoicing on our end while you apply the update.",
    aiConfidenceScore: 0.94,
    aiQualityScore: 0.91,
    aiDeflected: false,
    createdAt: "2026-11-23T09:14:00Z",
    updatedAt: "2026-11-23T09:42:00Z",
    slaBreachHours: 1.2,
    tags: ["stripe", "webhooks", "billing-blocker", "tier-1"],
    messages: [
      {
        id: "m_001",
        sender: "customer",
        senderName: "Sarah Jenkins",
        content: "We rotated our production API keys this morning following our quarterly security audit. Since then, incoming customer subscription renewals via Stripe are timing out or returning 401. This is blocking invoice generation for ~120 enterprise accounts.",
        timestamp: "2026-11-23T09:14:00Z",
      },
      {
        id: "m_002",
        sender: "ai",
        senderName: "SupportPilot AI Assistant",
        content: "Automated triage completed. Classified as Technical / Urgent. Relevant runbook retrieved: 'Stripe Webhook Signature Verification Troubleshooting'. Escalated to On-Call Senior Engineer.",
        timestamp: "2026-11-23T09:14:08Z",
        isInternal: true,
      },
      {
        id: "m_003",
        sender: "agent",
        senderName: "Marcus Vance",
        content: "Hi Sarah, Marcus here from the escalations team. Looking at your webhook telemetry now — we're receiving requests with a signature timestamp mismatch from your secondary replica. Let's get on a huddle if needed.",
        timestamp: "2026-11-23T09:22:00Z",
      },
    ],
  },
  {
    id: "tkt_002",
    ticketNumber: "SP-4891",
    subject: "Inquiry regarding SOC2 Type II report and GDPR DPA addendum",
    description: "Our legal procurement team requires your latest SOC2 Type II compliance audit report and signed Data Processing Agreement (DPA) before approving our annual seat expansion.",
    customerName: "David Zhao",
    customerEmail: "david.zhao@fintechcapital.com",
    status: "in_progress",
    priority: "high",
    channel: "email",
    category: "Security",
    assignedTo: {
      id: "usr_02",
      name: "Elena Rostova",
      avatar: "ER",
      role: "Compliance & Security Lead",
    },
    aiSuggestedResponse: "Hello David,\n\nThank you for reaching out. SupportPilot AI maintains continuous SOC 2 Type II certification and full GDPR/CCPA compliance. You can securely download our latest audit report directly from our Trust Center under mutual NDA, or I have attached the pre-countersigned standard DPA addendum for your legal review.",
    aiConfidenceScore: 0.98,
    aiQualityScore: 0.96,
    aiDeflected: true,
    createdAt: "2026-11-23T08:30:00Z",
    updatedAt: "2026-11-23T09:10:00Z",
    tags: ["compliance", "soc2", "gdpr", "legal"],
    messages: [
      {
        id: "m_004",
        sender: "customer",
        senderName: "David Zhao",
        content: "Our legal procurement team requires your latest SOC2 Type II compliance audit report and signed Data Processing Agreement (DPA) before approving our annual seat expansion.",
        timestamp: "2026-11-23T08:30:00Z",
      },
    ],
  },
  {
    id: "tkt_003",
    ticketNumber: "SP-4890",
    subject: "How do I configure role-based access for junior support tier?",
    description: "We are onboarding 14 new contractors who only need permission to view and respond to tickets in the 'L1 Queue'. They should not be able to delete knowledge base docs or export customer CSVs.",
    customerName: "Priya Patel",
    customerEmail: "p.patel@globalretail.de",
    status: "pending_review",
    priority: "medium",
    channel: "portal",
    category: "Account",
    assignedTo: {
      id: "usr_03",
      name: "Alex Turner",
      avatar: "AT",
      role: "Customer Success Architect",
    },
    aiSuggestedResponse: "Hi Priya,\n\nYou can configure this seamlessly using our Role-Based Access Control (RBAC):\n1. Navigate to Organization Settings > Team Members\n2. When inviting contractors, assign them the 'Agent' or 'Viewer' role.\n3. In Settings > Queue Routing, restrict L2/L3 queue visibility.\n'Agent' roles cannot delete knowledge base assets or trigger data exports by default.",
    aiConfidenceScore: 0.96,
    aiQualityScore: 0.95,
    aiDeflected: true,
    createdAt: "2026-11-23T07:45:00Z",
    updatedAt: "2026-11-23T08:12:00Z",
    tags: ["rbac", "permissions", "onboarding"],
    messages: [
      {
        id: "m_005",
        sender: "customer",
        senderName: "Priya Patel",
        content: "We are onboarding 14 new contractors who only need permission to view and respond to tickets in the 'L1 Queue'. They should not be able to delete knowledge base docs or export customer CSVs.",
        timestamp: "2026-11-23T07:45:00Z",
      },
    ],
  },
  {
    id: "tkt_004",
    ticketNumber: "SP-4889",
    subject: "Refund request for accidental duplicate billing on annual invoice #INV-8821",
    description: "Our corporate card was charged twice on November 21st for invoice #INV-8821 ($2,400 x 2 = $4,800). Please process a credit back to the card ending in 4419.",
    customerName: "Michael Chang",
    customerEmail: "m.chang@apexventures.org",
    status: "resolved",
    priority: "high",
    channel: "email",
    category: "Billing",
    assignedTo: {
      id: "usr_04",
      name: "Hannah Abbott",
      avatar: "HA",
      role: "Billing Support Specialist",
    },
    aiSuggestedResponse: "Hi Michael,\n\nI apologize for the duplicate charge. I have verified your account billing records, and refund ID `ref_992144` for $2,400.00 has been initiated back to card ending in 4419. It should reflect on your statement within 3-5 business days.",
    aiConfidenceScore: 0.99,
    aiQualityScore: 0.98,
    aiDeflected: false,
    createdAt: "2026-11-22T16:20:00Z",
    updatedAt: "2026-11-23T06:15:00Z",
    tags: ["billing", "refund", "invoice", "duplicate-charge"],
    messages: [
      {
        id: "m_006",
        sender: "customer",
        senderName: "Michael Chang",
        content: "Our corporate card was charged twice on November 21st for invoice #INV-8821 ($2,400 x 2 = $4,800). Please process a credit back to the card ending in 4419.",
        timestamp: "2026-11-22T16:20:00Z",
      },
      {
        id: "m_007",
        sender: "agent",
        senderName: "Hannah Abbott",
        content: "Hi Michael, refund has been processed successfully. Credit reference #CR-8821 has been sent to your billing address.",
        timestamp: "2026-11-23T06:15:00Z",
      },
    ],
  },
  {
    id: "tkt_005",
    ticketNumber: "SP-4888",
    subject: "Feature request: native bi-directional integration with Linear & Jira",
    description: "Our engineering squad uses Linear while support operates in SupportPilot. We need an automated way to push escalated tickets as Linear issues and sync comments back.",
    customerName: "Liam O'Connor",
    customerEmail: "liam@nextstack.dev",
    status: "open",
    priority: "low",
    channel: "chat",
    category: "Feature Request",
    aiSuggestedResponse: "Hi Liam,\n\nGreat news! SupportPilot AI features an automated webhook integration with n8n and Zapier that currently supports bi-directional Linear & Jira sync. In addition, our native Linear 2-way sync app is slated for our Q1 roadmap. Would you like access to our early beta preview?",
    aiConfidenceScore: 0.92,
    aiQualityScore: 0.90,
    aiDeflected: true,
    createdAt: "2026-11-23T06:00:00Z",
    updatedAt: "2026-11-23T06:05:00Z",
    tags: ["integrations", "linear", "jira", "roadmap"],
    messages: [
      {
        id: "m_008",
        sender: "customer",
        senderName: "Liam O'Connor",
        content: "Our engineering squad uses Linear while support operates in SupportPilot. We need an automated way to push escalated tickets as Linear issues and sync comments back.",
        timestamp: "2026-11-23T06:00:00Z",
      },
    ],
  },
  {
    id: "tkt_006",
    ticketNumber: "SP-4887",
    subject: "SSO SAML 2.0 configuration returning 'Invalid Audience URI' with Okta",
    description: "We are configuring Okta Single Sign-On. When users click the tile in Okta, SupportPilot throws 'AudienceRestriction error'. We configured the Entity ID to https://auth.supportpilot.io/saml.",
    customerName: "Evelyn Reed",
    customerEmail: "evelyn@aerospace-dyn.com",
    status: "in_progress",
    priority: "high",
    channel: "email",
    category: "Technical",
    assignedTo: {
      id: "usr_01",
      name: "Marcus Vance",
      avatar: "MV",
      role: "Senior Escalations Engineer",
    },
    aiSuggestedResponse: "Hi Evelyn,\n\nThe Entity ID for organization-specific Okta SAML is unique to your tenant slug: `https://auth.supportpilot.io/saml/org_{your_slug}`. Updating the Audience URI in your Okta application settings will resolve the mismatch immediately.",
    aiConfidenceScore: 0.95,
    aiQualityScore: 0.93,
    aiDeflected: false,
    createdAt: "2026-11-22T21:10:00Z",
    updatedAt: "2026-11-23T05:30:00Z",
    tags: ["sso", "okta", "saml", "authentication"],
    messages: [
      {
        id: "m_009",
        sender: "customer",
        senderName: "Evelyn Reed",
        content: "We are configuring Okta Single Sign-On. When users click the tile in Okta, SupportPilot throws 'AudienceRestriction error'. We configured the Entity ID to https://auth.supportpilot.io/saml.",
        timestamp: "2026-11-22T21:10:00Z",
      },
    ],
  },
];

export const MOCK_AGENT_ACTIVITIES: AgentActivity[] = [
  {
    id: "act_101",
    agentName: "Classifier Agent",
    action: "Categorized and prioritized incoming payload",
    ticketId: "SP-4892",
    ticketSubject: "Stripe webhook failing with 401 Unauthorized",
    status: "completed",
    latencyMs: 342,
    tokensUsed: 418,
    confidence: 0.96,
    timestamp: "2 minutes ago",
    details: "Detected keywords 'Stripe 401', 'renewals blocked'. Mapped to Technical / Urgent with high confidence.",
  },
  {
    id: "act_102",
    agentName: "Retriever Agent",
    action: "Semantic RAG query across ChromaDB collections",
    ticketId: "SP-4892",
    ticketSubject: "Stripe webhook failing with 401 Unauthorized",
    status: "completed",
    latencyMs: 184,
    tokensUsed: 120,
    confidence: 0.94,
    timestamp: "2 minutes ago",
    details: "Retrieved 3 chunks from 'Stripe Integration & Key Rotation Runbook.pdf' (cosine similarity: 0.89).",
  },
  {
    id: "act_103",
    agentName: "Generator Agent",
    action: "Drafted empathetic resolution proposal",
    ticketId: "SP-4892",
    ticketSubject: "Stripe webhook failing with 401 Unauthorized",
    status: "completed",
    latencyMs: 820,
    tokensUsed: 940,
    confidence: 0.91,
    timestamp: "1 minute ago",
    details: "Generated response with step-by-step instructions for updating webhook secret in Stripe dashboard.",
  },
  {
    id: "act_104",
    agentName: "Evaluator Agent",
    action: "Automated response quality & safety verification",
    ticketId: "SP-4892",
    ticketSubject: "Stripe webhook failing with 401 Unauthorized",
    status: "completed",
    latencyMs: 290,
    tokensUsed: 380,
    confidence: 0.95,
    timestamp: "1 minute ago",
    details: "Quality gate passed: Accuracy 0.94, Empathy 0.92, Completeness 0.95. Marked is_safe_to_send: True.",
  },
  {
    id: "act_105",
    agentName: "Classifier Agent",
    action: "Categorized incoming legal query",
    ticketId: "SP-4891",
    ticketSubject: "Inquiry regarding SOC2 Type II report",
    status: "completed",
    latencyMs: 310,
    tokensUsed: 390,
    confidence: 0.98,
    timestamp: "25 minutes ago",
    details: "Detected compliance audit requirement. Assigned to Security & Compliance queue.",
  },
  {
    id: "act_106",
    agentName: "Generator Agent",
    action: "Synthesized multi-document DPA summary",
    ticketId: "SP-4891",
    ticketSubject: "Inquiry regarding SOC2 Type II report",
    status: "completed",
    latencyMs: 760,
    tokensUsed: 890,
    confidence: 0.97,
    timestamp: "24 minutes ago",
    details: "Injected Trust Center link and legal contact points into generated answer.",
  },
];

export const MOCK_DASHBOARD_STATS = {
  totalTickets: 1284,
  openTickets: 42,
  inProgressTickets: 18,
  resolvedTickets: 1198,
  escalatedTickets: 6,
  avgFirstResponseTimeMin: 4.2,
  avgResolutionTimeHours: 1.8,
  aiDeflectionRate: 74.2,
  csatScore: 4.86,
  weeklyTicketTrends: [
    { day: "Mon", received: 142, resolved: 138, aiDeflected: 104 },
    { day: "Tue", received: 168, resolved: 160, aiDeflected: 122 },
    { day: "Wed", received: 185, resolved: 180, aiDeflected: 136 },
    { day: "Thu", received: 210, resolved: 202, aiDeflected: 154 },
    { day: "Fri", received: 195, resolved: 190, aiDeflected: 148 },
    { day: "Sat", received: 84, resolved: 82, aiDeflected: 68 },
    { day: "Sun", received: 72, resolved: 70, aiDeflected: 58 },
  ],
  categoryBreakdown: [
    { name: "Technical", value: 480, percentage: 37 },
    { name: "Billing", value: 320, percentage: 25 },
    { name: "Account", value: 240, percentage: 19 },
    { name: "Security", value: 140, percentage: 11 },
    { name: "Feature Req", value: 104, percentage: 8 },
  ],
  channelDistribution: [
    { channel: "Portal", count: 580, share: "45%" },
    { channel: "Email", count: 420, share: "33%" },
    { channel: "Live Chat", count: 210, share: "16%" },
    { channel: "API/Webhook", count: 74, share: "6%" },
  ],
};

export const MOCK_TEAM_MEMBERS = [
  { id: "usr_01", name: "Alex Turner", email: "alex.turner@supportpilot.io", role: "Owner", status: "online", activeTickets: 3 },
  { id: "usr_02", name: "Marcus Vance", email: "m.vance@supportpilot.io", role: "Admin", status: "online", activeTickets: 7 },
  { id: "usr_03", name: "Elena Rostova", email: "elena.r@supportpilot.io", role: "Agent", status: "busy", activeTickets: 4 },
  { id: "usr_04", name: "Hannah Abbott", email: "hannah.a@supportpilot.io", role: "Agent", status: "online", activeTickets: 2 },
  { id: "usr_05", name: "David Kim", email: "d.kim@supportpilot.io", role: "Viewer", status: "offline", activeTickets: 0 },
];

export const MOCK_KNOWLEDGE_DOCS = [
  { id: "doc_01", title: "API Authentication & Token Lifecycle", fileName: "api-auth-lifecycle.md", type: "MD", size: "48 KB", chunks: 14, status: "indexed", updatedAt: "2026-11-22" },
  { id: "doc_02", title: "Enterprise Billing & Refund Policy", fileName: "billing-refunds-2026.pdf", type: "PDF", size: "380 KB", chunks: 42, status: "indexed", updatedAt: "2026-11-20" },
  { id: "doc_03", title: "Okta & Azure AD SAML Configuration Runbook", fileName: "saml-sso-guide.docx", type: "DOCX", size: "1.2 MB", chunks: 68, status: "indexed", updatedAt: "2026-11-19" },
  { id: "doc_04", title: "Webhook Retry Logic & Idempotency Keys", fileName: "webhooks-spec.md", type: "MD", size: "32 KB", chunks: 9, status: "indexed", updatedAt: "2026-11-18" },
  { id: "doc_05", title: "SOC2 Compliance Controls & Data Retention", fileName: "soc2-controls-summary.pdf", type: "PDF", size: "640 KB", chunks: 56, status: "indexed", updatedAt: "2026-11-15" },
];
