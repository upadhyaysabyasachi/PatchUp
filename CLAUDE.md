# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is PatchUp

A voice-first simulator for rehearsing difficult conversations before they happen: asking for a raise, giving hard feedback, telling your father you're quitting, a breakup, a layoff, confronting a co-founder, or bring-your-own. An **actor** LLM plays the counterpart (with hidden motivations and curveballs) while every user turn is **judged**: how it moves the counterpart, and how it scores on a rubric. The original "convince your angry girlfriend" game survives as the *Classic* mode. Uses the full Sarvam AI stack: Bulbul V3 (TTS), Saarika v2.5 (STT), Sarvam 105b (actor, coach note, scenario builder, debrief), Mayura v1 (translates the counterpart's opening line into the session language, and native-script user turns for the judge). Judgement is **TypeSafe Jev** (typed Score/Noul/Choice answers, no generated text) when `TYPESAFE_API_KEY` is set; otherwise the Sarvam 105b actor self-reports movement and the coach self-scores. Built for the #TheMicIsYours Sarvam AI challenge.

## Development Commands

### Backend (FastAPI + Python)
```bash
cd backend
uv venv venv && uv pip install --python venv/bin/python -r requirements.txt   # or: python -m venv venv && pip install -r requirements.txt
cp .env.example .env  # Add SARVAM_API_KEY; SUPABASE_* optional; ALLOWED_ORIGINS for prod
./venv/bin/uvicorn main:app --reload --port 8000
./venv/bin/python -m unittest discover -s . -v   # offline tests, no network or DB
```

### Frontend (Next.js 16 + React 18 + Tailwind)
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev          # Dev server at localhost:3000
npm run build        # Production build (also the type check)
```

### Database (optional)
App works with in-memory storage when Supabase is not configured. Fresh project: run `supabase/migration.sql` in the SQL Editor. Existing project: run `supabase/migrations/*.sql` in order. Set `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` in `backend/.env`. The rehearsal columns need `002_rehearsal_scenarios.sql`; without it inserts fail and sessions silently live in memory for 60s at a time.

## Architecture

### Backend modules (`backend/`)
- `main.py` — FastAPI app, CORS, Pydantic models, endpoints, orchestration (`process_user_message`, `start_from_brief`, `build_scenario`, `end_session_endpoint`). All network I/O is called from here, so tests patch `main.sarvam_llm` / `main.sarvam_tts` and `db.supabase`.
- `content.py` — pure data. Rehearsal `PRESETS`, classic `PERSONAS` / `SCENARIOS`, `DIFFICULTY_CONFIG` (temperaments `open|defensive|hostile` + classic `easy..nightmare`, each with a starting receptiveness and trust/defensiveness dials), `RUBRICS` (coach dimensions + actor hints per conversation type), `EMOTION_VOICE_PARAMS`, Bulbul `VOICES`, safety keywords and resources. `preset_brief()` / `classic_brief()` express both flows as one brief shape.
- `prompts.py` — actor, coach, scenario-builder and debrief prompt builders. Sarvam 105b needs the first non-system message to be from the user, so the opening line is folded into the system prompt.
- `parsing.py` — LLM-output parsers that never raise on bad output (`parse_actor` falls back, `parse_coach` / `parse_brief` return None) plus `brief_from_data` for client-supplied briefs. Only `parse_tips` raises.
- `sarvam.py` — `sarvam_stt`, `sarvam_tts`, `sarvam_translate`, and `sarvam_llm(messages, temperature, max_tokens, model, reasoning, json_mode)`. Models: `SARVAM_ACTOR_MODEL` (`sarvam-105b-conversations`, reasoning off) for the actor; `SARVAM_LLM_MODEL` (`sarvam-105b`, `reasoning="low"`) for coach, builder and debrief. `sarvam-m` no longer exists. JSON mode (`response_format: json_object`) is on for every call, so the debrief asks for `{"tips": [...]}` and `parse_tips` unwraps objects.
- `elevenlabs.py` — `elevenlabs_tts` (Eleven v3 by default; the counterpart's `emotion` becomes a v3 audio tag like `[angry]`, and `pace`/`temperature` map to `voice_settings`), `elevenlabs_stt` (Scribe v2), `pick_elevenlabs_voice(name, gender, accent)`. Voice order: env override → account voice with that accent label → Voice Library search (`/v1/shared-voices`, most-used, free-tier-allowed) added to the account via `/v1/voices/add` and cached per (gender, accent) → any account voice of the gender → premade defaults. Returns MP3. Raises on failure; `main.speak()` / `main.transcribe()` own the fallback to Sarvam.
- `typesafe.py` — TypeSafe Jev via `POST https://api.typesafe.ai/v1/systemone` (httpx, no SDK). `judge_turn()` asks 6 Score questions in one request (movement, trust, defensiveness + the rubric's 3 dimensions) and maps expected levels to deltas / 0-10 in code; `judge_intake()` asks 2 Nouls (abuse, self-harm; flagged at ≥ `SAFETY_THRESHOLD` 0.6) + 1 Choice (conversation type). `judge_enabled()` is just "is the key set". Level descriptions live in `content.py` (`RUBRICS[...]["dimensions"][dim]["levels"]`, `MOVEMENT_LEVELS`, `TRUST_LEVELS`, `DEFENSIVENESS_LEVELS`).
- `db.py` — Supabase client with in-memory fallback. Any Supabase error opens a 60s circuit breaker; sessions created meanwhile live in `memory_sessions` and are always read from there first. `normalize_session` maps legacy `boyfriend`/`girlfriend` roles and fills missing rehearsal columns.

### The brief
Every session is driven by a brief: `{kind: preset|custom|classic, conversation_type, counterpart{name, role, gender, accent, relationship, style, voice_id}, user_goal, user_fears, history, hidden_motivations[], curveballs[], opening_line}`. `accent` is an id from `content.ACCENTS` (default `indian`), chosen by the user in the intake; it drives ElevenLabs voice selection only (`voice_id` is the Sarvam fallback speaker). Presets are canned briefs (no LLM). Custom ones come from `POST /api/scenario/build` (Sarvam 105b), which also runs a keyword + LLM safety screen and returns a `safety` payload with helplines instead of a brief for self-harm/abuse. Classic sessions are converted with `classic_brief()`. The brief is stored on the session (`brief` JSONB); rows written before briefs existed are rebuilt from `persona_id`/`scenario_id` by `session_brief()`.

### One user turn: judge → actor + coach → TTS
1. **Judge** (`judge_with_jev`). With a TypeSafe key: if the message is in a native Indic script, Mayura translates it to English first (Jev is English-first); then one Jev request returns movement/trust/defensiveness deltas and the 3 rubric scores. Positive movement is scaled by the difficulty's `gain_factor` (`apply_gain`); losses land in full. Code updates `current_score` / `counterpart_state` *before* the actor speaks. Without a key, or if Jev fails, this step is skipped and the actor self-reports (`judged_by: "actor"`).
2. **Actor + coach** run concurrently (`asyncio.gather`, both Sarvam 105b). The actor gets the already-updated state when Jev judged (`build_actor_messages(..., self_judging=False)`) and returns `{response, emotion}`; when self-judging, the prompt suffix also asks for the three deltas. The coach gets Jev's scores and only writes `{note, stronger}`; when self-judging it also returns `scores`. A coach failure never fails the turn.
3. **TTS** of the actor's reply via `speak()`; pace/temperature = avg(difficulty, emotion) ± a defensiveness nudge.

### Speech providers
`TTS_PROVIDER` / `STT_PROVIDER` default to `elevenlabs` when `ELEVENLABS_API_KEY` is set, else `sarvam`. `speak()` tries ElevenLabs when it's the provider *and* `supports_language(model, language)` (v3 speaks all 9 UI languages; `eleven_multilingual_v2`/flash only `en`, `hi`, `ta`), then falls back to Sarvam Bulbul on any error. `transcribe()` does the same with Scribe → Saarika. Responses carry `audio_mime` (`audio/mpeg` from ElevenLabs, `audio/wav` from Sarvam — the frontend passes it to `playBase64Audio`) and `voice_provider` / `stt_provider`; `/api/health` reports the configured providers. Tests patch `main.elevenlabs_tts` / `main.elevenlabs_stt` / `main.pick_elevenlabs_voice` and set `main.TTS_PROVIDER`.

`current_score` is the counterpart's **receptiveness** and drives the meter and end conditions (≥90 → `patched_up`, ≤0 → `blocked`; status names kept for compatibility). Coach output is stored on the user turn as `coach` (with `judged_by`); running averages in `skill_scores`. Stats are recorded exactly once: in `process_user_message` when the score resolves the session, else in `/end` when the user quits.

### Endpoints (`/api/`)
- `GET /catalog` (presets, personas, scenarios, temperaments, difficulties, languages, rubrics), `/health`, `/leaderboard`
- `POST /scenario/build` `{preset_id?, intake?}` → `{brief | safety, built_by, judged_by}`; untouched preset intake skips the LLM. Otherwise Sarvam 105b writes the brief while Jev classifies safety + conversation type in parallel; Jev's safety verdict wins, and its conversation type is used for custom scenarios (presets keep theirs)
- `POST /session/start` `{brief, difficulty, language}` or classic `{persona_id, scenario_id, difficulty, language}`; non-classic opening lines are translated with Mayura when language ≠ `en-IN`
- `POST /session/{id}/respond` (WAV upload) · `/respond-text` (form field `text`)
- `POST /session/{id}/rewind` `{turn_number}` — truncate before that user turn, restore state from the snapshot on the preceding counterpart turn (or replay deltas for legacy rows), reopen
- `POST /session/{id}/restart` — same brief/difficulty/language, `previous_session_id` set; `/end` then returns `previous_score`
- `POST /session/{id}/end` — debrief: verdict, tips, `skill_scores`, annotated `transcript`, `reveal` (hidden motivations + curveballs), `previous_score`
- `GET /session/{id}` · `DELETE /session/{id}`

### Conversation turn shape
Counterpart turns: `{role, text, emotion, score_delta, state{receptiveness,trust,defensiveness}, timestamp}`. User turns: `{role, text, turn_number, coach|null, timestamp}`.

### Frontend (Next.js App Router)
- `/` landing · `/setup` mode picker (presets / write your own / classic) → intake or persona+scenario → temperament or difficulty → language → build + start · `/chat?id=` · `/result?id=`
- `ChatContent.tsx` — meter labelled by the rubric (`Forgiveness`, `Buy-in`, `Openness`, `Acceptance`), compact `SkillMeter`, coach notes on user bubbles, ↺ Retry (rewind). No auto-redirect at the end: the banner offers "Retry last turn" or "See debrief".
- `ResultContent.tsx` — calls `/end` on mount (the chat page no longer does), skill bars, reveal, annotated transcript, run again, delete.
- `lib/api.ts` — typed client; `getCatalog()` is the only source of presets/options (nothing is hardcoded in the setup page).
- Session metadata is passed between pages via `sessionStorage` (`patchup_session`, `patchup_result`).

## Environment Variables

### Backend (`backend/.env`)
- `SARVAM_API_KEY` — required (LLM, translation, and the speech fallback)
- `ELEVENLABS_API_KEY` — optional; set = ElevenLabs is the primary voice (TTS + STT). `TTS_PROVIDER`/`STT_PROVIDER=sarvam|elevenlabs` force one; `ELEVENLABS_TTS_MODEL` (default `eleven_v3`), `ELEVENLABS_STT_MODEL` (`scribe_v2`), `ELEVENLABS_VOICE_IDS_FEMALE/MALE`, `ELEVENLABS_BASE_URL` tune it.
- `TYPESAFE_API_KEY` — optional; set = Jev judges turns and intakes, blank = Sarvam 105b self-judges. `/api/health` reports `judge`.
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` — optional; blank = in-memory
- `ALLOWED_ORIGINS` — comma-separated; defaults to `http://localhost:3000,http://127.0.0.1:3000`. Credentials are off.

### Frontend (`frontend/.env.local`)
- `NEXT_PUBLIC_API_URL` — defaults to `http://localhost:8000`
