"""[designed: T170au/#874] Shared projection of the original's three stories."""

from goal2.engine.original_match.news import NewsPageMemory, news_pages
from goal2.game.season_wire import validate_news_page

# [confirmed: F032/E038] Masthead, inclusive story rows and inclusive columns.
BULLETIN_PANELS = {'left': (8, 10, 18, 3, 22), 'middle': (6, 8, 20, 29, 50),
                   'right': (8, 10, 18, 57, 76)}
FILLER = set('≡░ ')


def bulletin_columns(read):
    """Project story text from a reader of inclusive ranges of decoded cells."""
    result = {}
    for name, (head, first, last, left, right) in BULLETIN_PANELS.items():
        lines = [read(row, left, right).strip() for row in range(first, last + 1)]
        result[name] = {'masthead': read(head, left, right).strip(),
                        'lines': [text for text in lines if text and not set(text) <= FILLER]}
    return result


def native_bulletins(*observations):
    """Return detached S05 pages in the order the native observations delivered them."""
    pages = []
    for observation in observations:
        if not isinstance(observation, dict) or type(observation.get('news_pages')) is not tuple:
            raise ValueError('Native bulletins require the verified news sequence.')
        for source in observation['news_pages']:
            validate_news_page(source)
            lines, = news_pages(NewsPageMemory(**source))
            pages.append(bulletin_columns(lambda row, left, right: lines[row][left:right + 1]))
    return pages
