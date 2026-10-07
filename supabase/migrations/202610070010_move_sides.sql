begin;
alter table public.line_sides drop constraint line_sides_side_check;
alter table public.line_sides add constraint line_sides_side_check check(side in ('BULL','BEAR','MORE','LESS'));
alter table public.picks drop constraint picks_side_check;
alter table public.picks add constraint picks_side_check check(side in ('BULL','BEAR','MORE','LESS'));
commit;
