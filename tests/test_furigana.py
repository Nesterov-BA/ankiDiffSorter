"""Unit tests for the furigana-aware parser (no mecab / anki required)."""

from __future__ import annotations

import re

import pytest

from src.furigana import AnnotatedText, is_kana_only, strip_furigana

# ---------------------------------------------------------------------------
# is_kana_only
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("いぬ", True),
        ("カナ", True),
        ("こーひー", True),
        ("か・な", True),
        ("", False),
        ("犬", False),
        ("いぬ1", False),
        ("[いぬ]", False),
    ],
)
def test_is_kana_only(text, expected):
    assert is_kana_only(text) is expected


# ---------------------------------------------------------------------------
# strip_furigana: square brackets
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("犬[いぬ]が走る", "犬が走る"),
        ("犬[いぬ]が 走[はし]る", "犬が 走る"),
        # okurigana stays outside the brackets
        ("食[た]べた", "食べた"),
        ("見[み]た", "見た"),
        # full word reading
        ("食べる[たべる]", "食べる"),
        # two annotated words
        ("猫[ねこ]と犬[いぬ]", "猫と犬"),
        # mixed
        ("私は本[ほん]を読[よ]んだ", "私は本を読んだ"),
    ],
)
def test_strip_square_brackets(source, expected):
    assert strip_furigana(source) == expected


def test_brackets_with_non_kana_are_left_alone():
    # [笑] is not furigana: contains kanji, must not be stripped.
    assert strip_furigana("彼は[笑]ながら話した") == "彼は[笑]ながら話した"


def test_katakana_reading():
    assert strip_furigana("ドラゴン[どらごん]") == "ドラゴン"


# ---------------------------------------------------------------------------
# strip_furigana: ruby
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<ruby>犬<rt>いぬ</rt></ruby>が走る", "犬が走る"),
        ("<ruby>食<rt>た</rt></ruby>べた", "食べた"),
        ("<ruby>食べる<rt>たべる</rt></ruby>", "食べる"),
        # rp / rb variants
        ("<ruby>犬<rp>(</rp><rt>いぬ</rt><rp>)</rp></ruby>", "犬"),
        ("<ruby><rb>犬</rb><rt>いぬ</rt></ruby>", "犬"),
        # two ruby elements
        ("<ruby>猫<rt>ねこ</rt></ruby>と<ruby>犬<rt>いぬ</rt></ruby>", "猫と犬"),
    ],
)
def test_strip_ruby(source, expected):
    assert strip_furigana(source) == expected


def test_strip_mixed_brackets_and_ruby():
    src = "私は<ruby>犬<rt>いぬ</rt></ruby>と猫[ねこ]を見た"
    assert strip_furigana(src) == "私は犬と猫を見た"


# ---------------------------------------------------------------------------
# strip_furigana: html tags / anki placeholders / whitespace
# ---------------------------------------------------------------------------


def test_plain_keeps_other_html_content_but_strips_tags():
    assert strip_furigana("<b>犬</b>が走る") == "犬が走る"
    assert strip_furigana("これは<span class='x'>テスト</span>です") == "これはテストです"


def test_sound_and_type_tags_are_removed_from_plain():
    assert strip_furigana("[sound:dog.mp3]犬が吠える") == "犬が吠える"
    assert strip_furigana("[[type:vocab]]猫が好き") == "猫が好き"


def test_plain_keeps_whitespace():
    assert strip_furigana("今日 は いい 天気") == "今日 は いい 天気"


def test_plain_normalizes_newline_and_tilde():
    assert strip_furigana("昨日\n今日") == "昨日 今日"
    assert strip_furigana("大きい\uff5e小さい") == "大きい~小さい"


# ---------------------------------------------------------------------------
# highlight render
# ---------------------------------------------------------------------------


def _render_tokens(text, ranges, status="unknown"):
    """Wrap the given plain-text ranges with spans (like token-based render)."""
    annotated = AnnotatedText(text)
    segments = [(s, e, status) for s, e in ranges]
    return annotated.render(segments)


@pytest.mark.parametrize(
    ("source", "ranges", "needle"),
    [
        # reading text stays *inside* the span, markup preserved
        ("犬[いぬ]が走る", [(0, 1)], '<span morph-status="unknown">犬[いぬ]</span>'),
        (
            "<ruby>犬<rt>いぬ</rt></ruby>が走る",
            [(0, 1)],
            '<span morph-status="unknown"><ruby>犬<rt>いぬ</rt></ruby></span>',
        ),
        # mecab tokenizes 食べた as 食べ + た
        ("食[た]べた", [(0, 2)], '<span morph-status="unknown">食[た]べ</span>'),
        ("食べた[たべた]", [(0, 3)], '<span morph-status="unknown">食べた[たべた]</span>'),
    ],
)
def test_render_keeps_reading_inside_span(source, ranges, needle):
    rendered = _render_tokens(source, ranges)
    assert needle in rendered


def test_render_preserves_original_markup_when_no_reading_text_is_lost():
    source = "これは<ruby>毎日<rt>まいにち</rt></ruby>コーヒーを飲[の]む"
    annotated = AnnotatedText(source)
    segments = [(i, i + 1, "known") for i in range(len(annotated.plain))]
    rendered = annotated.render(segments)
    # every base char is wrapped; original markup must still be present
    assert "<ruby>毎日<rt>まいにち</rt></ruby>" in rendered
    assert "[の]" in rendered


def test_render_no_furigana_returns_markup_skeleton():
    # With realistic token segments, markup around/inside words is preserved.
    source = "昨日、<b>学校</b>へ行った。"
    annotated = AnnotatedText(source)
    # tokens: 昨日 | 、 | 学校 | へ | 行っ | た | 。
    ranges = [(0, 2), (2, 3), (3, 5), (5, 6), (6, 8), (8, 9), (9, 10)]
    rendered = annotated.render([(s, e, "known") for s, e in ranges])
    assert "<b>" in rendered and "</b>" in rendered
    assert "学校" in rendered


def test_render_unknown_style():
    # sanity: statuses known/learning/unknown all render the span attr
    annotated = AnnotatedText("犬が走る")
    rendered = annotated.render(
        [(0, 1, "known"), (1, 2, "learning"), (2, 4, "unknown")]
    )
    assert rendered == (
        '<span morph-status="known">犬</span>'
        '<span morph-status="learning">が</span>'
        '<span morph-status="unknown">走る</span>'
    )


def test_render_without_segments_returns_original():
    source = "犬[いぬ]が<ruby>走る<rt>はしる</rt></ruby>"
    assert AnnotatedText(source).render([]) == source


def test_ruby_element_span_is_not_split_across_tokens():
    # mecab would split 食べた into 食べ + た; a single ruby element must not
    # be split into two sibling spans.
    source = "<ruby>食べた<rt>たべた</rt></ruby>後で。"
    annotated = AnnotatedText(source)
    # simulate two tokens inside the ruby element
    segments = [(0, 2, "unknown"), (2, 3, "known"), (3, 4, "unknown")]
    rendered = annotated.render(segments)
    # whole ruby element got one span with the worst status (unknown)
    assert rendered.count("<ruby>") == 1
    assert '<span morph-status="unknown"><ruby>食べた<rt>たべた</rt></ruby></span>' in rendered


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def test_original_markup_survives_round_trip():
    """The text of every segment should always be a substring of the original."""
    samples = [
        "犬[いぬ]が公園[こうえん]を走る。",
        "<ruby>犬<rt>いぬ</rt></ruby>が<ruby>公園<rt>こうえん</rt></ruby>を走る。",
        "これは<span class='x'>テスト</span>です。",
        "[sound:x.mp3]猫が<ruby>好き<rt>すき</rt></ruby>だ。",
    ]
    for source in samples:
        annotated = AnnotatedText(source)
        for i in range(len(annotated.plain)):
            start, end = annotated.original_span(i, i + 1)
            assert annotated.original[start:end] != ""
            assert source.find(annotated.original[start:end]) != -1


def _strip_span_markup(html: str) -> str:
    html = re.sub(r'<span morph-status="(?:known|learning|unknown|undefined)">', "", html)
    return html.replace("</span>", "")


@pytest.mark.parametrize(
    "source",
    [
        "犬[いぬ]が公園[こうえん]を走る。",
        "<ruby>犬<rt>いぬ</rt></ruby>が<ruby>公園<rt>こうえん</rt></ruby>を走る。",
        "[sound:x.mp3]猫が<ruby>好き<rt>すき</rt></ruby>だ。",
        "私[わたし]は<ruby>昨日<rt>きのう</rt></ruby>学校へ行[い]った。",
        "食[た]べた。",
        "彼は[笑]ながら話した。",
        "取[と]って置[お]きなさい。",
    ],
)
def test_render_span_stripping_recovers_original(source):
    """Removing inserted spans must give back the original sentence exactly."""
    annotated = AnnotatedText(source)
    n = len(annotated.plain)
    # give every character a span; overlapping/merged ruby logic may collapse
    # some of them, but the result must still contain all original characters.
    rendered = annotated.render([(i, i + 1, "unknown") for i in range(n)])
    assert _strip_span_markup(rendered) == source


def _flatten_html(html: str) -> str:
    """Delete every span tag; text content must be unaffected by morph spans."""
    return re.sub(r"</?span[^>]*>", "", html)


def test_render_span_stripping_recovers_original_with_foreign_spans():
    source = "これは<span class='x'>テスト</span>です。"
    annotated = AnnotatedText(source)
    rendered = annotated.render([(i, i + 1, "unknown") for i in range(len(annotated.plain))])
    # inserting morph spans must not drop or duplicate any real text
    assert _flatten_html(rendered) == _flatten_html(source)
    # and the foreign markup is still present
    assert "<span class='x'>" in rendered
