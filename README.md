# 🩹 PatchUp — Practice Patching Up With Your AI Girlfriend

> *"Practice before you patch up. Because second chances don't come with a tutorial."*

A voice-first relationship simulator where you practice convincing an angry AI girlfriend to forgive you. She speaks in expressive Indian voices (**Sarvam Bulbul V3**), you speak back (**Sarvam Saarika STT**), and an LLM (**Sarvam-M**) judges your responses in real-time with a live Patch-Up Meter.

**Built for #TheMicIsYours — Build with Bulbul Challenge by @SarvamAI**

---

## 🎯 Sarvam APIs Used (Full Sarvam Stack!)

| API | Model | Purpose |
|-----|-------|---------|
| **Text-to-Speech** | **Bulbul V3** ⭐ | Girlfriend's voice — dynamic pace/temperature per emotion |
| **Speech-to-Text** | Saarika v2.5 | Transcribing your voice input |
| **Chat Completion** | Sarvam-M | Girlfriend's AI brain + response scoring |
| **Translate** | Mayura v1 | Multi-language support |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ & Node.js 18+
- Sarvam AI API key (free at [dashboard.sarvam.ai](https://dashboard.sarvam.ai) — unlimited Bulbul V3 until Feb 28!)

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # Edit and add your SARVAM_API_KEY
uvicorn main:app --reload --port 8000
```

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
2. Run `supabase/migration.sql` in the SQL Editor
3. Add `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` to `backend/.env`

Without Supabase, the app works perfectly with in-memory storage.

---

## 🌐 Deploy (Render + Vercel)

**Backend (Render)**

1. Push this repo and connect it to [Render](https://render.com) as a new **Web Service**.
2. Render will use the root [render.yaml](render.yaml): root = `backend`, build = `pip install -r requirements.txt`, start = `uvicorn main:app --host 0.0.0.0 --port $PORT`. Confirm these in the dashboard if you didn’t use the blueprint.
3. In the Render service, add **Environment** variables: `SARVAM_API_KEY` (required). Optionally `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` for persistence.
4. Deploy and copy the backend URL (e.g. `https://patchup-api.onrender.com`).

**Frontend (Vercel)**

1. Connect the same repo to [Vercel](https://vercel.com), set **Root Directory** to `frontend`.
2. Add **Environment Variable**: `NEXT_PUBLIC_API_URL` = your Render backend URL (e.g. `https://patchup-api.onrender.com`). For local dev this defaults to `http://localhost:8000` if unset; in production it must be set to your backend URL.
3. Deploy. The app at your Vercel URL will talk to the Render backend.

---

## ✨ Features

- 🎙️ **Full Voice Conversations** — Speak and hear her respond in real-time
- 🎭 **4 Girlfriend Personas** — Drama Queen, Silent Treatment, Logical Arguer, Explosive
- 📋 **6 Fight Scenarios** — Anniversary, ex's photo, cooking, boys trip, late, gaming
- 🔥 **4 Difficulty Levels** — Thoda Gussa → Maa Ko Bata Dungi
- 💕 **Live Patch-Up Meter** — Heart-fill scoring with real-time feedback
- 🗣️ **Hindi-English Code-Mixing** — Natural Hinglish (Bulbul V3's killer feature)
- 🌐 **7 Indian Languages** — Hindi, English, Tamil, Telugu, Bengali, Kannada, Malayalam
- 🎚️ **Dynamic Voice Params** — Bulbul V3 pace/temperature change with her emotion
- ⌨️ **Text Fallback** — Works without mic too
- 🏆 **Results + Tips** — AI-generated coaching after each attempt

---

## 🎤 Bulbul V3 Dynamic Voice

| Emotion | Pace | Temp | Effect |
|---------|------|------|--------|
| Angry 😡 | 1.3x | 0.9 | Fast, intense |
| Cold 🧊 | 0.85x | 0.3 | Slow, detached |
| Sarcastic 😏 | 1.0x | 0.6 | Normal with edge |
| Softening 🌸 | 0.9x | 0.5 | Gentle, warming |
| Explosive 🌋 | 1.4x | 0.95 | Maximum intensity |

---

## 📁 Project Structure

```
patchup/
├── render.yaml                 # Render backend config (rootDir: backend)
├── backend/
│   ├── main.py                 # FastAPI — all endpoints + Sarvam integrations
│   ├── requirements.txt
│   ├── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx            # Landing page
│   │   │   ├── layout.tsx          # Root layout
│   │   │   ├── globals.css         # Custom styles + animations
│   │   │   ├── setup/page.tsx      # Persona/scenario/difficulty picker
│   │   │   ├── chat/
│   │   │   │   ├── page.tsx        # Chat wrapper (Suspense)
│   │   │   │   └── ChatContent.tsx # Core voice conversation UI
│   │   │   └── result/
│   │   │       ├── page.tsx        # Result wrapper (Suspense)
│   │   │       └── ResultContent.tsx # Score, tips, share
│   │   ├── components/
│   │   │   ├── PatchMeter.tsx      # Heart-fill score bar
│   │   │   ├── MicButton.tsx       # Recording button + animations
│   │   │   └── ChatBubble.tsx      # Message bubbles with replay
│   │   ├── hooks/
│   │   │   └── useAudioRecorder.ts # Browser MediaRecorder hook
│   │   └── lib/
│   │       └── api.ts              # API client + audio player
│   ├── package.json
│   ├── tailwind.config.js
│   └── .env.local.example
├── supabase/
│   └── migration.sql               # Database schema
└── README.md
```

---

## 📝 License

MIT — Built with ❤️ for the Sarvam Bulbul V3 Challenge
