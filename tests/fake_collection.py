"""In-memory stand-ins for Anki objects used by the add-on."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


class FakeNote:
    def __init__(self, fields: dict[str, str]):
        self._fields = dict(fields)

    def __contains__(self, name: str) -> bool:
        return name in self._fields

    def __getitem__(self, name: str) -> str:
        return self._fields[name]

    def __setitem__(self, name: str, value: str) -> None:
        self._fields[name] = value


@dataclass
class FakeCard:
    note_id: int
    deck_id: int
    _note: FakeNote
    is_new: bool
    interval: int = 0
    due: int = 0
    flushed: bool = False

    def note(self) -> FakeNote:
        return self._note

    @property
    def note_fields(self) -> FakeNote:
        return self._note

    def flush(self) -> None:
        self.flushed = True


class FakeDeckManager:
    def __init__(self) -> None:
        self._decks = {}

    def add_deck(self, name: str, deck_id: int) -> None:
        self._decks[name] = {"id": deck_id}

    def by_name(self, name: str):
        return self._decks.get(name)


class FakeDb:
    def __init__(self, owner: "FakeCollection") -> None:
        self._owner = owner

    def list(self, sql: str, *args):
        if "SELECT id FROM cards WHERE did = ?" in sql:
            deck_id = args[0]
            return [c.id for c in self._owner.cards if c.deck_id == deck_id]
        raise NotImplementedError(sql)


class FakeCollection:
    def __init__(self) -> None:
        self.decks = FakeDeckManager()
        self.cards: list[FakeCard] = []
        self.updated_notes: list[FakeNote] = []
        self.db = FakeDb(self)
        self._next_id = 1

    def _new_card_id(self) -> int:
        cid = self._next_id
        self._next_id += 1
        return cid

    def add_note(self, deck_id: int, fields: dict[str, str], *, is_new: bool, interval: int = 0) -> FakeCard:
        note_id = self._next_id
        card = FakeCard(
            note_id=note_id,
            deck_id=deck_id,
            _note=FakeNote(fields),
            is_new=is_new,
            interval=interval,
        )
        card.id = self._new_card_id()
        card.note_id = note_id
        self.cards.append(card)
        return card

    def get_card(self, cid: int) -> FakeCard:
        for card in self.cards:
            if getattr(card, "id", None) == cid:
                return card
        raise KeyError(cid)

    def find_cards(self, query: str):
        ids = []
        new_only = "is:new" in query
        review_only = "is:review" in query
        for card in self.cards:
            if new_only and not card.is_new:
                continue
            if review_only and card.is_new:
                continue
            m = re.search(r"prop:ivl\s*(<=|>=|<|>)\s*(\d+)", query)
            if review_only and m:
                op, val = m.group(1), int(m.group(2))
                ok = {
                    "<": card.interval < val,
                    ">": card.interval > val,
                    "<=": card.interval <= val,
                    ">=": card.interval >= val,
                }[op]
                if not ok:
                    continue
            ids.append(getattr(card, "id"))
        return ids

    def update_note(self, note: FakeNote) -> None:
        self.updated_notes.append(note)


class FakeProgress:
    def __init__(self) -> None:
        self.calls = []

    def start(self, **kwargs) -> None:
        self.calls.append(("start", kwargs))

    def update(self, **kwargs) -> None:
        self.calls.append(("update", kwargs))

    def finish(self) -> None:
        self.calls.append(("finish", {}))


class FakeApp:
    def processEvents(self) -> None:  # noqa: N802
        pass


class FakeMw:
    def __init__(self) -> None:
        self.col = FakeCollection()
        self.progress = FakeProgress()
        self.app = FakeApp()
