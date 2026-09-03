# ankiDiffSorter
Anki addon to sort card based on the difficulty of a field

## What it does
For every new card in the configured deck it:

1. tokenizes the `Sentence` field with mecab,
2. computes a numeric difficulty from the sentence's words (known /
   learning / unknown),
3. writes the difficulty into the card's due position (so the queue is
   sorted easy → hard),
4. refreshes the Migaku-style fields `am-highlighted` (sentence with
   per-word `<span morph-status="...">`) and `am-all-morphs`
   (comma-joined headwords).

## Furigana support
The `Sentence` field may contain furigana in either of two common formats:

* square-bracket readings: `漢字[かんじ]`, okurigana may stay outside the
  brackets (`食[た]べた`);
* ruby elements: `<ruby>漢字<rt>かんじ</rt></ruby>`.

Readings are removed before tokenization, so a reading is never counted as
an extra unknown word and the difficulty of an annotated sentence equals the
difficulty of the same plain sentence.  The annotated sentence itself is
never modified; `am-highlighted` keeps the original markup 1:1 and each
reading stays inside the span of its word.

## Tests
Run with pytest (mecab tests are skipped automatically if the bundled mecab
cannot run):

```bash
python -m pytest tests
```
(The test configuration lives in `tests/pytest.ini`, so the tests work when
invoked as above or from inside the `tests/` directory; running bare `pytest`
from the repo root is not supported because the repo root itself is an Anki
add-on package.)
