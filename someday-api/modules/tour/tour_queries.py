"""Raw SQL for the tour domain."""

GET_TOUR_STATE = """
    SELECT tour_state
    FROM public.users
    WHERE id = :user_id AND status = 1
"""

UPDATE_TOUR_STATE = """
    UPDATE public.users
    SET tour_state = CAST(:tour_state AS jsonb)
    WHERE id = :user_id AND status = 1
    RETURNING tour_state
"""
