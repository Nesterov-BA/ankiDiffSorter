from aqt import mw

from . import mecab_controller


def get_cards_by_tag(tag):
    if mw.col != None:
        return mw.col.find_cards(f"tag:{tag}")
    return None


def get_field_values_from_deck(deck_name: str, field_name: str) -> list[str]:
    """
    Returns a list of values from the specified field for all notes of cards
    in the given deck. If a note doesn't have the field, an empty string is used.
    """
    if mw is None or mw.col is None:
        raise RuntimeError("Collection not available")

    col = mw.col
    deck = col.decks.by_name(deck_name)
    if deck is None:
        raise ValueError(f"Deck '{deck_name}' not found")

    deck_id = deck["id"]

    # Get all card IDs in this deck
    card_ids = col.db.list("SELECT id FROM cards WHERE did = ?", deck_id)

    values = get_field_from_ids(card_ids, field_name)
    return values


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


def get_words(sentence, mecab):
    tokens = mecab.translate(sentence)
    words = [t.word for t in tokens]
    return words


def get_sentence_difficulty(sentence, mature_list, young_list, mecab):
    """
    Returns integer sentence difficulty based on a list of known words
    Args:
        sentence ():
        word_list ():
        mecab ():

    Returns:

    """
    sentence_words = get_words(sentence, mecab)
    difficulty = 0
    for word in sentence_words:
        if word in mature_list:
            pass
        elif word in young_list:
            difficulty += 1000
        else:
            difficulty += 1000000
    return difficulty


def get_field_difficulties(deck, field, mature_list, young_list):
    mecab = mecab_controller.MecabController()
    values = get_field_values_from_deck(deck_name=deck, field_name=field)
    difficulties = []
    for sentence in values:
        difficulties.append(
            get_sentence_difficulty(sentence, mature_list, young_list, mecab)
        )
    return difficulties


def get_young_words(deck_name, field_name):
    if mw is None or mw.col is None:
        return

    col = mw.col
    young_ids = col.find_cards(f'deck:"{deck_name}" is:review prop:ivl<21')
    return get_field_from_ids(young_ids, field_name)


def get_mature_words(deck_name, field_name):
    if mw is None or mw.col is None:
        return

    col = mw.col
    mature_ids = col.find_cards(f'deck:"{deck_name}" is:review prop:ivl<21')
    return get_field_from_ids(mature_ids, field_name)
