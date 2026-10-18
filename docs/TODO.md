# PatchUp — Roadmap & TODO

Goal: evolve PatchUp from a comedic "angry girlfriend" game into a simulator where people
**rehearse real difficult conversations before they happen** (asking for a raise, giving hard
feedback, telling parents about a career change, ending a relationship, letting someone go, etc.).

## Current state (after `feature/rehearsal-simulator`)

**Done, keep:**
- Voice pipeline — STT → actor + coach (concurrent) → TTS (`process_user_message`, `backend/main.py`)
- Emotion-driven Bulbul voice params, nudged by the counterpart's defensiveness (`EMOTION_VOICE_PARAMS`, `voice_params`)
- Every session runs off a **brief** (`content.py`): presets, LLM-built custom scenarios, and classic girlfriend sessions all share one shape
- Meter = counterpart receptiveness; coach = 3-dimension skill score per turn; both in the UI
- Rewind / run again / annotated transcript / reveal on the debrief
- Supabase with in-memory fallback and a circuit breaker; 38 offline tests

**Still open:**
- Supabase Auth and per-user history
- Latency: streaming LLM → TTS; hands-free mode; interruptions
- Data-retention policy (delete endpoint exists; no automatic expiry yet)

---

## Milestone 1 — Bring your own scenario (highest leverage)

- [x] Rename roles to `user` / `counterpart` across backend, DB and frontend
      Code reads both. `supabase/migrations/001_neutral_conversation_roles.sql` is ready; the production
      `sessions` table was empty on 2026-10-17, so run it whenever convenient.
- [x] Scenario intake form: who is the other person (manager, parent, co-founder, partner, report)?
      What outcome do you need? What are you afraid they'll say? Relationship history / their usual style?
      (`frontend/src/components/IntakeForm.tsx`; presets prefill it and are editable)
- [x] `POST /api/scenario/build` — LLM turns intake into a counterpart brief with hidden
      motivations and 1–2 curveball objections the user didn't anticipate
      (untouched presets skip the LLM; keyword + LLM safety screen)
- [x] Keep existing girlfriend scenarios as preset templates (*Classic* mode, `classic_brief()`)
- [x] Add preset templates: raise negotiation, hard feedback, career change with parents,
      breakup, layoff conversation, confronting a co-founder (`PRESETS` in `content.py`)
- [x] Update `supabase/migration.sql` (store scenario brief, drop fixed persona/scenario/difficulty checks)
      Fresh installs: `migration.sql`. Existing project: `migrations/002_rehearsal_scenarios.sql`
      (also fixes the RLS policies that granted `anon` full access). **Not yet applied to the live project.**

## Milestone 2 — Split actor and coach

- [x] **Actor** LLM call: plays the counterpart only; tracks internal state
      (receptiveness, trust, defensiveness) which drives voice params
- [x] Judgement on **TypeSafe Jev** (`backend/typesafe.py`): movement, trust and defensiveness deltas plus
      the rubric scores come from typed Score answers, and intake safety / conversation type from Noul + Choice.
      The actor no longer judges the user. Falls back to Sarvam-M self-judging without `TYPESAFE_API_KEY`.
- [x] **Coach** LLM call: scores each user turn against a rubric per conversation type (`RUBRICS`)
  - Emotional repair: acknowledgment, ownership, non-defensiveness
  - Negotiation: clarity of ask, anchoring, objection handling
  - Feedback delivery: specificity, behaviour vs. person, next steps
  - Delivering hard news (added): clarity, empathy, steadiness
- [x] Multi-dimensional score in the UI instead of a single meter (`SkillMeter.tsx`, meter kept for receptiveness)
- [x] Fix end-threshold mismatch: prompt says ≥90, backend now uses `>= 90`
      (`process_user_message`), verdict uses ≥90

## Milestone 3 — Rehearsal loop (feedback & replay)

- [x] Annotated transcript: coach note + "a stronger way to say this" on each user turn
      (live in the chat bubbles; full transcript on the result page)
- [x] Rewind: retry from any turn (`POST /session/{id}/rewind`; ↺ Retry on each user bubble)
- [x] Run again: replay the same scenario and compare scores (`POST /session/{id}/restart`; `previous_score` in the debrief)
- [ ] Supabase Auth — per-user history and progress over time

## Voice providers

- [x] ElevenLabs as the primary voice (`backend/elevenlabs.py`): Eleven v3 TTS with the counterpart's emotion
      as an audio tag, Scribe v2 STT, voices picked from the account by gender. Sarvam Bulbul/Saarika remain
      as per-call fallback and as the provider when `ELEVENLABS_API_KEY` is unset.
- [ ] Measure v3 latency per turn in production; if it hurts, switch `ELEVENLABS_TTS_MODEL=eleven_v3_conversational`
- [x] Accent is part of the intake (`counterpart.accent`, default Indian). `pick_elevenlabs_voice` uses an
      account voice with that accent, or searches the Voice Library and adds one to the account on first use
      (free-tier-allowed, most-used first). Library additions use the account's custom-voice slots; if the plan
      is out of slots the add fails and a same-gender voice is used instead.

## Milestone 4 — Realism

- [ ] Stream LLM output and start TTS on the first sentence to cut per-turn latency
      (actor and coach now run concurrently, but STT → LLM → TTS is still sequential)
- [ ] Hands-free mode with voice-activity detection instead of push-to-talk
- [ ] Counterpart can interrupt long monologues
- [x] Difficulty expressed as counterpart temperament (open / defensive / hostile), not just starting score
      (classic levels kept for the girlfriend presets)

## Milestone 5 — Safety & privacy

- [x] Detect scenarios involving abuse or self-harm and surface support resources
      (keyword backstop + LLM classification in `/scenario/build`; `SafetyNotice.tsx` with Indian helplines; no brief is built)
- [ ] Data-retention policy + "delete my session" endpoint
      `DELETE /api/session/{id}` and the result-page button exist. Automatic expiry (e.g. a Supabase cron
      deleting sessions older than N days) still to do.
- [x] Tighten CORS (`ALLOWED_ORIGINS` env, default localhost; `allow_credentials=False`)

---

## Smaller fixes

- [x] `_supabase_failed` never resets — replaced with a 60s circuit breaker in `db.py`; sessions created
      during an outage live in memory and are read from there first
- [x] Parse debrief tips as a validated JSON array, including fenced/wrapped output
- [x] Mayura (Translate) is listed in CLAUDE.md / PRD but never called — now translates the
      counterpart's opening line into the session language for preset/custom briefs (code-mixed mode for hi-IN)
- [x] Add offline regression tests for malformed LLM output, tips, score thresholds,
      legacy roles, response compatibility and debrief statistics
      (`cd backend && ./venv/bin/python -m unittest discover -s . -v`; 38 tests covering parsing, content,
      prompts, the conversation loop, build/start, rewind/restart/delete, and the storage breaker)
- [x] `game_stats` got two rows per session (chat page and result page both called `/end`); stats are now
      recorded exactly once

## Found while building (not yet done)

- [ ] Rewound counterpart turns lose their audio (only the opening line's audio is kept client-side).
      Store `audio` on counterpart turns or regenerate on demand.
- [ ] `/api/leaderboard` still ranks by `final_score` across all conversation types; group by `conversation_type`.
- [ ] PRD.md still describes v1.
