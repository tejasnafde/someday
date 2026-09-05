from handler.unfurl_handler import strip_nul
from modules.tagging.tagging_helper import (
    CANONICAL_TAGS,
    DOMAIN_TAGS,
    build_prompt,
    build_vocabulary,
    heuristic_tags,
)


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


def test_port_in_url_still_matches_domain():
    assert heuristic_tags("https://www.zomato.com:443/x", None) == ["food"]


class VocabStubDB:
    def __init__(self, tags):
        self.tags = tags

    def execute_query_with_value(self, query, params):
        return [{"tag": t} for t in self.tags]


def test_vocabulary_normalizes_legacy_mixed_case_tags():
    vocab = build_vocabulary(VocabStubDB(["Design", "design", "Date  Night"]), "c1")
    assert "design" in vocab
    assert "date night" in vocab
    assert "Design" not in vocab
    assert vocab.count("design") == 1


def test_vocabulary_is_not_capped():
    many = [f"circletag{i}" for i in range(30)]
    vocab = build_vocabulary(VocabStubDB(many), "c1")
    assert len(vocab) == len(CANONICAL_TAGS) + 30


def test_strip_nul_removes_nul_bytes():
    meta = {"title": "a\x00b", "image": None, "site": "x", "description": "\x00"}
    out = strip_nul(meta)
    assert out["title"] == "ab"
    assert out["description"] == ""
    assert out["image"] is None


def test_strip_nul_passes_none_through():
    assert strip_nul(None) is None
