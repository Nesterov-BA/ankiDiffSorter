# import the main window object (mw) from aqt
from aqt import mw

# import all of the Qt GUI library
from aqt.qt import QAction, qconnect

# import the "show info" tool from utils.py
from aqt.utils import showInfo, tooltip

# We're going to add a menu item below. First we want to create a function to
# be called when the menu item is activated.
from .src.get_diff import (
    calculate_notes_difficulties,
    get_mature_words,
    get_young_words,
)

# Initialize the controller


def get_config():
    """Return the add‑on configuration dict with fallback defaults."""
    config = mw.addonManager.getConfig(__name__)
    if config is None:
        # Create default config file if it doesn't exist
        default_config = {
            "deck_name": "Mining",
            "word_field": "Word",
            "sentence_field": "Sentence",
        }
        mw.addonManager.writeConfig(__name__, default_config)
        return default_config
    return config


def test_function() -> None:
    """Show card count in current collection."""
    if mw is not None and mw.col is not None:
        cfg = get_config()
        deck_name = cfg["deck_name"]
        word_field = cfg["word_field"]
        sentence_field = cfg["sentence_field"]

        young_words = get_young_words(deck_name, word_field)
        mature_words = get_mature_words(deck_name, word_field)
        calculate_notes_difficulties(
            deck_name, sentence_field, mature_list=mature_words, young_list=young_words
        )
        showInfo(f"Finished recalc!")
    else:
        tooltip("Collection not available")


# create a new menu item, "test"
action = QAction("Difficulty based reorder", mw)
# set it to call testFunction when it's clicked
qconnect(action.triggered, test_function)
# and add it to the tools menu
mw.form.menuTools.addAction(action)
