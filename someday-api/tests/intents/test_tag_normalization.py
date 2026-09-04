from schemas.intents_schema import MAX_TAGS, CreateIntentRequest, normalize_tags


def test_lowercases_and_trims():
    assert normalize_tags(["  Design ", "FOOD"]) == ["design", "food"]


def test_dedupes_case_variants_preserving_order():
    assert normalize_tags(["Movies", "movies", "MOVIES", "food"]) == ["movies", "food"]


def test_collapses_inner_whitespace():
    assert normalize_tags(["date   night"]) == ["date night"]


def test_drops_empty_entries():
    assert normalize_tags(["", "   ", "food"]) == ["food"]


def test_caps_count():
    tags = [f"tag{i}" for i in range(MAX_TAGS + 5)]
    assert len(normalize_tags(tags)) == MAX_TAGS


def test_caps_length():
    out = normalize_tags(["x" * 200])
    assert len(out[0]) == 40


def test_create_request_normalizes():
    req = CreateIntentRequest(title="t", tags=["Food", "food ", "Date  Night"])
    assert req.tags == ["food", "date night"]
