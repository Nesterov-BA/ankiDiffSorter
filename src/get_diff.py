import re

from aqt import mw

from . import mecab_controller
from .furigana import AnnotatedText
from .mecab_controller.basic_types import PartOfSpeech


def get_cards_by_tag(tag):
    if mw.col != None:
        return mw.col.find_cards(f"tag:{tag}")
    return None


def get_field_values_from_deck(deck_name: str, field_name: str) -> list[str]:
    """
    Returns a list of values from the specified field for all notes of cards
    in the given deck. If a note doesn't have the field, an empty string is used.
    """

    # Get all card IDs in this deck
    #
    card_ids = get_deck(deck_name)

    values = get_field_from_ids(card_ids, field_name)
    return values


def get_deck(deck_name):
    if mw is None or mw.col is None:
        raise RuntimeError("Collection not available")

    col = mw.col
    deck = col.decks.by_name(deck_name)
    if deck is None:
        raise ValueError(f"Deck '{deck_name}' not found")

    deck_id = deck["id"]

    if col.db is None:
        return
    card_ids = col.db.list("SELECT id FROM cards WHERE did = ?", deck_id)
    return card_ids


def get_field_from_ids(card_ids, field_name):

    if mw is None or mw.col is None:
        raise RuntimeError("Collection not available")
    col = mw.col
    values = []
    for cid in card_ids:
        card = col.get_card(cid)
        note = card.note()
        # Retrieve field value, default to empty string if missing
        value = note[field_name] if field_name in note else ""
        values.append(value)
    return values


def get_notes_from_ids(card_ids):
    if mw is None or mw.col is None:
        raise RuntimeError("Collection not available")
    col = mw.col
    notes = []
    for cid in card_ids:
        card = col.get_card(cid)
        notes.append(card.note())
    return notes


def get_notes_from_deck(deck_name):
    ids = get_deck(deck_name)
    return get_notes_from_ids(ids)


def get_new_card_from_deck(deck_name):
    if mw is None or mw.col is None:
        raise RuntimeError("Collection not available")
    col = mw.col
    new_ids = col.find_cards(f'deck:"{deck_name}" is:new')
    cards = []
    for cid in new_ids:
        card = col.get_card(cid)
        cards.append(card)
    return cards


def get_words(sentence, mecab):
    tokens = get_tokens(sentence, mecab)
    words = [t.word for t in tokens]
    return words


def _plain_tokens(sentence, mecab):
    """Tokenize a (possibly annotated) sentence on its plain view."""
    annotated = AnnotatedText(sentence)
    tokens = list(mecab.translate(annotated.plain))
    return annotated, tokens


def _token_spans(annotated: AnnotatedText, tokens) -> list[tuple[int, int] | None]:
    """
    Map every token back onto plain-text character coordinates.

    Whitespace is not part of tokens (mecab never emits it) but it is present
    in ``plain``, so the walker skips it while aligning token words.
    """
    plain = annotated.plain
    spans: list[tuple[int, int] | None] = []
    pos = 0
    for token in tokens:
        word = token.word
        if not word:
            spans.append(None)
            continue
        start = plain.find(word, pos)
        if start == -1:
            spans.append(None)
            continue
        spans.append((start, start + len(word)))
        pos = start + len(word)
    return spans


def _analyze(sentence, mature_list, young_list, mecab):
    """Tokenize (furigana-aware), classify and highlight in one pass."""
    annotated, tokens = _plain_tokens(sentence, mecab)
    spans = _token_spans(annotated, tokens)
    difficulty = 0
    segments = []
    headwords = []
    for token, span in zip(tokens, spans):
        headword = token.headword
        headwords.append(headword)
        if headword in mature_list:
            status = "known"
        elif headword in young_list:
            difficulty += 1000
            status = "learning"
        elif token.part_of_speech is not PartOfSpeech.symbol and is_japanese(token.word):
            difficulty += 1000000
            status = "unknown"
        else:
            status = None
        if status is not None and span is not None:
            segments.append((span[0], span[1], status))
    formatted_sentence = annotated.render(segments)
    return difficulty, formatted_sentence, ", ".join(headwords)


def get_sentence_difficulty(sentence, mature_list, young_list, mecab):
    """
    Returns integer sentence difficulty based on a list of known words
    and a highlighted copy of the sentence.

    Furigana annotations (``word[reading]`` and ``<ruby>`` elements) are
    removed before tokenization, so readings never inflate the difficulty;
    the highlighted copy keeps the original markup and places each word's
    reading inside the same morph-status span.
    """
    difficulty, formatted_sentence, _ = _analyze(sentence, mature_list, young_list, mecab)
    return difficulty, formatted_sentence


def get_sentence_headwords(sentence, mecab) -> str:
    """Return the headwords of a sentence joined by commas (plain view)."""
    annotated, tokens = _plain_tokens(sentence, mecab)
    return ", ".join(token.headword for token in tokens)


def create_span(text, morph_status):
    result = f'<span morph-status="{morph_status}">{text}</span>'
    return result


def get_field_difficulties(deck, field, mature_list, young_list):
    mecab = mecab_controller.MecabController()
    values = get_field_values_from_deck(deck_name=deck, field_name=field)
    difficulties = []
    formatted_sentences = []
    for sentence in values:
        difficuty, formatted_sentence = get_sentence_difficulty(
            sentence, mature_list, young_list, mecab
        )
        difficulties.append(difficuty)
        formatted_sentences.append(formatted_sentence)
    return difficulties, formatted_sentences


def calculate_notes_difficulties(deck, field, mature_list, young_list):
    mecab = mecab_controller.MecabController()
    if mw is None or mw.col is None:
        raise RuntimeError("Collection not available")
    # notes = get_notes_from_deck(deck)
    cards = get_new_card_from_deck(deck)
    total = len(cards)
    mw.progress.start(
        label=f"Calculating difficulties for {len(cards)} new cards…",
        max=len(cards),
        immediate=True,  # show immediately
    )
    mw.app.processEvents()
    idx = 0
    for card in cards:
        idx += 1
        note = card.note()
        sentence = note[field]
        difficulty, formatted_sentence, all_headwords = _analyze(
            sentence, mature_list, young_list, mecab
        )
        note["Comment"] = ""
        note["am-highlighted"] = formatted_sentence
        note["am-all-morphs"] = all_headwords
        card.due = difficulty
        card.flush()  # save the change
        mw.col.update_note(note)
        mw.progress.update(
            label=f"Calculating card difficulties {idx}/{total}…", value=idx
        )
        mw.app.processEvents()
    mw.progress.finish()


def get_young_words(deck_name, field_name):
    if mw is None or mw.col is None:
        return

    col = mw.col
    young_ids = col.find_cards(f'deck:"{deck_name}" is:review prop:ivl<21')
    return get_field_from_ids(young_ids, field_name)


def get_tokens(sentence, mecab):
    annotated = AnnotatedText(sentence)
    tokens = mecab.translate(annotated.plain)
    return tokens


def get_mature_words(deck_name, field_name):
    if mw is None or mw.col is None:
        return

    col = mw.col
    mature_ids = col.find_cards(f'deck:"{deck_name}" is:review prop:ivl>=21')
    return get_field_from_ids(mature_ids, field_name)


def is_japanese(text):
    # Japanese Unicode ranges:
    # Hiragana: U+3040 - U+309F
    # Katakana: U+30A0 - U+30FF
    # Kanji (CJK Unified Ideographs): U+4E00 - U+9FAF
    japanese_pattern = re.compile(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+")
    return bool(japanese_pattern.search(text))
