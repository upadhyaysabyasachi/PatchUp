-- Run once AFTER deploying the backend that reads both legacy and neutral roles.
-- New sessions already use user/counterpart. Preserve all other turn metadata.
begin;

update public.sessions
set conversation = (
    select jsonb_agg(
        case turn->>'role'
            when 'boyfriend' then jsonb_set(turn, '{role}', '"user"'::jsonb)
            when 'girlfriend' then jsonb_set(turn, '{role}', '"counterpart"'::jsonb)
            else turn
        end order by position
    )
    from jsonb_array_elements(conversation) with ordinality as turns(turn, position)
)
where jsonb_path_exists(conversation, '$[*] ? (@.role == "boyfriend" || @.role == "girlfriend")');

commit;
