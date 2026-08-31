# import the main window object (mw) from aqt
from aqt import mw

# import all of the Qt GUI library
from aqt.qt import QAction, qconnect

# import the "show info" tool from utils.py
from aqt.utils import showInfo, tooltip

# We're going to add a menu item below. First we want to create a function to
# be called when the menu item is activated.
from .src.get_diff import (
    get_cards_by_tag,
    get_field_difficulties,
    get_field_values_from_deck,
    get_mature_words,
    get_sentence_difficulty,
    get_young_words,
)

# Initialize the controller


def test_function() -> None:
    """Show card count in current collection."""
    if mw is not None and mw.col is not None:
        word_list = get_field_values_from_deck("Mining", "Word")
        young_words = get_young_words("Mining", "Word")
        mature_words = get_mature_words("Mining", "Word")
        difficulties = get_field_difficulties(
            "Mining", "Sentence", mature_words, young_words
        )
        showInfo(f"Words: {difficulties}")
    else:
        tooltip("Collection not available")


def show_mining_stats():
    if mw is None or mw.col is None:
        tooltip("Collection not available")
        return

    col = mw.col
    young_ids = col.find_cards('deck:"Mining" is:review prop:ivl<21')
    mature_ids = col.find_cards('deck:"Mining" is:review prop:ivl>=21')

    showInfo(
        f"Deck 'Mining' stats:\n"
        f"Young cards: {len(young_ids)}\n"
        f"Mature cards: {len(mature_ids)}\n"
        f"Total reviews: {len(young_ids) + len(mature_ids)}"
    )


# create a new menu item, "test"
action = QAction("test", mw)
action2 = QAction("test2", mw)
# set it to call testFunction when it's clicked
qconnect(action.triggered, test_function)
qconnect(action2.triggered, show_mining_stats)
# and add it to the tools menu
mw.form.menuTools.addAction(action)
mw.form.menuTools.addAction(action2)
