# EPIC 7C - Control Tower Web UI + AI Co-Pilot Implementation Summary

**Date:** 2025-11-30  
**Platform:** GTI-OS Data Platform v1.0  
**Status:** ✅ COMPLETE

---

## 1. Overview

EPIC 7C delivers a production-grade **Control Tower Web UI** with an integrated **AI Co-Pilot** that uses LLM technology to help users understand trade data, buyer profiles, and risk signals.

### Key Principles

- ✅ **Accuracy First**: All numeric data comes from GTI-OS API, never hallucinated
- ✅ **Read-Only**: UI only reads data, no mutations allowed
- ✅ **Scalable**: Pagination, debounced search, optimized for 100M+ rows
- ✅ **LLM Abstraction**: Works with OpenAI, Anthropic, Groq, or local Ollama

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Control Tower UI                             │
│                 (React + TypeScript + Vite)                      │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│   │Dashboard│  │ Buyers  │  │   HS    │  │  Risk   │           │
│   │  Page   │  │  List   │  │Dashboard│  │Overview │           │
│   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
│        │            │            │            │                  │
│        └────────────┴────────────┴────────────┘                  │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │ HTTP (localhost:3000 → :8000)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                               │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    /api/v1/*                             │   │
│   │  /health  /buyers  /hs-dashboard  /risk  /ai/explain    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│   ┌──────────────────────┴──────────────────────────────────┐   │
│   │                  LLM Client                              │   │
│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │   │
│   │  │ OpenAI  │  │Anthropic│  │  Groq   │  │ Ollama  │    │   │
│   │  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL                                    │
│   vw_buyer_360  │  vw_country_hs_dashboard  │  risk_scores      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. LLM Detection & Selection

### 3.1 Detection Priority

| Priority | Provider | Detection Method |
|----------|----------|------------------|
| 1 | OpenAI | `OPENAI_API_KEY` env var |
| 2 | Anthropic | `ANTHROPIC_API_KEY` env var |
| 3 | Groq | `GROQ_API_KEY` env var |
| 4 | Ollama | `ollama list` command |
| 5 | Docker LLM | `docker ps` for known containers |

### 3.2 Current Detection Result

```json
{
  "best_provider": "ollama",
  "best_model": "llama3:latest",
  "providers": {
    "ollama": {"available": true, "models": ["llama3:latest", "mistral:latest"]},
    "openai": {"available": false},
    "anthropic": {"available": false},
    "groq": {"available": false}
  }
}
```

### 3.3 To Change LLM Provider

**Use OpenAI:**
```bash
set OPENAI_API_KEY=sk-your-key-here
python scripts/run_api.py
```

**Use Groq (free, fast):**
```bash
set GROQ_API_KEY=gsk-your-key-here
python scripts/run_api.py
```

**Use local Ollama:**
```bash
ollama pull llama3
ollama serve
python scripts/run_api.py
```

---

## 4. Web UI Pages

### 4.1 Dashboard (`/`)

- **Stats cards**: Total shipments, buyers, countries, HS codes
- **Top 5 HS codes chart**: Bar chart by value
- **Risk distribution**: Color-coded grid for shipment/buyer risks
- **Pipeline status**: Last run status for each pipeline

### 4.2 Buyer List (`/buyers`)

- **Filterable table**: Country, risk level, HS code filters
- **Debounced search**: 400ms delay for HS code filter
- **Pagination**: 20 items per page
- **Click to navigate**: Row click opens Buyer 360

### 4.3 Buyer 360 (`/buyers/:uuid`)

- **Header**: Buyer name, country, risk badge
- **Stats grid**: Value, shipments, weight, active years
- **Top HS codes**: Ranked list with value and share %
- **Top origins**: Ranked list of origin countries
- **Risk assessment**: Score, confidence, reason codes
- **AI Co-Pilot**: 
  - Quick explain buttons (Sales, Risk, General)
  - Custom question input
  - AI-generated explanations

### 4.4 HS Dashboard (`/hs-dashboard`)

- **Quick select**: Click top HS codes to analyze
- **Filters**: Country, direction
- **Stats**: Value, shipments, buyers, risk %
- **Monthly trend chart**: Line chart of value over time
- **Monthly breakdown table**: Detailed monthly data

### 4.5 Risk Overview (`/risk`)

- **Summary cards**: Risk counts by level (LOW→CRITICAL)
- **Tabbed view**: Shipments vs Buyers
- **Risk level filter**: Filter by severity
- **Sortable tables**: With pagination

---

## 5. AI Co-Pilot

### 5.1 Accuracy Guarantees

The AI Co-Pilot is designed for **maximum accuracy**:

1. **Context injection**: All buyer data is passed as JSON to LLM
2. **System prompt**: Explicitly forbids hallucination
3. **No direct DB access**: LLM only sees pre-fetched data
4. **Traceable**: Provider and model logged with each response

### 5.2 System Prompt

```
You are a trade intelligence analyst assistant for GTI-OS Control Tower.

CRITICAL RULES:
1. ALL facts, numbers, HS codes, countries, values, and volumes MUST come 
   ONLY from the JSON context provided.
2. NEVER invent or hallucinate any data. If information is not in the 
   context, say "Not available in data."
3. You may summarize, explain, and provide insights based ONLY on the 
   provided data.
```

### 5.3 Use Cases

| Use Case | Description |
|----------|-------------|
| `sales` | Business pitch for manufacturers |
| `risk` | Due diligence analysis |
| `general` | General overview |
| Custom | User's own question |

---

## 6. API Endpoints (New in EPIC 7C)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ai/status` | GET | AI availability status |
| `/api/v1/ai/explain-buyer/{uuid}` | POST | Generate buyer explanation |
| `/api/v1/ai/ask-buyer/{uuid}` | POST | Answer custom question |
| `/api/v1/ai/capabilities` | GET | Detected LLM providers |

---

## 7. File Structure

### Backend (New Files)

```
api/
├── llm/
│   ├── __init__.py       # Module exports
│   ├── detector.py       # LLM detection logic
│   └── client.py         # Unified LLM client
└── routers/
    └── ai.py             # AI endpoints
```

### Frontend

```
control-tower-ui/
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── index.html
└── src/
    ├── main.tsx          # App entry
    ├── App.tsx           # Router & layout
    ├── index.css         # Tailwind imports
    ├── api/
    │   └── client.ts     # API client & types
    └── pages/
        ├── Dashboard.tsx
        ├── BuyerList.tsx
        ├── Buyer360Page.tsx
        ├── HsDashboard.tsx
        └── RiskOverview.tsx
```

---

## 8. How to Run

### Start Backend API

```bash
cd "E:\Port Data Brain"
python scripts/run_api.py
# API running at http://localhost:8000
```

### Start Frontend Dev Server

```bash
cd "E:\Port Data Brain\control-tower-ui"
npm run dev
# UI running at http://localhost:3000
```

### Production Build

```bash
cd control-tower-ui
npm run build
# Output in dist/ folder
```

---

## 9. Tech Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2 | UI framework |
| TypeScript | 5.2 | Type safety |
| Vite | 5.0 | Build tool |
| TailwindCSS | 3.3 | Styling |
| TanStack Query | 5.8 | Data fetching |
| React Router | 6.20 | Routing |
| Recharts | 2.10 | Charts |
| Lucide React | 0.294 | Icons |

### Backend

| Technology | Purpose |
|------------|---------|
| FastAPI | API framework |
| Pydantic | Data validation |
| httpx | HTTP client for LLM calls |
| psycopg2 | PostgreSQL driver |

---

## 10. Testing

### Backend Tests

```bash
python tests/test_api_smoke.py
```

**Results:**
- ✅ Health check OK
- ✅ AI status returns correctly
- ✅ All data endpoints work
- ✅ SQL injection protected

### Frontend Build

```bash
npm run build
# ✓ 2212 modules transformed
# ✓ Built in 3.71s
```

### Manual QA Checklist

- [x] Dashboard loads with stats
- [x] Buyer list paginates correctly
- [x] Buyer 360 shows full profile
- [x] HS Dashboard shows trends
- [x] Risk overview displays correctly
- [x] AI explain returns plausible text
- [x] No hallucinated data in AI responses

---

## 11. Known Limitations

1. **AI Response Time**: Ollama (local) is slower than cloud APIs
2. **Bundle Size**: 638KB (could use code splitting)
3. **No Auth**: UI is open (add authentication for production)
4. **No Real-time**: Data updates require page refresh

---

## 12. Future Improvements

1. **Authentication**: Add JWT or API key auth
2. **Real-time Updates**: WebSocket for live data
3. **Export Features**: CSV/PDF export for reports
4. **More AI Features**: Comparative analysis, anomaly detection
5. **Dark Mode**: User preference support

---

## Conclusion

EPIC 7C successfully delivers:

- ✅ **Production-grade React UI** with 5 main pages
- ✅ **AI Co-Pilot** with accuracy-first design
- ✅ **LLM Detection** selecting best available provider (Ollama detected)
- ✅ **Graceful Degradation** when AI unavailable
- ✅ **Read-only** access to GTI-OS data
- ✅ **Pagination & Debouncing** for scale
- ✅ **Full Documentation** for setup and usage

The Control Tower is ready for use with the existing backend API.
