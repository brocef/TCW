"""A `RecordsReader` that answers from tables, for the gate and advance tests."""

from tcw.work.gates import ABSENT, REMOVED


class FakeReader:
    """Anything not listed is absent, or, for a removal, removed."""

    def __init__(self, capabilities=None, removals=None, terms=None):
        self.capabilities = capabilities or {}
        self.removals = removals or {}
        self.terms = terms or {}

    def capability(self, path):
        return self.capabilities.get(path, ABSENT)

    def removal(self, path):
        return self.removals.get(path, REMOVED)

    def term(self, term):
        return self.terms.get(term, ABSENT)
