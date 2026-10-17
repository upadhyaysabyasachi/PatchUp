-- Rehearsal scenarios: bring-your-own counterpart, actor/coach split, rewind & run-again.
-- Run AFTER 001_neutral_conversation_roles.sql and BEFORE deploying the rehearsal backend.
-- Idempotent: safe to re-run.
begin;

-- ── sessions ──────────────────────────────────────────────────────────────────
-- Custom scenarios have no persona; difficulty now also accepts temperaments.
alter table public.sessions
    alter column persona_id drop not null,
    alter column scenario_id drop not null;
alter table public.sessions drop constraint if exists sessions_difficulty_check;
alter table public.sessions add constraint sessions_difficulty_check
    check (difficulty in ('easy', 'medium', 'hard', 'nightmare', 'open', 'defensive', 'hostile'));

alter table public.sessions
    add column if not exists brief jsonb,                       -- counterpart brief (hidden motivations, curveballs, opening line)
    add column if not exists conversation_type text,            -- negotiation | feedback | emotional_repair | difficult_news
    add column if not exists counterpart_state jsonb,           -- {trust, defensiveness}; receptiveness is current_score
    add column if not exists skill_scores jsonb not null default '{}'::jsonb,  -- running per-dimension averages (0-10)
    add column if not exists previous_session_id uuid references public.sessions(id) on delete set null;

create index if not exists idx_sessions_previous on public.sessions(previous_session_id);
create index if not exists idx_sessions_conversation_type on public.sessions(conversation_type);

-- ── game_stats ────────────────────────────────────────────────────────────────
alter table public.game_stats
    alter column persona_id drop not null,
    alter column scenario_id drop not null,
    add column if not exists conversation_type text,
    add column if not exists skill_scores jsonb;

-- ── Row Level Security ────────────────────────────────────────────────────────
-- The backend uses the service role, which bypasses RLS. The old "service role"
-- policies were actually granted to every role, so anyone with the anon key could
-- read and write sessions. Remove them; keep public read on game_stats for the leaderboard.
drop policy if exists "Service role full access on sessions" on public.sessions;
drop policy if exists "Service role full access on game_stats" on public.game_stats;
revoke all on public.sessions from anon, authenticated;
revoke insert, update, delete on public.game_stats from anon, authenticated;

drop policy if exists "Public read on game_stats" on public.game_stats;
create policy "Public read on game_stats"
    on public.game_stats for select
    to anon, authenticated
    using (true);

commit;
