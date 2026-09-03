"""
End-to-end test of calculate_notes_difficulties() against an in-memory
collection.  Requires the bundled mecab (skipped otherwise).
"""

from __future__ import annotations

import pytest

from tests.fake_collection import FakeCard, FakeNote


def _add_deck(mw, name="Mining", deck_id=1):
    mw.col.decks.add_deck(name, deck_id)


def _add_cards(mw, deck_id, entries):
    """entries: list of dicts with fields/is_new/interval."""
    cards = []
    for entry in entries:
        card = mw.col.add_note(
            deck_id,
            entry["fields"],
            is_new=entry.get("is_new", False),
            interval=entry.get("interval", 0),
        )
        cards.append(card)
    return cards


def test_calculate_notes_difficulties_end_to_end(fake_mw):
    from src.get_diff import calculate_notes_difficulties

    _add_deck(fake_mw, "Mining", deck_id=1)

    # a mature card (known word), a young card and a new card.
    _add_cards(
        fake_mw,
        1,
        [
            {"fields": {"Word": "犬"}, "is_new": False, "interval": 30},
            {"fields": {"Word": "猫"}, "is_new": False, "interval": 3},
            {"fields": {"Word": "犬"}, "is_new": True},
        ],
    )
    # the new card carries the sentence with bracket + ruby furigana
    new_card = fake_mw.col.cards[-1]
    new_card.note()["Sentence"] = "犬[いぬ]と<ruby>猫<rt>ねこ</rt></ruby>が走る。"
    # other fields the add-on writes to
    for field in ("Comment", "am-highlighted", "am-all-morphs"):
        new_card.note()[field] = ""

    from src.get_diff import get_mature_words, get_young_words

    mature = get_mature_words("Mining", "Word")
    young = get_young_words("Mining", "Word")
    assert "犬" in mature
    assert "猫" in young

    calculate_notes_difficulties("Mining", "Sentence", mature_list=mature, young_list=young)

    # difficulty = と, が, 走る unknown (3e6) + 猫 learning (1000)
    assert new_card.due == 3_001_000, new_card.due
    assert new_card.flushed is True
    # am-highlighted keeps furigana markup inside spans
    highlighted = new_card.note()["am-highlighted"]
    assert "犬[いぬ]" in highlighted
    assert "<ruby>猫<rt>ねこ</rt></ruby>" in highlighted
    # readings are not duplicated in the morph list
    morphs = new_card.note()["am-all-morphs"]
    assert "ねこ" not in morphs and "いぬ" not in morphs
    assert "犬" in morphs
    # Comment is cleared
    assert new_card.note()["Comment"] == ""


def test_calculate_notes_difficulties_no_new_cards(fake_mw):
    from src.get_diff import calculate_notes_difficulties

    _add_deck(fake_mw, "Mining", deck_id=1)
    _add_cards(fake_mw, 1, [{"fields": {"Word": "犬"}, "is_new": False, "interval": 30}])
    calculate_notes_difficulties("Mining", "Sentence", mature_list=[], young_list=[])


def test_calculate_notes_difficulties_empty_sentence(fake_mw):
    from src.get_diff import calculate_notes_difficulties

    _add_deck(fake_mw, "Mining", deck_id=1)
    _add_cards(fake_mw, 1, [{"fields": {"Word": "犬"}, "is_new": True}])
    card = fake_mw.col.cards[-1]
    card.note()["Sentence"] = ""
    for field in ("Comment", "am-highlighted", "am-all-morphs"):
        card.note()[field] = ""
    calculate_notes_difficulties("Mining", "Sentence", mature_list=[], young_list=[])
    assert card.due == 0
