"""[designed: owner #433/T136, continuing T93] Country-fitting presentation names only.

Authored T93 names are preferred. Other countries use families from their canonical squad,
not a claimed frequency ranking. Original records, explicit renames and saves remain untouched.
"""
from functools import lru_cache,wraps
from pathlib import Path
from goal2.game.pool_names import table,FIRST,COUNT


class NamesPolicy:
    def __init__(self,data):
        self.data=data;self._names={}

    def names(self,country):
        if type(country) is not int or not 1<=country<len(self.data.country_names):
            raise ValueError('A pool name needs a country1..128')
        if country in self._names:return self._names[country]
        entry=table().get(country)
        if entry is not None and entry[0]==self.data.country_names[country]:
            _,families,initials=entry
            names=tuple(f'{i} {f}' for i,f in zip(initials,families))
        else:
            families=[]
            reserved=set()
            for word in self.data.squad_20[country]:
                family=self.data.player_names[word]
                reserved.add(self.original_name(word))
                if family and not any(ord(c)<32 or ord(c)==127 for c in family) and family not in families:
                    families.append(family)
            names=[]
            for rotation in range(26):
                for index,family in enumerate(families):
                    initial=chr(65+(index+rotation+country)%26)
                    name=f'{initial} {family}'
                    if name not in reserved and name not in names:names.append(name)
                    if len(names)==COUNT:break
                if len(names)==COUNT:break
            names=tuple(names)
        if len(names)!=COUNT or len(set(names))!=COUNT:
            raise ValueError('The country does not provide eighty distinct pool display names')
        self._names[country]=names
        return names

    def original_name(self,word):
        return f'{self.data.player_initials[word]} {self.data.player_names[word]}'

    def resolver(self,state):
        from goal2.core import views
        mem=views.Memory(state);base=mem.far(views.PLAYERS)
        def name(word,original):
            if not FIRST<=word<len(self.data.player_names):return original
            # The guest's F2 rename takes precedence over the derived default.
            if original!=self.original_name(word):return original
            country=mem.byte(base+views.PLAYER_SIZE*word)
            if not 1<=country<len(self.data.country_names):return original
            if mem.country_name(country)!=self.data.country_names[country]:return original
            return self.names(country)[(word-FIRST)%COUNT]
        return name


@lru_cache(maxsize=4)
def _policy(path,modified,size):
    from goal2.data import load
    return NamesPolicy(load(Path(path).read_bytes()))


def resolver_for(state,data_path):
    if data_path is None:return None
    path=Path(data_path).resolve()
    try:
        info=path.stat();policy=_policy(str(path),info.st_mtime_ns,info.st_size)
    except (OSError,ValueError):
        # Imported/custom snapshots keep their own names when canonical data cannot identify them.
        return None
    return policy.resolver(state)


def presented(method):
    """Scope a name resolver to one pure model-view call, restored even on an exception."""
    @wraps(method)
    def view(self,*args,**kwargs):
        from goal2.core import views
        resolver=resolver_for(self.state,self.data_path)
        if resolver is None:return method(self,*args,**kwargs)
        with views.display_player_names(resolver):return method(self,*args,**kwargs)
    return view
