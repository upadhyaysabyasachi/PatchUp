-- ═══════════════════════════════════════════════════════════════
-- PatchUp 🩹 — Supabase Schema (fresh install)
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor).
-- Idempotent: safe to re-run. For an existing project created from an
-- older version of this file, run supabase/migrations/*.sql in order instead.
-- ═══════════════════════════════════════════════════════════════

-- Sessions: one row per rehearsal (ongoing or finished).
create table if not exists public.sessions (
    id uuid primary key default gen_random_uuid(),
    persona_id text,                     -- classic girlfriend presets only
    scenario_id text,                    -- preset id, classic scenario id, or 'custom'
    difficulty text not null check (difficulty in ('easy', 'medium', 'hard', 'nightmare', 'open', 'defensive', 'hostile')),
    language text not null default 'hi-IN',
    current_score integer not null default 50,   -- counterpart receptiveness, 0-100
    status text not null default 'ongoing' check (status in ('ongoing', 'patched_up', 'blocked', 'quit')),
    conversation jsonb not null default '[]'::jsonb,  -- turns; user turns carry coach annotations
    system_prompt text,
    brief jsonb,                         -- counterpart brief: hidden motivations, curveballs, opening line
    conversation_type text,              -- negotiation | feedback | emotional_repair | difficult_news
    counterpart_state jsonb,             -- {trust, defensiveness}
    skill_scores jsonb not null default '{}'::jsonb,  -- running per-dimension averages (0-10)
    previous_session_id uuid references public.sessions(id) on delete set null,  -- "run again" chain
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Game stats: aggregated for the leaderboard (no transcript, no PII).
create table if not exists public.game_stats (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references public.sessions(id) on delete set null,
    persona_id text,
    scenario_id text,
    difficulty text not null,
    final_score integer not null,
    status text not null,
    total_turns integer not null default 0,
    conversation_type text,
    skill_scores jsonb,
    created_at timestamptz not null default now()
);

-- Auto-update updated_at on sessions.
create or replace function public.update_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists sessions_updated_at on public.sessions;
create trigger sessions_updated_at
    before update on public.sessions
    for each row
    execute function public.update_updated_at();

-- Indexes for common queries.
create index if not exists idx_sessions_status on public.sessions(status);
create index if not exists idx_sessions_previous on public.sessions(previous_session_id);
create index if not exists idx_sessions_conversation_type on public.sessions(conversation_type);
create index if not exists idx_game_stats_score on public.game_stats(final_score desc);
create index if not exists idx_game_stats_status on public.game_stats(status);

-- Row Level Security.
-- The backend uses the service role key, which bypasses RLS, so sessions need no
-- policies at all: anon and authenticated users get nothing. game_stats is readable
-- by everyone for the leaderboard.
alter table public.sessions enable row level security;
alter table public.game_stats enable row level security;

revoke all on public.sessions from anon, authenticated;
revoke insert, update, delete on public.game_stats from anon, authenticated;

drop policy if exists "Service role full access on sessions" on public.sessions;
drop policy if exists "Service role full access on game_stats" on public.game_stats;
drop policy if exists "Public read on game_stats" on public.game_stats;
create policy "Public read on game_stats"
    on public.game_stats for select
    to anon, authenticated
    using (true);
