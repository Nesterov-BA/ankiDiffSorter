# import the main window object (mw) from aqt
from aqt import mw

# import all of the Qt GUI library
from aqt.qt import QAction, qconnect

# import the "show info" tool from utils.py
from aqt.utils import showInfo, tooltip

# We're going to add a menu item below. First we want to create a function to
# be called when the menu item is activated.


def test_function() -> None:
    """Show card count in current collection."""
    if mw is not None and mw.col is not None:
        card_count = mw.col.card_count()
        showInfo(f"Card count: {card_count}")
    else:
        tooltip("Collection not available")


# create a new menu item, "test"
action = QAction("test", mw)
# set it to call testFunction when it's clicked
qconnect(action.triggered, test_function)
# and add it to the tools menu
mw.form.menuTools.addAction(action)
