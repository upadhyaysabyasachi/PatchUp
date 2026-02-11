-- ═══════════════════════════════════════════════════════════════
-- PatchUp 🩹 — Supabase Schema
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor)
-- ═══════════════════════════════════════════════════════════════

-- Sessions table: stores active and completed conversations
create table if not exists sessions (
    id uuid primary key default gen_random_uuid(),
    persona_id text not null,
    scenario_id text not null,
    difficulty text not null check (difficulty in ('easy', 'medium', 'hard', 'nightmare')),
    language text not null default 'hi-IN',
    current_score integer not null default 50,
    status text not null default 'ongoing' check (status in ('ongoing', 'patched_up', 'blocked', 'quit')),
    conversation jsonb not null default '[]'::jsonb,
    system_prompt text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Game stats: aggregated for leaderboard (no PII)
create table if not exists game_stats (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references sessions(id) on delete set null,
    persona_id text not null,
    scenario_id text not null,
    difficulty text not null,
    final_score integer not null,
    status text not null,
    total_turns integer not null default 0,
    created_at timestamptz not null default now()
);

-- Auto-update updated_at on sessions
create or replace function update_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger sessions_updated_at
    before update on sessions
    for each row
    execute function update_updated_at();

-- Indexes for common queries
create index if not exists idx_sessions_status on sessions(status);
create index if not exists idx_game_stats_score on game_stats(final_score desc);
create index if not exists idx_game_stats_status on game_stats(status);

-- Row Level Security (enable for production)
alter table sessions enable row level security;
alter table game_stats enable row level security;

-- Allow service role full access (backend uses service key)
create policy "Service role full access on sessions"
    on sessions for all
    using (true)
    with check (true);

create policy "Service role full access on game_stats"
    on game_stats for all
    using (true)
    with check (true);

-- Allow anonymous read on game_stats for leaderboard
create policy "Public read on game_stats"
    on game_stats for select
    using (true);
