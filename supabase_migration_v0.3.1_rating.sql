-- AI Work Hacks 職場大絕 v0.3.1
-- Live migration: add 1-5 star ratings while preserving existing votes.

alter table public.votes
    add column if not exists rating integer not null default 1 check (rating between 1 and 5);

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

grant execute on function public.ai_work_hacks_add_vote_once(bigint, text, text) to service_role;
grant execute on function public.ai_work_hacks_add_vote_rating_once(bigint, text, text, integer) to service_role;
