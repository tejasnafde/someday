-- Tell an admin removal apart from a member leaving. Both still set
-- status = 0, so every existing status filter keeps working. A removal also
-- stamps removed_at and removed_by, and joining by invite refuses a row with
-- removed_at set until an admin allows the person back (clears it).
-- One ALTER per column: test_deletion_coverage parses one ADD COLUMN per statement.

ALTER TABLE public.circle_members ADD COLUMN IF NOT EXISTS removed_at timestamptz;
ALTER TABLE public.circle_members ADD COLUMN IF NOT EXISTS removed_by uuid REFERENCES public.users(id);
