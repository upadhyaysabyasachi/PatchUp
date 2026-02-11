# PatchUp 🩹 — Product Requirements Document

> **Practice Patching Up With Your AI Girlfriend**
> Voice-Powered Relationship Conversation Simulator | Powered by Sarvam AI — Bulbul V3

| Field | Detail |
|-------|--------|
| Version | 1.0 |
| Date | February 10, 2026 |
| Author | PatchUp Team |
| Status | Draft |
| Contest | #TheMicIsYours — Build with Bulbul Challenge |

---

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. Problem Statement](#2-problem-statement)
- [3. Target Audience](#3-target-audience)
- [4. Feature Specification](#4-feature-specification)
  - [4.1 Girlfriend Persona Selector](#41-girlfriend-persona-selector)
  - [4.2 Scenario Selector](#42-scenario-selector)
  - [4.3 Difficulty Levels](#43-difficulty-levels)
  - [4.4 Voice Conversation Engine](#44-voice-conversation-engine)
  - [4.5 Patch-Up Meter (Scoring System)](#45-patch-up-meter-scoring-system)
  - [4.6 Results Screen](#46-results-screen)
- [5. Technical Architecture](#5-technical-architecture)
  - [5.1 Tech Stack](#51-tech-stack)
  - [5.2 API Endpoints](#52-api-endpoints)
  - [5.3 Database Schema (Supabase)](#53-database-schema-supabase)
- [6. User Flow](#6-user-flow)
- [7. Frontend Pages](#7-frontend-pages)
- [8. Design Direction](#8-design-direction)
- [9. Success Metrics](#9-success-metrics)
- [10. Risks and Mitigations](#10-risks-and-mitigations)
- [11. Future Scope (Post-Hackathon)](#11-future-scope-post-hackathon)
- [12. Appendix: Sarvam API Usage](#12-appendix-sarvam-api-usage)

---

## 1. Executive Summary

PatchUp is a voice-first conversational simulator where users practice convincing an angry AI girlfriend to forgive them. The girlfriend speaks with expressive Indian voices powered by Sarvam Bulbul V3 (text-to-speech), the user speaks back via Sarvam Saarika (speech-to-text), and an LLM (Sarvam-M) drives the girlfriend's personality and judges responses in real-time through a live Patch-Up Meter.

The product is built for the #TheMicIsYours Build with Bulbul Challenge by Sarvam AI, showcasing the full Sarvam AI stack across 4 APIs: Bulbul V3 (TTS), Saarika (STT), Sarvam-M (LLM), and Mayura (Translate).

**Target Users:** Indian men aged 18–35 who want a fun, relatable way to practice communication skills in relationships.

**Core Value Proposition:** A hilarious yet insightful voice-based simulator that showcases Bulbul V3's expressive Indian voices while helping users improve how they handle conflict in relationships.

---

## 2. Problem Statement

Relationship conflicts are universal, but practicing how to handle them is nearly impossible. Most people learn through trial and error — often at the cost of real relationships. There is no safe, low-stakes environment to practice communication skills in emotionally charged scenarios.

Simultaneously, Indian-language voice AI has lacked a compelling, relatable consumer demo. Existing TTS showcases are typically robotic readouts of text — they don't demonstrate the emotional range, code-mixing capability, or natural prosody that Bulbul V3 is capable of.

### Goals

1. Create a viral, shareable demo that showcases Bulbul V3's expressiveness
2. Demonstrate the full Sarvam AI stack (4 APIs) in a single product
3. Build something culturally resonant for Indian users
4. Deliver a polished, production-quality web app within hackathon timelines

---

## 3. Target Audience

### Primary Persona: "The Boyfriend"

- Age 18–35, urban Indian male
- Familiar with Hindi-English code-mixing (Hinglish)
- Active on social media (Instagram, Twitter/X)
- Has been in or is currently in a relationship
- Thinks it's funny and relatable — will share with friends

### Secondary: AI/Tech Community

- Developers evaluating Sarvam AI for voice applications
- Contest judges and Sarvam AI team
- Tech Twitter/LinkedIn audience interested in Indian AI demos

---

## 4. Feature Specification

### 4.1 Girlfriend Persona Selector

Users choose (or customize) the personality of the AI girlfriend they're dealing with. Each persona maps to a specific Bulbul V3 speaker voice, default language, and system prompt behavior.

| Persona | Vibe | Bulbul Voice | Language |
|---------|------|--------------|----------|
| Priya — Bollywood Drama Queen | Over-the-top emotional, filmy dialogues | Priya | hi-IN + en-IN |
| Neha — Silent Treatment Expert | One-word answers, devastating one-liners | Neha | en-IN |
| Ritu — The Logical Arguer | Timestamps, receipts, builds a legal case | Ritu | en-IN + hi-IN |
| Kavya — The Explosive One | Zero to hundred, rapid-fire accusations | Kavya | hi-IN |
| Custom | User-defined persona description | User picks | User picks |

### 4.2 Scenario Selector

Pre-built fight scenarios provide context for the conversation. Each scenario has persona-specific opening lines so the first message feels authentic.

| Scenario | Description |
|----------|-------------|
| Forgot the Anniversary | You didn't wish her. She planned the whole day. |
| Caught Liking Ex's Photo | Instagram activity at 2 AM. Screenshots exist. |
| Said Her Cooking Was 'Okay' | 3 hours of effort. Two-word review. |
| Boys Trip Without Telling Her | She found out from someone else's Instagram story. |
| 2 Hours Late, No Text | She sat alone at the restaurant. Waiter asked thrice. |
| Chose Gaming Over Date Night | You said "20 minutes". It became 3 hours. |
| Custom Scenario | User writes their own scenario description. |

### 4.3 Difficulty Levels

Difficulty affects the girlfriend's stubbornness, forgiveness threshold, starting score, and Bulbul V3 voice parameters (pace and temperature).

| Level | Name | Starting Score | Behavior | TTS Pace / Temp |
|-------|------|---------------|----------|-----------------|
| Easy | Thoda Gussa | 50% | Annoyed but open to listening, gives hints | 0.9x / 0.4 |
| Medium | Full Naraaz | 30% | Cold shoulder, generic sorry barely registers | 1.0x / 0.6 |
| Hard | Breakup Mode | 15% | One wrong word = it's over | 1.2x / 0.8 |
| Nightmare | Maa Ko Bata Dungi | 5% | Threatens family, brings up years-old issues | 1.3x / 0.9 |

### 4.4 Voice Conversation Engine

The core interaction loop is fully voice-based with a text fallback:

1. User holds mic button and speaks
2. Audio sent to Sarvam Saarika v2.5 (STT) for transcription
3. Transcribed text + conversation history sent to Sarvam-M (LLM)
4. LLM returns: girlfriend's response, score delta, emotion tag
5. Response sent to Sarvam Bulbul V3 (TTS) with emotion-based voice parameters
6. Audio plays in browser; chat bubbles and score meter update

#### Dynamic Voice Parameters

Bulbul V3's pace and temperature are dynamically adjusted based on the girlfriend's emotional state, blended with the base difficulty parameters:

| Emotion | Pace | Temperature | Effect |
|---------|------|-------------|--------|
| Angry 😡 | 1.3x | 0.9 | Fast, intense delivery |
| Cold 🧊 | 0.85x | 0.3 | Slow, detached, icy |
| Sarcastic 😏 | 1.0x | 0.6 | Normal pace with an edge |
| Softening 🌸 | 0.9x | 0.5 | Gentler, warming up |
| Happy 😊 | 1.0x | 0.5 | Natural, warm |
| Crying 😢 | 0.8x | 0.7 | Slow, emotional breaks |
| Explosive 🌋 | 1.4x | 0.95 | Maximum speed and intensity |

### 4.5 Patch-Up Meter (Scoring System)

A real-time visual score bar displayed at the top of the chat screen, rendered as a heart-fill progress bar (10 hearts). The LLM evaluates each user response contextually and returns a score delta.

#### Scoring Guidelines (in LLM System Prompt)

| User Response Type | Score Delta |
|--------------------|-------------|
| Genuine acknowledgment + specific details about the mistake | +15 to +25 |
| Thoughtful response showing he understands her feelings | +10 to +20 |
| Simple but sincere "I messed up" | +5 to +10 |
| Generic "sorry babe" with no substance | +1 to +3 |
| Changing the topic or deflecting | -5 to -10 |
| Making excuses ("it wasn't a big deal") | -10 to -15 |
| Getting defensive or arguing back | -15 to -20 |
| Saying something dismissive or hurtful | -20 to -25 |

#### End Conditions

- Score reaches **90%+** → **PATCHED UP** (she forgives you)
- Score drops to **0%** → **BLOCKED** (she's done)
- User ends chat manually → verdict based on final score

### 4.6 Results Screen

After a conversation ends, the user sees:

- Animated verdict (Patched Up / Blocked / Still Naraaz / Made It Worse)
- Final score with heart visualization
- Best and worst responses highlighted from the conversation
- AI-generated tips (via Sarvam-M) on what they should have said
- Share CTA with #TheMicIsYours @SarvamAI for social posting
- Try Again / New Scenario buttons

---

## 5. Technical Architecture

### 5.1 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 14 (App Router) + Tailwind CSS | Polished UI with SSR |
| Backend | FastAPI (Python) | Async API, Sarvam SDK integration |
| AI — TTS | Sarvam Bulbul V3 | Girlfriend's voice (dynamic params) |
| AI — STT | Sarvam Saarika v2.5 | User voice transcription |
| AI — LLM | Sarvam-M | Girlfriend's brain + scoring |
| AI — Translate | Sarvam Mayura v1 | Multi-language support |
| Database | Supabase (PostgreSQL) | Sessions, stats, leaderboard |
| Hosting | Vercel + Railway | Frontend + Backend deployment |

### 5.2 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/personas` | List available girlfriend personas |
| GET | `/api/scenarios` | List fight scenarios |
| GET | `/api/difficulties` | List difficulty levels |
| GET | `/api/leaderboard` | Top 10 patch-up scores |
| POST | `/api/session/start` | Create new game session |
| POST | `/api/session/{id}/respond` | Send voice audio, get response |
| POST | `/api/session/{id}/respond-text` | Text fallback input |
| POST | `/api/session/{id}/end` | End session, get tips |

### 5.3 Database Schema (Supabase)

Two tables with RLS enabled:

#### `sessions`

| Column | Type | Description |
|--------|------|-------------|
| id | uuid (PK) | Session identifier |
| persona_id | text | Selected persona |
| scenario_id | text | Selected scenario |
| difficulty | text (enum) | easy / medium / hard / nightmare |
| language | text | BCP-47 code (e.g. hi-IN) |
| current_score | integer | Live patch-up score (0–100) |
| status | text (enum) | ongoing / patched_up / blocked / quit |
| conversation | jsonb | Full conversation history |
| system_prompt | text | LLM system prompt for this session |

#### `game_stats`

| Column | Type | Description |
|--------|------|-------------|
| id | uuid (PK) | Stats record ID |
| session_id | uuid (FK) | Reference to session |
| persona_id | text | Persona used |
| scenario_id | text | Scenario played |
| difficulty | text | Difficulty level |
| final_score | integer | Final patch-up score |
| total_turns | integer | Number of user turns |

---

## 6. User Flow

1. User lands on home page → sees PatchUp branding + CTA
2. Clicks "Start Practicing" → enters 4-step setup wizard
3. **Step 1:** Pick girlfriend persona (or create custom)
4. **Step 2:** Pick the fight scenario (or write custom)
5. **Step 3:** Pick difficulty level
6. **Step 4:** Pick language + review summary → Start
7. Session starts: girlfriend speaks her opening line (auto-play audio)
8. User holds mic button, speaks response, releases
9. App transcribes (STT), gets LLM response, generates voice (TTS), plays audio
10. Patch-Up Meter updates in real-time with score delta animation
11. Loop continues until: Patched Up (≥90%) / Blocked (≤0%) / User ends
12. Results screen: verdict, score, best/worst moves, AI tips, share button

---

## 7. Frontend Pages

| Route | Page | Key Elements |
|-------|------|-------------|
| `/` | Landing | Hero branding, feature pills, CTA, Sarvam badge |
| `/setup` | Game Setup | 4-step wizard: persona → scenario → difficulty → language |
| `/chat?id=...` | Conversation | Patch-Up Meter, chat bubbles, mic button, emotion indicator |
| `/result?id=...` | Results | Verdict animation, score card, tips, share CTA |

---

## 8. Design Direction

- **Theme:** Dark rose/crimson aesthetic with grain texture overlay
- **Primary Color:** `#e11d48` (Rose/Crimson)
- **Background:** `#0a0506` (Near-black with warm undertone)
- **Typography:** Playfair Display (headings) + DM Sans (body)
- **Cards:** Glass-morphism with backdrop blur and subtle borders
- **Animations:** Slide-up entrances, glow pulse on CTAs, mic ripple effect, heart-fill meter transitions

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Contest Placement | Top 3 | Sarvam AI contest results |
| Demo Completion Rate | >70% | Sessions that reach a verdict vs. abandoned |
| Avg. Turns Per Session | >5 | Indicates engagement and replay value |
| Social Shares | >50 | Posts with #TheMicIsYours mentioning PatchUp |
| Bulbul V3 API Calls | >500 | Demonstrates real usage of the model |

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Sarvam-M returns malformed JSON | High | Robust JSON parser with fallback extraction; default responses |
| STT misinterprets Hindi/Hinglish | Medium | Text input fallback always available |
| TTS latency causes poor UX | Medium | Show processing animation; pre-generate opening lines |
| LLM scoring is inconsistent | Medium | Detailed scoring guidelines in prompt; clamp deltas to -25..+25 |
| Browser mic permission denied | Low | Auto-switch to text mode with clear UI message |
| Supabase downtime | Low | In-memory fallback; app works without DB |

---

## 11. Future Scope (Post-Hackathon)

- Custom persona creator with free-text personality description
- Multiplayer mode: friends watch and vote on responses
- Leaderboard with global rankings by difficulty
- Voice cloning: upload a voice sample for the girlfriend
- Expanded to 22 Indian languages (Bulbul V3 roadmap)
- Mobile app (React Native) with push notification reminders
- Integration with Sarvam Vision for image-based scenarios
- Relationship coaching mode with professional prompts

---

## 12. Appendix: Sarvam API Usage

PatchUp uses the full Sarvam AI stack, making it a comprehensive showcase of India's sovereign AI capabilities:

| API | Model | Endpoint | Usage in PatchUp |
|-----|-------|----------|-----------------|
| Text-to-Speech | Bulbul V3 | `/text-to-speech` | Girlfriend's voice with dynamic pace/temp per emotion |
| Speech-to-Text | Saarika v2.5 | `/speech-to-text` | Transcribing user's voice recordings |
| Chat Completion | Sarvam-M | `/chat/completions` | Generating responses + scoring + tips |
| Translate | Mayura v1 | `/translate` | Language switching support (7 languages) |

All APIs are accessed via the Sarvam REST API (`api.sarvam.ai`) with API key authentication. Bulbul V3 has unlimited free access through February 28, 2026.

---

## Project Structure

```
patchup/
├── backend/
│   ├── main.py                 # FastAPI — all endpoints + Sarvam integrations
│   ├── requirements.txt
│   └── .env.example
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
│   │   │       └── ResultContent.tsx
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
