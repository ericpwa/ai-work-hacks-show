-- AI Work Hacks 職場大絕 v0.3 Cloud Ready
-- Run this in Supabase SQL Editor before deploying the Streamlit app.
-- Data retention policy: app keeps classroom data for 90 days by default.

create table if not exists public.classes (
    class_code text primary key,
    class_title text not null default '',
    phase text not null default 'collecting'
        check (phase in ('collecting', 'voting', 'results')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.submissions (
    id bigserial primary key,
    class_code text not null references public.classes(class_code) on delete cascade,
    day text not null,
    name text not null,
    role text not null,
    work_title text not null,
    link text not null,
    summary text not null default '',
    votes integer not null default 0 check (votes >= 0),
    hidden boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.votes (
    id bigserial primary key,
    class_code text not null references public.classes(class_code) on delete cascade,
    submission_id bigint not null references public.submissions(id) on delete cascade,
    voter_label text not null,
    rating integer not null default 1 check (rating between 1 and 5),
    created_at timestamptz not null default now(),
    unique (class_code, submission_id, voter_label)
);

alter table public.votes
    add column if not exists rating integer not null default 1 check (rating between 1 and 5);

create index if not exists idx_aiwh_submissions_class_day_created
    on public.submissions(class_code, day, created_at desc);
create index if not exists idx_aiwh_submissions_class_votes
    on public.submissions(class_code, hidden, votes desc, created_at desc);
create index if not exists idx_aiwh_votes_class_submission
    on public.votes(class_code, submission_id, created_at desc);

alter table public.classes enable row level security;
alter table public.submissions enable row level security;
alter table public.votes enable row level security;

revoke all on table public.classes from anon, authenticated;
revoke all on table public.submissions from anon, authenticated;
revoke all on table public.votes from anon, authenticated;
grant select, insert, update, delete on table public.classes to service_role;
grant select, insert, update, delete on table public.submissions to service_role;
grant select, insert, update, delete on table public.votes to service_role;
grant usage, select on sequence public.submissions_id_seq to service_role;
grant usage, select on sequence public.votes_id_seq to service_role;

create or replace function public.ai_work_hacks_add_vote_rating_once(
    p_submission_id bigint,
    p_class_code text,
    p_voter_label text,
    p_rating integer default 1
)
returns void
language plpgsql
as $$
begin
    if p_rating < 1 or p_rating > 5 then
        raise exception 'invalid_rating';
    end if;

    if not exists (
        select 1
          from public.submissions
         where id = p_submission_id
           and class_code = p_class_code
           and hidden = false
    ) then
        raise exception 'submission_not_found';
    end if;

    insert into public.votes (class_code, submission_id, voter_label, rating)
    values (p_class_code, p_submission_id, trim(p_voter_label), p_rating);

    update public.submissions
       set votes = votes + p_rating,
           updated_at = now()
     where id = p_submission_id
       and class_code = p_class_code;
end;
$$;

create or replace function public.ai_work_hacks_add_vote_once(
    p_submission_id bigint,
    p_class_code text,
    p_voter_label text
)
returns void
language plpgsql
as $$
begin
    perform public.ai_work_hacks_add_vote_rating_once(p_submission_id, p_class_code, p_voter_label, 1);
end;
$$;

create or replace function public.ai_work_hacks_purge_old_data(p_cutoff timestamptz)
returns integer
language plpgsql
as $$
declare
    deleted_count integer;
begin
    with old_submissions as (
        select id
          from public.submissions
         where created_at < p_cutoff
    ),
    deleted_votes as (
        delete from public.votes
         where submission_id in (select id from old_submissions)
    ),
    deleted_submissions as (
        delete from public.submissions
         where id in (select id from old_submissions)
         returning id
    )
    select count(*) into deleted_count from deleted_submissions;

    return deleted_count;
end;
$$;

revoke all on function public.ai_work_hacks_add_vote_once(bigint, text, text) from anon, authenticated;
revoke all on function public.ai_work_hacks_add_vote_rating_once(bigint, text, text, integer) from anon, authenticated;
revoke all on function public.ai_work_hacks_purge_old_data(timestamptz) from anon, authenticated;
grant execute on function public.ai_work_hacks_add_vote_once(bigint, text, text) to service_role;
grant execute on function public.ai_work_hacks_add_vote_rating_once(bigint, text, text, integer) to service_role;
grant execute on function public.ai_work_hacks_purge_old_data(timestamptz) to service_role;

insert into public.classes (class_code, class_title, phase)
values ('AIHACKS-0605', 'AI Work Hacks 課堂', 'collecting')
on conflict (class_code) do nothing;
