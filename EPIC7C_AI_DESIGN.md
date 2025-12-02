# EPIC 7C - AI Co-Pilot Design Document

**Version:** 1.0  
**Date:** 2025-11-30  
**Status:** Approved

---

## 1. Overview

The AI Co-Pilot is an LLM-powered assistant integrated into the GTI-OS Control Tower UI. Its purpose is to help users understand trade data, buyer profiles, and risk signals through natural language explanations.

### Core Principle: Accuracy First

The AI Co-Pilot follows a **strict accuracy-first design**:
- All facts MUST come from the GTI-OS API/database
- The LLM is NEVER allowed to invent data
- The LLM can only summarize, explain, and provide insights on provided data

---

## 2. What AI IS Allowed To Do

### 2.1 Explain Structured Data
- Summarize a buyer's trade history in plain language
- Explain what HS codes mean and their significance
- Describe risk signals and their business implications
- Interpret price patterns and volume trends

### 2.2 Generate Narratives
- Create business-friendly summaries of buyer profiles
- Write due diligence briefings based on available data
- Generate sales pitch suggestions using actual buyer data

### 2.3 Rank and Prioritize
- Suggest which buyers to focus on based on volume/risk
- Highlight key patterns in the provided data
- Prioritize action items using existing metrics

### 2.4 Answer Questions
- Answer user questions about displayed data
- Explain trade terminology and concepts
- Provide context for metrics and indicators

---

## 3. What AI is NOT Allowed To Do

### 3.1 Invent Data (Strictly Forbidden)
- ❌ Create fake HS codes
- ❌ Invent price numbers
- ❌ Make up country names or trade routes
- ❌ Fabricate buyer names or UUIDs
- ❌ Generate statistics not in the context

### 3.2 Query Database Directly
- ❌ Execute SQL queries
- ❌ Access database connections
- ❌ Bypass the API layer

### 3.3 Modify Data
- ❌ Update any records
- ❌ Delete any data
- ❌ Create new entries
- ❌ Trigger write operations

### 3.4 Access External Data
- ❌ Make web searches
- ❌ Access external APIs
- ❌ Use training data as facts

---

## 4. Prompting Strategy

### 4.1 System Prompt (Always Included)

```
You are a trade intelligence analyst assistant for GTI-OS Control Tower.

CRITICAL RULES:
1. ALL facts, numbers, HS codes, countries, values, and volumes MUST come 
   ONLY from the JSON context provided.
2. NEVER invent or hallucinate any data. If information is not in the 
   context, say "Not available in data."
3. You may summarize, explain, and provide insights based ONLY on the 
   provided data.
4. Format responses clearly with bullet points and sections when appropriate.
5. Be concise and business-focused.

Your role is to help users understand trade data, buyer profiles, and risk 
signals using ONLY the structured data provided.
```

### 4.2 Context Injection Pattern

All LLM calls MUST include structured JSON context:

```json
{
  "buyer": {
    "buyer_uuid": "abc-123...",
    "buyer_name": "ACME IMPORTS",
    "buyer_country": "KENYA",
    "total_shipments": 150,
    "total_value_usd": 2500000,
    "top_hs_codes": [
      {"hs_code_6": "690721", "value_usd": 1500000, "share_pct": 60}
    ],
    "top_origin_countries": [
      {"country": "INDIA", "value_usd": 2000000, "share_pct": 80}
    ]
  },
  "risk": {
    "risk_level": "HIGH",
    "risk_score": 78.5,
    "main_reason_code": "GHOST_ENTITY",
    "reasons": {...}
  }
}
```

### 4.3 User Prompt Templates

**Buyer Explanation:**
```
Explain this buyer to a manufacturer looking for potential business partners.
Focus on:
1. Company overview (size, location, activity period)
2. Product focus (top HS codes and what they trade)
3. Volume and value patterns
4. Main trade routes/lanes
5. Risk assessment and any concerns
6. Business opportunity summary

Use ONLY the data provided. Do not invent any numbers or facts.
```

**Risk Analysis:**
```
Analyze the risk profile for this entity.
Explain:
1. Overall risk level and score interpretation
2. Main risk factors (reason codes)
3. What the risk signals mean for business
4. Recommended due diligence steps

Use ONLY the data provided.
```

**Free-form Question:**
```
Answer this question using ONLY the provided data context:

Question: {user_question}

If the answer is not available in the data, say "This information is not 
available in the current data."
Never invent or estimate numbers.
```

---

## 5. Architecture

### 5.1 Data Flow

```
┌─────────────────┐
│   Control Tower │
│   Web UI        │
└────────┬────────┘
         │ User clicks "Explain Buyer"
         ▼
┌─────────────────┐
│ /api/v1/ai/     │
│ explain-buyer   │
└────────┬────────┘
         │ 1. Fetch structured data from DB/views
         ▼
┌─────────────────┐
│ vw_buyer_360    │ ◄── Buyer data
│ risk_scores     │ ◄── Risk data  
│ vw_buyer_hs_    │ ◄── HS activity
│ activity        │
└────────┬────────┘
         │ 2. Build JSON context
         ▼
┌─────────────────┐
│ LLM Client      │
│ (Ollama/OpenAI) │
└────────┬────────┘
         │ 3. Generate explanation
         ▼
┌─────────────────┐
│ JSON Response   │
│ {explanation:...}│
└─────────────────┘
```

### 5.2 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| Web UI | Display data, capture user questions |
| AI Endpoint | Fetch data, build context, call LLM |
| LLM Client | Abstract LLM provider, enforce prompts |
| LLM (Ollama/etc) | Generate text from context |

### 5.3 Security Boundaries

```
┌──────────────────────────────────────────────┐
│ TRUSTED ZONE (Backend)                       │
│                                              │
│  ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │ Database │───▶│ API      │───▶│ LLM    │ │
│  │ (source  │    │ Endpoint │    │ Client │ │
│  │ of truth)│    │          │    │        │ │
│  └──────────┘    └──────────┘    └────────┘ │
│                        │                     │
└────────────────────────┼─────────────────────┘
                         │ JSON only
                         ▼
┌──────────────────────────────────────────────┐
│ UNTRUSTED ZONE (Frontend)                    │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ Web UI - displays only what API sends │   │
│  └──────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

---

## 6. LLM Provider Selection

### 6.1 Current Machine Status

**Detected on this machine (2025-11-30):**

| Property | Value |
|----------|-------|
| **Provider** | Ollama (local) |
| **Model** | llama3:latest |
| **Endpoint** | http://localhost:11434 |
| **Status** | ✅ Available |
| **Also Available** | mistral:latest |

### 6.2 Detection Priority

| Priority | Provider | Condition |
|----------|----------|-----------|
| 1 | Ollama + llama3 | Preferred for local, good reasoning |
| 2 | Ollama + mistral | Fallback local |
| 3 | OpenAI | OPENAI_API_KEY set |
| 4 | Anthropic | ANTHROPIC_API_KEY set |
| 5 | Groq | GROQ_API_KEY set |

### 6.3 Model Selection

Within each provider, prefer larger/better models:

**Ollama (preferred for local):** llama3:70b > llama3:latest > qwen2:72b > mixtral > mistral

**OpenAI:** gpt-4o > gpt-4-turbo > gpt-4 > gpt-3.5-turbo

### 6.3 Graceful Degradation

If no LLM is available:
- AI features display "AI Co-Pilot unavailable"
- All data features continue to work normally
- No errors thrown, just disabled state

---

## 7. Validation Rules

### 7.1 Pre-Generation Checks
- [ ] Context JSON is not empty
- [ ] Required fields present (buyer_uuid, etc.)
- [ ] Context size within limits (< 16K tokens)

### 7.2 Post-Generation Checks
- [ ] Response is not empty
- [ ] Response is proper text (not error message)
- [ ] Log context and response for audit

### 7.3 Accuracy Spot-Checks
During QA, verify:
- [ ] No HS codes in response that aren't in context
- [ ] No countries mentioned that aren't in context
- [ ] No prices/values invented
- [ ] Numbers match context exactly

---

## 8. Example Interactions

### Example 1: Buyer Explanation

**Context Provided:**
```json
{
  "buyer": {
    "buyer_name": "SUNRISE TRADERS",
    "buyer_country": "KENYA",
    "total_shipments": 186,
    "total_value_usd": 19347201,
    "top_hs_codes": [
      {"hs_code_6": "100630", "value_usd": 15000000, "share_pct": 77.5}
    ]
  },
  "risk": {
    "risk_level": "UNSCORED"
  }
}
```

**AI Response:**
```
## SUNRISE TRADERS - Buyer Profile

### Company Overview
- **Location:** Kenya
- **Trade Activity:** 186 recorded shipments
- **Total Trade Value:** $19.3 million USD

### Product Focus
Primary focus on HS 100630 (Rice), representing 77.5% of their 
import value ($15M). This indicates a specialized bulk commodity 
importer.

### Risk Assessment
Currently UNSCORED - no risk flags detected. Standard due 
diligence recommended for new relationships.

### Business Opportunity
Strong volume buyer with clear product focus. Suitable for rice 
exporters seeking established East African distribution partners.
```

### Example 2: Missing Data Handling

**User Question:** "What is their average order size?"

**AI Response:**
```
The average order size is not directly available in the current 
data. However, based on the available figures:
- Total shipments: 186
- Total value: $19.3M USD
- Calculated average: approximately $104,000 per shipment

Note: This is a calculated estimate, not a recorded metric.
```

---

## 9. Error Handling

### 9.1 LLM Unavailable
```json
{
  "error": "AI Co-Pilot unavailable",
  "detail": "No LLM provider configured",
  "fallback": "Data is still available in the UI"
}
```

### 9.2 LLM Timeout
```json
{
  "error": "AI request timed out",
  "detail": "Please try again",
  "context_available": true
}
```

### 9.3 Context Too Large
```json
{
  "error": "Context too large for AI processing",
  "detail": "Reduce data selection and try again"
}
```

---

## 10. Monitoring & Audit

### 10.1 Logged Information
- Timestamp of AI request
- User/session identifier
- Context size (tokens)
- LLM provider used
- Response time
- Success/failure status

### 10.2 Not Logged (Privacy)
- Full context JSON (too large)
- API keys
- User PII

---

## Approval

This design ensures maximum accuracy by:
1. Strict system prompts forbidding hallucination
2. Structured JSON context injection
3. No direct database access from LLM
4. Clear boundaries between trusted and untrusted zones

AI-generated content is always based on verified GTI-OS data.
