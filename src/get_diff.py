from aqt import mw


def get_cards_by_tag(tag):
    if mw.col != None:
        return mw.col.find_cards(f"tag:{tag}")
    return None
