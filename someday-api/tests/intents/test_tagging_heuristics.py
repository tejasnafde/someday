from modules.tagging.tagging_helper import CANONICAL_TAGS, DOMAIN_TAGS, build_prompt, heuristic_tags


def test_domain_match():
    assert heuristic_tags("https://www.zomato.com/gurgaon/comorin", None) == ["food"]


def test_subdomain_match():
    assert heuristic_tags("https://open.spotify.com/track/abc", None) == ["music"]


def test_no_match_returns_empty():
    assert heuristic_tags("https://example.com/thing", None) == []


def test_no_url():
    assert heuristic_tags(None, None) == []


def test_unrelated_suffix_does_not_match():
    # notzomato.com must not match zomato.com
    assert heuristic_tags("https://notzomato.com/x", None) == []


def test_google_maps_site_tags_places():
    assert heuristic_tags(None, {"site": "Google Maps"}) == ["places"]


def test_domain_map_stays_inside_canonical_vocabulary():
    canonical = set(CANONICAL_TAGS)
    for tags in DOMAIN_TAGS.values():
        for tag in tags:
            assert tag in canonical


def test_build_prompt_includes_signals():
    intent = {
        "title": "Comorin kebabs",
        "category": "eat",
        "url": "https://www.zomato.com/gurgaon/comorin",
        "note": "for anniversary",
        "link_meta": {"site": "Zomato", "description": "Best kebabs in Gurugram"},
    }
    prompt = build_prompt(intent, ["food", "date night"])
    assert "Comorin kebabs" in prompt
    assert "www.zomato.com" in prompt
    assert "Best kebabs" in prompt
    assert "Vocabulary: food, date night" in prompt


def test_build_prompt_tolerates_string_link_meta():
    prompt = build_prompt({"title": "t", "link_meta": '{"site": "X"}'}, ["food"])
    assert "Site: X" in prompt


def test_build_prompt_tolerates_invalid_link_meta():
    prompt = build_prompt({"title": "t", "link_meta": "not json"}, ["food"])
    assert "Title: t" in prompt
