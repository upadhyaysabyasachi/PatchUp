# PatchUp — Roadmap & TODO

Goal: evolve PatchUp from a comedic "angry girlfriend" game into a simulator where people
**rehearse real difficult conversations before they happen** (asking for a raise, giving hard
feedback, telling parents about a career change, ending a relationship, letting someone go, etc.).

## Current state

**Solid, keep:**
- Voice pipeline — STT → LLM → TTS (`process_user_message`, `backend/main.py`)
- Emotion-driven Bulbul voice params (`EMOTION_VOICE_PARAMS`)
- Patch meter UI, audio recorder hook, text fallback
- Supabase with in-memory fallback

**Gaps vs. the goal:**
- Conversation roles now use `user` / `counterpart`; existing comedy preset prompts remain
- Scenarios and personas are fixed comedy bits with canned opening lines (`SCENARIOS`, `PERSONAS`)
- The in-character LLM also judges the user — a single "forgiveness" score conflates the
  counterpart's emotional state with the user's communication skill
- Debrief is only 3 generic tips; for rehearsal, feedback is the core product

---

## Milestone 1 — Bring your own scenario (highest leverage)

- [ ] Rename roles to `user` / `counterpart` across backend, DB and frontend
      Code and legacy-session compatibility implemented; production data migration pending.
- [ ] Scenario intake form: who is the other person (manager, parent, co-founder, partner, report)?
      What outcome do you need? What are you afraid they'll say? Relationship history / their usual style?
- [ ] `POST /api/scenario/build` — LLM turns intake into a counterpart brief with hidden
      motivations and 1–2 curveball objections the user didn't anticipate
- [ ] Keep existing girlfriend scenarios as preset templates
- [ ] Add preset templates: raise negotiation, hard feedback, career change with parents,
      breakup, layoff conversation, confronting a co-founder
- [ ] Update `supabase/migration.sql` (store scenario brief, drop fixed persona/scenario/difficulty checks)

## Milestone 2 — Split actor and coach

- [ ] **Actor** LLM call: plays the counterpart only; tracks internal state
      (receptiveness, trust, defensiveness) which drives voice params
- [ ] **Coach** LLM call: scores each user turn against a rubric per conversation type
  - Emotional repair: acknowledgment, ownership, non-defensiveness
  - Negotiation: clarity of ask, anchoring, objection handling
  - Feedback delivery: specificity, behaviour vs. person, next steps
- [ ] Multi-dimensional score in the UI instead of a single meter
- [x] Fix end-threshold mismatch: prompt says ≥90, backend now uses `>= 90`
      (`process_user_message`), verdict uses ≥90

## Milestone 3 — Rehearsal loop (feedback & replay)

- [ ] Annotated transcript: coach note + "a stronger way to say this" on each user turn
- [ ] Rewind: retry from any turn (truncate conversation + new endpoint + UI)
- [ ] Run again: replay the same scenario and compare scores
- [ ] Supabase Auth — per-user history and progress over time

## Milestone 4 — Realism

- [ ] Stream LLM output and start TTS on the first sentence to cut per-turn latency
      (currently sequential STT → LLM → TTS)
- [ ] Hands-free mode with voice-activity detection instead of push-to-talk
- [ ] Counterpart can interrupt long monologues
- [ ] Difficulty expressed as counterpart temperament (open / defensive / hostile), not just starting score

## Milestone 5 — Safety & privacy

- [ ] Detect scenarios involving abuse or self-harm and surface support resources
- [ ] Data-retention policy + "delete my session" endpoint
- [ ] Tighten CORS (`allow_origins=["*"]` with `allow_credentials=True`)

---

## Smaller fixes

- [ ] `_supabase_failed` never resets — one transient error silently moves the whole process
      to in-memory storage. Add retry / reset.
- [x] Parse debrief tips as a validated JSON array, including fenced/wrapped output
- [ ] Mayura (Translate) is listed in CLAUDE.md / PRD but never called
- [x] Add offline regression tests for malformed LLM output, tips, score thresholds,
      legacy roles, response compatibility and debrief statistics
      (`python -m unittest discover -s backend -v`; 9 tests)
