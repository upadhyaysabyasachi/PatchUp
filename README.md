# 🩹 PatchUp — Rehearse the hard conversation

> *"The raise. The breakup. The talk with your father. Out loud, with someone who pushes back."*

A voice-first simulator for practising difficult conversations before they happen. You describe who you're talking to and what you need; PatchUp builds the other side, including things they won't say out loud and a couple of curveballs you haven't prepared for. You speak (**Sarvam Saarika**), they answer in an expressive Indian voice (**Sarvam Bulbul V3**), and a coach grades every turn you take.

The original *convince your angry girlfriend* game is still here as **Classic** mode.

**Built for #TheMicIsYours — Build with Bulbul Challenge by @SarvamAI**

---

## 🎯 Sarvam APIs Used (Full Sarvam Stack)

| API | Model | Purpose |
|-----|-------|---------|
| **Text-to-Speech** | **Bulbul V3** ⭐ | The counterpart's voice — pace/temperature follow emotion and defensiveness; 30+ voices picked per counterpart |
| **Speech-to-Text** | Saarika v2.5 | Transcribing your voice input |
| **Chat Completion** | Sarvam-M | Three roles: the **actor** (plays the counterpart), the **coach** (scores your turn), the **scenario builder** (intake → brief) |
| **Translate** | Mayura v1 | Says the counterpart's opening line in your chosen language (code-mixed Hinglish for Hindi); translates native-script turns for the judge |

### Judgement: TypeSafe Jev

The parts of PatchUp that are *judgement* rather than generation run on [TypeSafe Jev](https://docs.typesafe.ai), a System One model that returns typed, calibrated answers instead of text: how much your message moved the counterpart (and their trust and defensiveness), your 0-10 score on each rubric dimension, and whether a custom scenario involves abuse or self-harm. Set `TYPESAFE_API_KEY` to enable it. Without it, the Sarvam-M actor self-reports movement and the coach self-scores, as a fallback.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ & Node.js 18+
- Sarvam AI API key (free at [dashboard.sarvam.ai](https://dashboard.sarvam.ai))

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # Edit and add your SARVAM_API_KEY
uvicorn main:app --reload --port 8000
```

Tests (offline, no key needed): `python -m unittest discover -s . -v`

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # Edit: set NEXT_PUBLIC_API_URL for production (e.g. Render backend URL)
npm run dev
```

### 3. Open http://localhost:3000 🩹

### 4. (Optional) Supabase Database

1. Create a project at [supabase.com](https://supabase.com)
2. Fresh project: run `supabase/migration.sql` in the SQL Editor. Existing PatchUp project: run `supabase/migrations/*.sql` in order.
3. Add `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` to `backend/.env`

Without Supabase, the app works with in-memory storage (sessions are lost on restart).

---

## 🌐 Deploy (Render + Vercel)

**Backend (Render)**

1. Push this repo and connect it to [Render](https://render.com) as a new **Web Service**.
2. Render will use the root [render.yaml](render.yaml): root = `backend`, build = `pip install -r requirements.txt`, start = `uvicorn main:app --host 0.0.0.0 --port $PORT`.
3. Add **Environment** variables: `SARVAM_API_KEY` (required), `ALLOWED_ORIGINS` = your Vercel URL, `TYPESAFE_API_KEY` for Jev judgement. Optionally `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` for persistence.
4. Deploy and copy the backend URL (e.g. `https://patchup-api.onrender.com`).

**Frontend (Vercel)**

1. Connect the same repo to [Vercel](https://vercel.com), set **Root Directory** to `frontend`.
2. Add **Environment Variable**: `NEXT_PUBLIC_API_URL` = your Render backend URL.
3. Deploy.

**Current deployments**

| | Production (`main`) | Staging (`feature/rehearsal-simulator`) |
|---|---|---|
| Backend (Render) | `patchup.onrender.com` | `patchup-api-rehearsal.onrender.com` ([env vars](https://dashboard.render.com/web/srv-db9m037btjjs73c7ljsg/env)) |
| Frontend (Vercel project `patchup`) | `patchup-eight.vercel.app` | `patchup-git-feature-rehear-e197ee-sabyasachi-upadhyays-projects.vercel.app` |

Both auto-deploy on push to their branch. Render free tier sleeps after 15 min idle; the first request takes up to a minute. Secrets (`SARVAM_API_KEY`, `TYPESAFE_API_KEY`) are set in the Render dashboard only, never in the repo.

---

## ✨ Features

- 🎙️ **Full voice conversations** — speak and hear them respond
- 📋 **6 rehearsal presets** — ask for a raise, give hard feedback, tell your father you're quitting, end a relationship, let someone go, confront your co-founder
- ✍️ **Write your own** — who they are, what you need, what you're afraid they'll say → a brief with hidden motivations and curveballs
- 🎭 **Temperaments** — open / defensive / hostile; the counterpart tracks receptiveness, trust and defensiveness
- 🧭 **Coach on every turn** — scored on a 3-dimension rubric per conversation type (negotiation, feedback, emotional repair, hard news), with a note and a stronger way to say it
- ↺ **Rewind** — retry from any turn; **Run again** — same scenario, compare with your last score
- 📝 **Debrief** — skill bars, annotated transcript, and what the other person wasn't saying
- 🛡️ **Safety** — scenarios involving abuse or self-harm get support resources, not a simulation
- 🩹 **Classic mode** — 4 girlfriend personas × 6 fight scenarios × 4 anger levels, unchanged
- 🌐 **9 Indian languages** — Hindi (code-mixed), English, Tamil, Telugu, Bengali, Kannada, Malayalam, Marathi, Gujarati
- ⌨️ **Text fallback** — works without a mic

---

## 🔌 API (`/api`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/catalog` | Presets, personas, scenarios, temperaments, difficulties, languages, rubrics |
| POST | `/scenario/build` | `{preset_id?, intake?}` → `{brief}` or `{safety}` |
| POST | `/session/start` | `{brief, difficulty, language}` or classic `{persona_id, scenario_id, difficulty, language}` |
| POST | `/session/{id}/respond` · `/respond-text` | One turn: actor + coach (concurrent) → TTS |
| POST | `/session/{id}/rewind` | `{turn_number}` — retry from that turn |
| POST | `/session/{id}/restart` | Same scenario again, linked for score comparison |
| POST | `/session/{id}/end` | Debrief: tips, skill scores, annotated transcript, reveal |
| GET / DELETE | `/session/{id}` | Snapshot / delete your data |

---

## 📁 Project Structure

```
patchup/
├── render.yaml
├── backend/
│   ├── main.py                 # FastAPI — endpoints + orchestration
│   ├── content.py              # Presets, personas, temperaments, rubrics, voices, safety resources
│   ├── prompts.py              # Actor / coach / scenario-builder / debrief prompts
│   ├── parsing.py              # Robust parsing of LLM output
│   ├── sarvam.py               # Sarvam STT / TTS / LLM / Translate
│   ├── db.py                   # Supabase + in-memory fallback with circuit breaker
│   ├── test_main.py            # Offline regression tests
│   └── requirements.txt
├── frontend/src/
│   ├── app/
│   │   ├── page.tsx            # Landing
│   │   ├── setup/page.tsx      # Presets / write your own / classic → temperament → language
│   │   ├── chat/ChatContent.tsx    # Voice conversation, meter, skill bars, coach notes, retry
│   │   └── result/ResultContent.tsx # Debrief
│   ├── components/             # PatchMeter, SkillMeter, ChatBubble, MicButton, IntakeForm, SafetyNotice
│   ├── hooks/useAudioRecorder.ts
│   └── lib/api.ts              # Typed API client
├── supabase/
│   ├── migration.sql           # Fresh-install schema
│   └── migrations/             # Incremental migrations for existing projects
└── docs/TODO.md                # Roadmap
```

---

## 📝 License

MIT — Built with ❤️ for the Sarvam Bulbul V3 Challenge
