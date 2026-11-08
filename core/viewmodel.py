"""Typed display data travels with the text used for diagnostics and logs."""
class DataLines(list):
    def __init__(self,lines=(),*,domain='',records=(),meta=None):
        super().__init__(lines)
        self.domain=domain
        self.records=list(records)
        self.meta=meta or {}
    def with_lines(self,lines):
        return DataLines(lines,domain=self.domain,records=self.records,meta=self.meta)
