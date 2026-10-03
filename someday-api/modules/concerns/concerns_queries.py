"""Raw SQL for the concerns domain."""

# The SELECT from users keeps a deleted or unknown account from filing a report.
INSERT_REPORT = """
    INSERT INTO public.concern_reports (user_id, category, subject, body)
    SELECT id, :category, :subject, :body
    FROM public.users
    WHERE id = :user_id AND status = 1
    RETURNING id, category, created_at
"""
