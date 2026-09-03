"""
Integration tests for get_diff using the real bundled mecab.

These are skipped automatically when the bundled mecab cannot run.
"""

from __future__ import annotations

import pytest

mecab = pytest.importorskip("src.mecab_controller")


def _make_mecab():
    from src.mecab_controller import MecabController

    return MecabController()


@pytest.fixture(scope="module")
def controller():
    try:
        mecab = _make_mecab()
        mecab.translate("テスト")  # smoke test
        return mecab
    except Exception as exc:  # pragma: no cover - env dependent
        pytest.skip(f"bundled mecab is not runnable here: {exc}")


# ---------------------------------------------------------------------------
# difficulty parity: the same sentence with and without furigana
# ---------------------------------------------------------------------------

SENTENCE_VARIANTS = [
    ("犬が公園を走る。", ["犬[いぬ]が公園[こうえん]を走る。", "<ruby>犬<rt>いぬ</rt></ruby>が<ruby>公園<rt>こうえん</rt></ruby>を走る。"]),
    ("昨日、学校へ行った。", ["昨日[きのう]、学校[がっこう]へ行[い]った。", "昨日[きのう]、<ruby>学校<rt>がっこう</rt></ruby>へ行った。"]),
    ("私は本を読みます。", ["私[わたし]は本[ほん]を読[よ]みます。", "私は<ruby>本<rt>ほん</rt></ruby>を読みます。"]),
    ("猫は魚が好きだ。", ["猫[ねこ]は魚[さかな]が好き[すき]だ。", "<ruby>猫<rt>ねこ</rt></ruby>は<ruby>魚<rt>さかな</rt></ruby>が好きだ。"]),
]


@pytest.mark.parametrize("plain,annotated", SENTENCE_VARIANTS)
def test_furigana_does_not_change_difficulty(controller, plain, annotated):
    from src.get_diff import get_sentence_difficulty

    plain_diff, _ = get_sentence_difficulty(plain, [], [], controller)
    for annotated_sentence in annotated:
        annotated_diff, _ = get_sentence_difficulty(annotated_sentence, [], [], controller)
        assert annotated_diff == plain_diff, (plain, annotated_sentence)


@pytest.mark.parametrize("plain,annotated", SENTENCE_VARIANTS)
def test_furigana_does_not_change_morphs(controller, plain, annotated):
    from src.get_diff import get_sentence_headwords

    plain_headwords = get_sentence_headwords(plain, controller)
    for annotated_sentence in annotated:
        assert get_sentence_headwords(annotated_sentence, controller) == plain_headwords


# ---------------------------------------------------------------------------
# known words are recognised despite furigana
# ---------------------------------------------------------------------------


def test_known_words_are_not_counted_unknown(controller):
    from src.get_diff import get_sentence_difficulty

    mature = ["犬", "公園", "走る"]
    # all content words are known; particles が/を still count as unknown by
    # this add-on's simplified difficulty model.
    diff_bracket, fmt = get_sentence_difficulty("犬[いぬ]が公園[こうえん]を走る。", mature, [], controller)
    diff_plain, _ = get_sentence_difficulty("犬が公園を走る。", mature, [], controller)
    assert diff_bracket == diff_plain
    assert 'morph-status="known"' in fmt
    assert "犬[いぬ]" in fmt  # reading is kept inside the span
    assert fmt.count("unknown") == 2  # が and を
    assert diff_bracket == 2_000_000


def test_learning_words_add_1000(controller):
    from src.get_diff import get_sentence_difficulty

    young = ["犬"]
    diff, fmt = get_sentence_difficulty("犬[いぬ]が走る。", [], young, controller)
    # 犬 learning (+1000), が unknown (+1e6), 走る unknown (+1e6)
    assert diff == 2_001_000
    assert 'morph-status="learning"' in fmt


# ---------------------------------------------------------------------------
# am-highlighted keeps original markup 1:1
# ---------------------------------------------------------------------------


def test_highlight_keeps_markup_for_bracket_sentence(controller):
    from src.get_diff import get_sentence_difficulty

    sentence = "猫[ねこ]は魚[さかな]が好き[すき]だ。"
    _, fmt = get_sentence_difficulty(sentence, [], [], controller)
    assert "猫[ねこ]" in fmt
    assert "魚[さかな]" in fmt
    assert "好き[すき]" in fmt
    # no stray raw reading outside of span
    assert "ねこ" in fmt and fmt.count("ねこ") == 1


def test_highlight_keeps_ruby_markup(controller):
    from src.get_diff import get_sentence_difficulty

    sentence = "<ruby>猫<rt>ねこ</rt></ruby>は<ruby>魚<rt>さかな</rt></ruby>が好きだ。"
    _, fmt = get_sentence_difficulty(sentence, [], [], controller)
    assert "<ruby>猫<rt>ねこ</rt></ruby>" in fmt
    assert "<ruby>魚<rt>さかな</rt></ruby>" in fmt
    # ruby elements wrapped whole
    assert 'morph-status="unknown"><ruby>' in fmt


def test_highlight_does_not_break_on_symbols_and_numbers(controller):
    from src.get_diff import get_sentence_difficulty

    sentence = "りんごを2個買った。"
    diff, fmt = get_sentence_difficulty(sentence, [], [], controller)
    assert "2" in fmt
    assert isinstance(diff, int)


def test_highlight_no_furigana_plain_text(controller):
    from src.get_diff import get_sentence_difficulty

    sentence = "今日 は いい 天気 です。"
    diff, fmt = get_sentence_difficulty(sentence, [], [], controller)
    assert "今日" in fmt and "天気" in fmt
    assert diff == 5_000_000


def test_furigana_from_reading_method_matches_plain_difficulty(controller):
    """
    mecab.reading() generates AJT/Migaku-style square-bracket furigana with
    okurigana split out (e.g. 食[た]べた) and spaces between tokens.  Analysing
    that annotated text must give the same difficulty as the plain sentence.
    """
    from src.get_diff import get_sentence_difficulty

    plain_sentences = [
        "犬が公園を走る。",
        "昨日、友達と映画を観た。",
        "私は本を読んだ。",
        "日本語を勉強しています。",
        "取って置きなさい。",
        "猫は魚が好きだ。",
    ]
    for plain in plain_sentences:
        annotated = controller.reading(plain)  # type: ignore[attr-defined]
        assert annotated != plain, plain
        plain_diff, _ = get_sentence_difficulty(plain, [], [], controller)
        annotated_diff, fmt = get_sentence_difficulty(annotated, [], [], controller)
        assert annotated_diff == plain_diff, (plain, annotated)
        assert "<span morph-status=" in fmt


def test_reading_method_output_round_trips_to_plain_chars(controller):
    """Annotated text minus readings equals plain text minus whitespace."""
    from src.furigana import strip_furigana

    plain = "相合い傘をさして歩いた。"
    annotated = controller.reading(plain)  # type: ignore[attr-defined]
    stripped = "".join(strip_furigana(annotated).split())
    assert stripped == plain


def test_migaku_sentences_difficulty_sorted_consistently(controller):
    """
    Sentences of differing difficulty keep their relative order whether or not
    they carry furigana.
    """
    from src.get_diff import get_sentence_difficulty

    easy_plain = "私は犬が好きだ。"
    hard_plain = "彼は化学の教科書を読んでいる。"
    easy_furi = controller.reading(easy_plain)  # type: ignore[attr-defined]
    hard_furi = controller.reading(hard_plain)  # type: ignore[attr-defined]
    d_easy = get_sentence_difficulty(easy_plain, [], [], controller)[0]
    d_hard = get_sentence_difficulty(hard_plain, [], [], controller)[0]
    assert d_easy < d_hard
    assert get_sentence_difficulty(easy_furi, [], [], controller)[0] == d_easy
    assert get_sentence_difficulty(hard_furi, [], [], controller)[0] == d_hard


def test_empty_sentence_does_not_crash(controller):
    from src.get_diff import get_sentence_difficulty

    diff, fmt = get_sentence_difficulty("", [], [], controller)
    assert diff == 0
    assert fmt == ""


def test_reading_output_with_spaces_matches_plain(controller):
    """
    mecab.reading() inserts a space before every token that got furigana, so
    the stripped annotated text still contains those spaces.  As long as the
    tokens themselves don't change, difficulty must be unaffected.
    """
    from src.get_diff import get_sentence_difficulty
    from src.furigana import strip_furigana

    plain = "彼は本を読んだ。"
    annotated = controller.reading(plain)  # e.g. ' 彼[かれ]は 本[ほん]を 読[よ]んだ。'
    # tokens of the plain and of the stripped annotated text must be the same
    plain_tokens = [t.word for t in controller.translate(plain)]
    stripped_tokens = [t.word for t in controller.translate(strip_furigana(annotated))]
    assert plain_tokens == stripped_tokens
    assert get_sentence_difficulty(plain, [], [], controller)[0] == get_sentence_difficulty(
        annotated, [], [], controller
    )[0]
