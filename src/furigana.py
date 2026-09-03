"""
Helpers that make sentence analysis and highlighting furigana-aware.

Two annotation formats are understood:

* square-bracket readings: ``word[reading]`` (e.g. ``犬[いぬ]``), including
  okurigana kept outside the brackets (e.g. ``食[た]べた``);
* ruby elements: ``<ruby>word<rt>reading</rt></ruby>`` (and variants with
  ``<rb>`` / ``<rp>``).

The add-on needs two different views of the same note text:

1. ``plain`` -- the sentence with every reading removed and every tag
   stripped (whitespace is kept, because mecab's tokenization is
   whitespace-sensitive).  This is the text that should be fed to mecab so
   readings are not counted as extra unknown words and markup never reaches
   mecab.
2. highlighted HTML -- the *original* sentence (markup preserved 1:1) with
   ``<span morph-status="...">`` inserted around each word, keeping the
   word's reading inside the same span.

This module deliberately does not depend on anki or mecab_controller.
"""

from __future__ import annotations

import re

# Hiragana + katakana ranges used to decide whether text inside [] is a reading.
_HIRAGANA = "\u3040-\u309F"
_KATAKANA = "\u30A0-\u30FF"
_KANA_ONLY_RE = re.compile(rf"^[{_HIRAGANA}{_KATAKANA}ー・]+$")

_ANY_TAG_RE = re.compile(r"<[^<>]*>")
_SOUND_RE = re.compile(r"\[sound:[^\]]*\]", re.IGNORECASE)
_TYPE_RE = re.compile(r"\[\[type:[^\]]*\]\]", re.IGNORECASE)


def is_kana_only(text: str) -> bool:
    """True when *text* could be a reading annotation (only kana etc.)."""
    return bool(text) and bool(_KANA_ONLY_RE.match(text))


def _analysis_char(char: str) -> str:
    """Mirror mecab's escape_text() so our plain view matches what mecab sees."""
    if char == "\n":
        return " "
    if char == "\uff5e":  # ～ is turned into ~ by escape_text
        return "~"
    return char


class _RubyGroup:
    """A ruby element; keeps original and plain-text coordinates."""

    __slots__ = ("orig_start", "orig_end", "plain_start", "plain_end")

    def __init__(self, orig_start: int, orig_end: int, plain_start: int, plain_end: int) -> None:
        self.orig_start = orig_start
        self.orig_end = orig_end
        self.plain_start = plain_start
        self.plain_end = plain_end


class AnnotatedText:
    """
    A sentence parsed into plain text plus enough information to rebuild the
    original sentence with per-word spans.

    ``plain`` chars and their metadata are kept in parallel lists.  Readings
    and markup are absent from ``plain``; whitespace is kept.
    """

    def __init__(self, text: str) -> None:
        self.original = text
        plain_chars: list[str] = []
        # original index of each plain char
        orig_idx: list[int] = []
        # original index *after* the trailing text (e.g. [reading]) that
        # belongs to this plain char
        end_after: list[int] = []
        # ruby element each plain char belongs to (or None)
        ruby_of: list[_RubyGroup | None] = []
        ruby_groups: list[_RubyGroup] = []

        i, n = 0, len(text)

        def push(char: str, orig: int) -> None:
            plain_chars.append(_analysis_char(char))
            orig_idx.append(orig)
            end_after.append(orig + 1)
            ruby_of.append(None)

        def scan_ruby_base(inner_start: int, inner_end: int) -> int:
            """Append base chars found inside a ruby element. Return count."""
            pos = inner_start
            start_plain = len(plain_chars)
            while pos < inner_end:
                if text[pos] == "<":
                    tag = _ANY_TAG_RE.match(text, pos)
                    if tag is None:
                        pos += 1
                        continue
                    name = re.sub(r"[^A-Za-z]", "", tag.group(0)).lower()
                    if name in ("rt", "rp"):
                        close = re.compile(rf"</{name}\s*>", re.IGNORECASE).search(text, tag.end())
                        if close is None or close.end() > inner_end:
                            # unclosed reading element: everything up to the
                            # end of the ruby element is reading text
                            pos = inner_end
                            continue
                        pos = close.end()
                        continue
                    # other tags (rb, b, span, ...): drop the markup only
                    pos = tag.end()
                    continue
                if text[pos].isspace():
                    push(" ", pos)
                    pos += 1
                    continue
                push(text[pos], pos)
                pos += 1
            return start_plain

        while i < n:
            ch = text[i]

            # ruby element: drop rt/rp contents, keep base chars, remember the
            # original element span so a whole word can be wrapped together.
            ruby_open = re.match(r"<ruby\b[^>]*>", text[i:], re.IGNORECASE)
            if ruby_open is not None:
                elem_start = i
                open_end = i + ruby_open.end()
                close = re.search(r"</ruby\s*>", text[open_end:], re.IGNORECASE)
                if close is not None:
                    inner_end = open_end + close.start()
                    elem_end = open_end + close.end()
                else:
                    # unclosed ruby: treat the rest of the string as the element
                    inner_end = n
                    elem_end = n
                start_plain = len(plain_chars)
                scan_ruby_base(open_end, inner_end)
                group = _RubyGroup(elem_start, elem_end, start_plain, len(plain_chars))
                for k in range(start_plain, len(plain_chars)):
                    ruby_of[k] = group
                if start_plain < len(plain_chars):
                    ruby_groups.append(group)
                i = elem_end
                continue

            # [[type:...]] and [sound:...] placeholders never reach mecab.
            m = _TYPE_RE.match(text, i) or _SOUND_RE.match(text, i)
            if m is not None:
                i = m.end()
                continue

            # square-bracket reading directly following a base char, e.g.
            # 犬[いぬ], 食[た]べた. Content must look like a reading.
            if ch == "[":
                close = text.find("]", i + 1)
                if close != -1:
                    content = text[i + 1 : close]
                    if plain_chars and orig_idx[-1] + 1 == i and is_kana_only(content):
                        # reading belongs to the previous plain char
                        end_after[-1] = close + 1
                        i = close + 1
                        continue

            # any other html tag: drop the markup, keep the text (mecab's
            # escape_text strips tags too).
            if ch == "<":
                tag = _ANY_TAG_RE.match(text, i)
                if tag is not None:
                    i = tag.end()
                    continue

            if ch.isspace():
                push(" ", i)
                i += 1
                continue

            push(ch, i)
            i += 1

        self.plain = "".join(plain_chars)
        self._orig_idx = orig_idx
        self._end_after = end_after
        self._ruby_of = ruby_of
        self.ruby_groups = ruby_groups

    def original_span(self, plain_start: int, plain_end: int) -> tuple[int, int]:
        """
        Return the original-text span for plain chars [plain_start, plain_end).

        Extends the end past trailing readings that belong to the last char and
        past a ruby element that encloses the last char; extends the beginning
        to the start of a ruby element that encloses the first char.
        """
        if plain_start >= plain_end:
            return (0, 0)
        start = self._orig_idx[plain_start]
        end = max(self._end_after[plain_end - 1], self._orig_idx[plain_end - 1] + 1)
        first_group = self._ruby_of[plain_start]
        if first_group is not None and first_group.plain_start == plain_start:
            start = min(start, first_group.orig_start)
        last_group = self._ruby_of[plain_end - 1]
        if last_group is not None and last_group.plain_end == plain_end:
            end = max(end, last_group.orig_end)
        return (start, end)

    def render(self, segments: list[tuple[int, int, str | None]]) -> str:
        """
        Build the highlighted HTML of the original sentence.

        ``segments``: (plain_start, plain_end, status) sorted by plain
        position; status None means the text is emitted without a span.
        """
        if not segments:
            return self.original
        return _insert_spans(self.original, _resolve_overlaps(self, segments))


def strip_furigana(text: str) -> str:
    """Return *text* with readings and markup removed (plain view)."""
    return AnnotatedText(text).plain


_STATUS_RANK = {"known": 0, "learning": 1, "unknown": 2}


def _worst_status(segments: list[tuple[int, int, str | None]]) -> str | None:
    ranked = [seg for seg in segments if seg[2] is not None]
    if not ranked:
        return None
    return max(ranked, key=lambda seg: _STATUS_RANK.get(seg[2], 0))[2]


def _resolve_overlaps(
    annotated: AnnotatedText, segments: list[tuple[int, int, str | None]]
) -> list[tuple[int, int, str | None]]:
    """
    Convert plain segments to original intervals.

    A ruby element is atomic: its reading cannot be split across separate word
    spans.  If a ruby element is touched by several plain segments (mecab
    split the base into multiple tokens), they are merged into one segment
    spanning the whole element, using the "worst" status among them.  A
    segment that only partially covers an element (token boundary inside the
    ruby base) is likewise extended to the whole element so that generated
    spans never cut through ruby markup.
    """
    segs = sorted((s for s in segments if s[2] is not None), key=lambda s: (s[0], s[1]))

    # 1) merge segments that share a ruby element
    for group in annotated.ruby_groups:
        if group.plain_start >= group.plain_end:
            continue
        intersecting_idx = [
            idx
            for idx, (start, end, _status) in enumerate(segs)
            if start < group.plain_end and end > group.plain_start
        ]
        if len(intersecting_idx) < 2:
            # A single intersecting segment may still start before or end
            # after the element while its counterpart lies inside; verify that
            # the segment really covers the whole element.
            for idx in intersecting_idx:
                start, end, _ = segs[idx]
                if start > group.plain_start or end < group.plain_end:
                    intersecting_idx = [idx]
                    break
        if len(intersecting_idx) >= 1:
            low = min(segs[idx][0] for idx in intersecting_idx)
            high = max(segs[idx][1] for idx in intersecting_idx)
            merged = (
                min(low, group.plain_start),
                max(high, group.plain_end),
                _worst_status([segs[idx] for idx in intersecting_idx]),
            )
            for idx in sorted(intersecting_idx, reverse=True):
                del segs[idx]
            segs.append(merged)
            segs.sort(key=lambda s: (s[0], s[1]))

    # 2) convert to original-text intervals
    intervals: list[tuple[int, int, str | None]] = []
    for start, end, status in segs:
        intervals.append((*annotated.original_span(start, end), status))
    intervals.sort(key=lambda x: (x[0], x[1]))
    return intervals


def _insert_spans(original: str, intervals: list[tuple[int, int, str | None]]) -> str:
    out: list[str] = []
    cursor = 0
    for start, end, status in intervals:
        if end <= start:
            continue
        start = max(start, cursor)
        if start >= len(original):
            break
        out.append(original[cursor:start])
        text = original[start:end]
        if status is not None:
            out.append(f'<span morph-status="{status}">{text}</span>')
        else:
            out.append(text)
        cursor = end
    out.append(original[cursor:])
    return "".join(out)
