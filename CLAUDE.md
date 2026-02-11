# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is PatchUp

A voice-first relationship conversation simulator where users practice convincing an angry AI girlfriend to forgive them. Uses the full Sarvam AI stack: Bulbul V3 (TTS), Saarika v2.5 (STT), Sarvam-M (LLM), and Mayura v1 (Translate). Built for the #TheMicIsYours Sarvam AI challenge.

## Development Commands

### Backend (FastAPI + Python)
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add SARVAM_API_KEY; SUPABASE_* keys optional
uvicorn main:app --reload --port 8000
```

### Frontend (Next.js 16 + React 18 + Tailwind)
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev          # Dev server at localhost:3000
npm run build        # Production build
```

### Database (optional)
App works with in-memory storage when Supabase is not configured. To use Supabase, run `supabase/migration.sql` in the SQL Editor and set `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` in `backend/.env`.

## Architecture

### Monolith backend
Everything lives in `backend/main.py` — a single FastAPI file containing:
- Sarvam API helpers (`sarvam_stt`, `sarvam_tts`, `sarvam_llm`)
- Supabase/in-memory DB helpers (`db_create_session`, `db_get_session`, `db_update_session`)
- Game data definitions (`PERSONAS`, `SCENARIOS`, `DIFFICULTY_CONFIG`, `EMOTION_VOICE_PARAMS`)
- LLM system prompt builder (`build_system_prompt`)
- Core conversation loop (`process_user_message`) shared by voice and text endpoints
- All API endpoints under `/api/`

### Core conversation flow
1. `POST /api/session/start` — creates session, generates opening TTS audio
2. `POST /api/session/{id}/respond` — voice input: audio → STT → LLM (JSON) → TTS → response
3. `POST /api/session/{id}/respond-text` — text fallback: text → LLM (JSON) → TTS → response
4. `POST /api/session/{id}/end` — ends session, generates AI tips, records stats

Both voice and text endpoints funnel through `process_user_message()` which handles the LLM call, score update, TTS generation, and DB persistence.

### LLM response format
The LLM is prompted to return JSON with: `response`, `score_delta` (-25 to +25), `emotion`, `should_end`, `end_reason`. The `parse_llm_json()` function handles markdown fences and malformed JSON with a fallback.

### TTS voice parameters
Bulbul V3 pace/temperature are computed as the average of the difficulty base params and the emotion-specific params from `EMOTION_VOICE_PARAMS`.

### Frontend routing (Next.js App Router)
- `/` — Landing page
- `/setup` — Persona → scenario → difficulty → language picker
- `/chat?id=...` — Voice conversation UI (ChatContent.tsx is the core component)
- `/result?id=...` — Score verdict, tips, share CTA

### Frontend API layer
`frontend/src/lib/api.ts` is the API client. It uses `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`). Audio is transferred as base64 strings; `playBase64Audio()` handles decoding and playback.

### Key components
- `ChatContent.tsx` — core voice conversation UI with mic recording, chat bubbles, and score updates
- `PatchMeter.tsx` — heart-fill progress bar showing patch-up score
- `MicButton.tsx` — recording button with animations
- `useAudioRecorder.ts` — browser MediaRecorder hook

### Storage pattern
Supabase is optional. The backend checks if `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set; if not, it falls back to an in-memory `dict`. All DB operations go through `db_*` helper functions that handle both paths.

## Environment Variables

### Backend (`backend/.env`)
- `SARVAM_API_KEY` — required, from dashboard.sarvam.ai
- `SUPABASE_URL` — optional, pre-filled in .env.example
- `SUPABASE_SERVICE_KEY` — optional, leave blank for in-memory mode

### Frontend (`frontend/.env.local`)
- `NEXT_PUBLIC_API_URL` — defaults to `http://localhost:8000`
