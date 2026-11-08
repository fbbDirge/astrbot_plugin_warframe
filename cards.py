"""Keep text for tests/internal diagnostics; send structured cards to chat."""

class Card(str):
    def __new__(cls, text, *, title='', columns=(), rows=(), footer='', artwork=('', ''), chart=None):
        obj = super().__new__(cls, text)
        obj.blocks = []
        obj.kind = ""
        obj.title = title
        obj.columns = columns
        obj.rows = rows
        obj.footer = footer
        obj.chart = chart
        obj.artwork = artwork
        obj.artwork_path = None
        obj.artwork_overlay_path = None
        return obj


class IconText(str):
    """A display cell with an optional bundled icon; remains ordinary text to callers."""
    def __new__(cls, text, icon=''):
        obj = super().__new__(cls, text)
        obj.icon = icon
        return obj
