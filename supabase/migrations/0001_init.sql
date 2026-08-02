-- =========================================================
-- Umubyeyi cloud persistence schema
--
-- Run once in the Supabase project's SQL editor. Every table is scoped to
-- the signed-in user via Row Level Security (auth.uid()) -- the anon key
-- shipped to the browser can only ever read/write a user's own rows.
-- =========================================================

create extension if not exists "pgcrypto"; -- gen_random_uuid()

-- ---------- profiles ----------
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  language text check (language in ('rw','en')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "profiles: select own" on public.profiles
  for select using (auth.uid() = id);
create policy "profiles: update own" on public.profiles
  for update using (auth.uid() = id) with check (auth.uid() = id);

-- Auto-create a profile row the moment someone signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id) values (new.id);
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- ---------- threads (jsonb msgs blob, mirrors lib/chat.ts Thread type) ----------
create table public.threads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default '',
  title_source text check (title_source in ('fallback','generated','manual')),
  ts bigint not null,
  msgs jsonb not null default '[]'::jsonb,
  locked boolean not null default false,
  updated_at timestamptz not null default now()
);

alter table public.threads enable row level security;
create index threads_user_ts_idx on public.threads (user_id, ts desc);

create policy "threads: select own" on public.threads
  for select using (auth.uid() = user_id);
create policy "threads: insert own" on public.threads
  for insert with check (auth.uid() = user_id);
create policy "threads: update own" on public.threads
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "threads: delete own" on public.threads
  for delete using (auth.uid() = user_id);

-- ---------- mood_checkins ----------
create table public.mood_checkins (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  mood text not null,
  occurred_at timestamptz not null default now()
);

alter table public.mood_checkins enable row level security;
create index mood_checkins_user_date_idx on public.mood_checkins (user_id, occurred_at desc);

create policy "mood_checkins: select own" on public.mood_checkins
  for select using (auth.uid() = user_id);
create policy "mood_checkins: insert own" on public.mood_checkins
  for insert with check (auth.uid() = user_id);
create policy "mood_checkins: delete own" on public.mood_checkins
  for delete using (auth.uid() = user_id);

-- ---------- epds_results (streak is DERIVED client-side from this history) ----------
create table public.epds_results (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  occurred_at timestamptz not null default now(),
  total int not null check (total between 0 and 30),
  band text not null check (band in ('low','medium','high')),
  item10_flag boolean not null default false
);

alter table public.epds_results enable row level security;
create index epds_results_user_date_idx on public.epds_results (user_id, occurred_at desc);

create policy "epds_results: select own" on public.epds_results
  for select using (auth.uid() = user_id);
create policy "epds_results: insert own" on public.epds_results
  for insert with check (auth.uid() = user_id);
create policy "epds_results: delete own" on public.epds_results
  for delete using (auth.uid() = user_id);

-- ---------- guided_checkins (result summary only -- NOT the raw CHECKIN_FIELDS answers) ----------
create table public.guided_checkins (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  occurred_at timestamptz not null default now(),
  risk text not null,
  elevated boolean not null
);

alter table public.guided_checkins enable row level security;
create index guided_checkins_user_date_idx on public.guided_checkins (user_id, occurred_at desc);

create policy "guided_checkins: select own" on public.guided_checkins
  for select using (auth.uid() = user_id);
create policy "guided_checkins: insert own" on public.guided_checkins
  for insert with check (auth.uid() = user_id);
create policy "guided_checkins: delete own" on public.guided_checkins
  for delete using (auth.uid() = user_id);

-- ---------- concern_history ----------
create table public.concern_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  occurred_at timestamptz not null default now(),
  score numeric not null,
  level text not null
);

alter table public.concern_history enable row level security;
create index concern_history_user_date_idx on public.concern_history (user_id, occurred_at desc);

create policy "concern_history: select own" on public.concern_history
  for select using (auth.uid() = user_id);
create policy "concern_history: insert own" on public.concern_history
  for insert with check (auth.uid() = user_id);
create policy "concern_history: delete own" on public.concern_history
  for delete using (auth.uid() = user_id);
