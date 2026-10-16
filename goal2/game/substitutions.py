"""[designed: owner BM-7, T47] Unlimited friendly/five other, no re-entry.
[derived: proposed F027/F029 at0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb]
Managed swaps persist; source position bytes are not copied.
"""
import copy


def plan(eleven, bench, available, captain, *, kind=1, removed=()):
    """[designed] Explicit JSON-safe UI plan; order and full IDs retained."""
    return {'eleven':list(eleven),'bench':list(bench),'available':list(available),
            'captain':captain,'kind':kind,'removed':list(removed),'changes':[]}


def swap(current, outgoing, incoming):
    """[designed] Pure validation, used by both UI plan and live engine adapter."""
    if (type(outgoing) is not int or type(incoming) is not int
            or outgoing not in current['eleven'] or incoming not in current['bench']):
        raise ValueError('Choose one current starter and one bench player')
    if incoming in current['removed']:
        raise ValueError('A substituted player cannot re-enter')
    if incoming not in current['available']:
        raise ValueError('Incoming player is unavailable')
    if current['kind']!=1 and len(current['changes'])>=5:
        raise ValueError('Five substitutions already used')
    candidate=copy.deepcopy(current)
    candidate['eleven'][candidate['eleven'].index(outgoing)]=incoming
    candidate['bench'][candidate['bench'].index(incoming)]=outgoing
    candidate['removed'].append(outgoing);candidate['changes'].append([outgoing,incoming])
    if candidate['captain']==outgoing:candidate['captain']=incoming
    return candidate
