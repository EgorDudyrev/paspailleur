from collections import OrderedDict
from collections.abc import Iterator

from paspailleur.pattern_structures.pattern_structure import PatternStructure
from paspailleur.pattern_structures.pattern import Pattern
from paspailleur.pattern_structures import built_in_patterns as bip

from bitarray import frozenbitarray as fbarray


def test_init():
    ps = PatternStructure()

    ptrn = ps.PatternType({1, 2, 3})
    assert type(ptrn) == Pattern
    assert ptrn.value == {1, 2, 3}


def test_fit():
    patterns = [Pattern(frozenset({1, 2, 3})), Pattern(frozenset({0, 4})), Pattern(frozenset({1, 2, 4}))]
    context = {'a': patterns[0], 'b': patterns[1], 'c': patterns[2]}

    ps = PatternStructure()
    ps.fit(context)
    assert ps._object_names == ['a', 'b', 'c']
    object_irreducibles = {patterns[0]: fbarray('100'), patterns[1]: fbarray('010'), patterns[2]: fbarray('001')}
    assert ps._object_irreducibles == object_irreducibles
    assert ps._atomic_patterns is None

    class APattern(Pattern):  # short for atomised pattern
        @property
        def atomic_patterns(self):
            return {self.__class__(frozenset([v])) for v in self.value}

    patterns = [APattern(p.value) for p in patterns]
    context = {'a': patterns[0], 'b': patterns[1], 'c': patterns[2]}
    ps.fit(context)
    assert ps._atomic_patterns is not None


def test_extent():
    patterns = [Pattern(frozenset({1, 2, 3})), Pattern(frozenset({0, 4})), Pattern(frozenset({1, 2, 4}))]
    context = {'a': patterns[0], 'b': patterns[1], 'c': patterns[2]}

    ps = PatternStructure()
    ps.fit(context)
    assert ps.extent(patterns[0]) == {'a'}
    assert ps.extent(patterns[1]) == {'b'}
    assert ps.extent(patterns[2]) == {'c'}
    assert ps.extent(Pattern(frozenset({4}))) == {'b', 'c'}
    assert ps.extent(Pattern(frozenset())) == {'a', 'b', 'c'}
    assert ps.extent(Pattern(frozenset({1, 2, 3, 4}))) == set()

    assert ps.extent(patterns[0], return_bitarray=True) == fbarray('100')
    assert ps.extent(patterns[1], return_bitarray=True) == fbarray('010')
    assert ps.extent(patterns[2], return_bitarray=True) == fbarray('001')
    assert ps.extent(Pattern(frozenset({4})), return_bitarray=True) == fbarray('011')
    assert ps.extent(Pattern(frozenset()), return_bitarray=True) == fbarray('111')
    assert ps.extent(Pattern(frozenset({1, 2, 3, 4})), return_bitarray=True) == fbarray('000')


def test_intent():
    patterns = [Pattern(frozenset({1, 2, 3})), Pattern(frozenset({0, 4})), Pattern(frozenset({1, 2, 4}))]
    context = dict(zip('abc', patterns))

    ps = PatternStructure()
    ps.fit(context)
    assert ps.intent({'a'}) == patterns[0]
    assert ps.intent(['b']) == patterns[1]
    assert ps.intent(fbarray('001')) == patterns[2]
    assert ps.intent({'a', 'b'}) == Pattern(frozenset())
    assert ps.intent({'a', 'c'}) == Pattern(frozenset({1, 2}))
    assert ps.intent({'b', 'c'}) == Pattern(frozenset({4}))
    assert ps.intent([]) == Pattern(frozenset({0, 1, 2, 3, 4}))

    context = {
        'Stewart Island': {'Hiking', 'Observing Nature', 'Sightseeing Flights'},
        'Fjordland NP': {'Hiking', 'Observing Nature', 'Sightseeing Flights'},
        'Invercargill': {'Hiking', 'Observing Nature', 'Sightseeing Flights'},
        'Milford Sound': {'Hiking', 'Observing Nature', 'Sightseeing Flights'},
        'MT. Aspiring NP': {'Hiking', 'Observing Nature', 'Sightseeing Flights'},
        'Te Anau': {'Hiking', 'Jet Boating', 'Observing Nature', 'Sightseeing Flights'},
        'Dunedin': {'Hiking', 'Observing Nature', 'Sightseeing Flights'},
        'Oamaru': {'Hiking', 'Observing Nature'},
        'Queenstown': {'Bungee Jumping', 'Hiking', 'Jet Boating', 'Parachute Gliding', 'Sightseeing Flights', 'Skiing',
                       'Wildwater Rafting'},
        'Wanaka': {'Bungee Jumping', 'Hiking', 'Jet Boating', 'Parachute Gliding', 'Sightseeing Flights',
                   'Skiing', 'Wildwater Rafting'},
        'Otago Peninsula': {'Hiking', 'Observing Nature'},
        'Haast': {'Hiking', 'Observing Nature'},
        'Catlins': {'Hiking', 'Observing Nature'}
    }
    context = {obj: Pattern(frozenset(descr)) for obj, descr in context.items()}

    ps.fit(context)
    assert ps.intent(set(context)) == Pattern(frozenset({'Hiking'}))
    intent = ps.intent({'Fjordland NP'})
    assert intent == Pattern(frozenset({'Hiking', 'Observing Nature', 'Sightseeing Flights'}))


def test_min_pattern():
    patterns = [Pattern(frozenset({1, 2, 3})), Pattern(frozenset({0, 4})), Pattern(frozenset({1, 2, 4}))]
    context = dict(zip('abc', patterns))

    ps = PatternStructure()
    ps.fit(context)
    assert ps.min_pattern == Pattern(frozenset())

    patterns = [Pattern(frozenset({1, 2, 3})), Pattern(frozenset({0, 1, 4})), Pattern(frozenset({1, 2, 4}))]
    context = dict(zip('abc', patterns))
    ps.fit(context)
    assert ps.min_pattern == Pattern(frozenset({1}))

    class BPattern(Pattern):  # short for bounded pattern
        @property
        def min_pattern(self):
            return self.__class__(frozenset())

    patterns = [BPattern(frozenset({1, 2, 3})), BPattern(frozenset({0, 1, 4})), BPattern(frozenset({1, 2, 4}))]
    context = dict(zip('abc', patterns))
    ps.fit(context)
    assert ps.min_pattern == BPattern(frozenset())


def test_max_pattern():
    patterns = [Pattern(frozenset({1, 2, 3})), Pattern(frozenset({0, 4})), Pattern(frozenset({1, 2, 4}))]
    context = dict(zip('abc', patterns))

    ps = PatternStructure()
    ps.fit(context)
    assert ps.max_pattern == Pattern(frozenset(range(5)))

    class BPattern(Pattern):  # short for bounded pattern
        @property
        def max_pattern(self):
            return self.__class__(frozenset(range(10)))

    patterns = [BPattern(frozenset({1, 2, 3})), BPattern(frozenset({0, 1, 4})), BPattern(frozenset({1, 2, 4}))]
    context = dict(zip('abc', patterns))
    ps.fit(context)
    assert ps.max_pattern == BPattern(frozenset(range(10)))


def test_iter_atomic_patterns():
    class APattern(Pattern):  # short for atomised pattern
        @property
        def atomic_patterns(self):
            return {self.__class__(frozenset([v])) for v in self.value}

    patterns = [APattern(frozenset({1, 2, 3})), APattern(frozenset({0, 4})), APattern(frozenset({1, 2, 4}))]
    atomic_patterns_true = OrderedDict([
        (APattern(frozenset({2})), fbarray('101')),  # supp: 2
        (APattern(frozenset({1})), fbarray('101')),  # supp: 2
        (APattern(frozenset({4})), fbarray('011')),  # supp: 2
        (APattern(frozenset({3})), fbarray('100')),  # supp: 1
        (APattern(frozenset({0})), fbarray('010')),  # supp: 1
    ])
    context = dict(zip('abc', patterns))

    ps = PatternStructure()
    ps.fit(context, compute_atomic_patterns=False)
    ps._atomic_patterns = atomic_patterns_true

    atomic_patterns = ps.iter_atomic_patterns(return_extents=False, return_bitarrays=False)
    assert isinstance(atomic_patterns, Iterator)
    assert list(atomic_patterns) == list(atomic_patterns_true.keys())

    atomic_patterns_true_verb = OrderedDict([(k, {'abc'[g] for g in ext_ba.search(True)})
                                             for k, ext_ba in atomic_patterns_true.items()])
    atomic_patterns = ps.iter_atomic_patterns(return_extents=True, return_bitarrays=False)
    assert isinstance(atomic_patterns, Iterator)
    assert list(atomic_patterns) == list(atomic_patterns_true_verb.items())

    atomic_patterns = ps.iter_atomic_patterns(return_extents=True, return_bitarrays=True)
    assert isinstance(atomic_patterns, Iterator)
    assert list(atomic_patterns) == list(atomic_patterns_true.items())


def test_atomic_patterns():
    class APattern(Pattern):  # short for atomised pattern
        @property
        def atomic_patterns(self):
            return {self.__class__(frozenset([v])) for v in self.value}

    patterns = [APattern(frozenset({1, 2, 3})), APattern(frozenset({0, 4})), APattern(frozenset({1, 2, 4}))]
    atomic_patterns_true = OrderedDict([
        (APattern(frozenset({2})), fbarray('101')),  # supp: 2
        (APattern(frozenset({1})), fbarray('101')),  # supp: 2
        (APattern(frozenset({4})), fbarray('011')),  # supp: 2
        (APattern(frozenset({3})), fbarray('100')),  # supp: 1
        (APattern(frozenset({0})), fbarray('010')),  # supp: 1
    ])
    context = dict(zip('abc', patterns))

    ps = PatternStructure()
    assert ps._atomic_patterns is None

    ps.fit(context, compute_atomic_patterns=False)
    ps.init_atomic_patterns()
    assert ps._atomic_patterns == atomic_patterns_true
    assert ps._atomic_patterns_order == [fbarray('0'*len(atomic_patterns_true))] * len(atomic_patterns_true)

    atomic_patterns_true_verb = OrderedDict([(k, {'abc'[g] for g in ext_ba.search(True)})
                                             for k, ext_ba in atomic_patterns_true.items()])
    assert ps.atomic_patterns == atomic_patterns_true_verb


def test_iter_premaximal_patterns():
    patterns = [Pattern(frozenset({1, 2, 3})), Pattern(frozenset({4})), Pattern(frozenset({1, 2, 4}))]
    context = dict(zip('abc', patterns))

    premaximal_true = [patterns[0], patterns[2]]
    premaximal_true_set = {patterns[0]: set('a'), patterns[2]: set('c')}
    premaximal_true_ba = {patterns[0]: fbarray('100'), patterns[2]: fbarray('001')}
    ps = PatternStructure()
    ps.fit(context)
    assert dict(ps.iter_premaximal_patterns()) == premaximal_true_set
    assert list(ps.iter_premaximal_patterns(return_extents=False)) == premaximal_true
    assert dict(ps.iter_premaximal_patterns(return_extents=True, return_bitarrays=True)) == premaximal_true_ba


def test_premaximal_patterns():
    patterns = [Pattern(frozenset({1, 2, 3})), Pattern(frozenset({4})), Pattern(frozenset({1, 2, 4}))]
    context = dict(zip('abc', patterns))

    premaximal_true = {patterns[0]: set('a'), patterns[2]: set('c')}

    ps = PatternStructure()
    ps.fit(context)
    assert ps.premaximal_patterns == premaximal_true


def test_builtin_atomic_patterns():
    ps = PatternStructure()

    patterns = [bip.ItemSetPattern({1, 2, 3}), bip.ItemSetPattern({0, 4}), bip.ItemSetPattern({1, 2, 4})]
    context = dict(zip('abc', patterns))
    atomic_patterns_true_verb = [
        ({2}, 'ac'),  # supp: 2
        ({1}, 'ac'),  # supp: 2
        ({4}, 'bc'),  # supp: 2
        ({3}, 'a'),  # supp: 1
        ({0}, 'b'),  # supp: 1
    ]
    atomic_patterns_true_verb = OrderedDict([(bip.ItemSetPattern(ptrn), set(ext))
                                             for ptrn, ext in atomic_patterns_true_verb])
    ps.fit(context)
    assert ps.atomic_patterns == atomic_patterns_true_verb

    atomic_patterns_order_true = {(2,): [], (1,): [], (4,): [], (3,): [], (0,): []}
    atomic_patterns_order_true = {bip.ItemSetPattern(k): {bip.ItemSetPattern(v) for v in vs}
                                  for k, vs in atomic_patterns_order_true.items()}
    assert ps.atomic_patterns_order == atomic_patterns_order_true

    patterns = [bip.IntervalPattern('[0, 10]'), bip.IntervalPattern('(2, 11]'), bip.IntervalPattern('[5, 10]')]
    context = dict(zip('abc', patterns))
    atomic_patterns_true_verb = [
        ('[-inf, +inf]', 'abc'), ('[-inf, 11]', 'abc'), ('[0, +inf]', 'abc'),
        ('[-inf, 10]', 'ac'), ('[2, +inf]', 'bc'), ('(2, +inf]', 'bc'),
        ('[5, +inf]', 'c')
    ]
    atomic_patterns_true_verb = OrderedDict([(bip.IntervalPattern(ptrn), set(ext))
                                             for ptrn, ext in atomic_patterns_true_verb])
    atomic_patterns_order_true = {
        '[-inf, +inf]': {'[-inf, 11]', '[0, +inf]', '[-inf, 10]', '[2, +inf]', '(2, +inf]', '[5, +inf]'},
        '[-inf, 11]': {'[-inf, 10]'},
        '[0, +inf]': {'[2, +inf]', '(2, +inf]', '[5, +inf]'},
        '[-inf, 10]': set(),
        '[2, +inf]': {'(2, +inf]', '[5, +inf]'},
        '(2, +inf]': {'[5, +inf]'},
        '[5, +inf]': set(),
    }
    atomic_patterns_order_true = {bip.IntervalPattern(k): {bip.IntervalPattern(v) for v in vs}
                                  for k, vs in atomic_patterns_order_true.items()}

    ps.fit(context)
    assert ps.atomic_patterns == atomic_patterns_true_verb
    assert ps.atomic_patterns_order == atomic_patterns_order_true


    patterns = [['hello world', 'who is there'], ['hello world'], ['world is there']]
    patterns = [bip.NgramSetPattern(ngram) for ngram in patterns]
    context = dict(zip('abc', patterns))
    atomic_patterns_true_verb = [
        ('world', 'abc'),
        ('hello', 'ab'), ('hello world', 'ab'),
        ('is', 'ac'), ('there', 'ac'), ('is there', 'ac'),
        ('who', 'a'), ('who is', 'a'), ('who is there', 'a'),
        ('world is', 'c'), ('world is there', 'c'),
    ]
    atomic_patterns_true_verb = OrderedDict([(bip.NgramSetPattern([ptrn]), set(ext))
                                             for ptrn, ext in atomic_patterns_true_verb])

    ps.fit(context)
    assert set(ps.atomic_patterns) == set(atomic_patterns_true_verb)
    assert all(len(ps.atomic_patterns[prev]) >= len(ps.atomic_patterns[next])
               for prev, next in zip(ps.atomic_patterns, list(ps.atomic_patterns)[1:]))

    atomic_patterns_order_true = {
        'world': ['hello world', 'world is', 'world is there'],
        'hello': ['hello world'],
        'hello world': [],
        'is': ['is there', 'who is', 'who is there', 'world is', 'world is there'],
        'there': ['is there', 'who is there', 'world is there'],
        'is there': ['who is there', 'world is there'],
        'who': ['who is', 'who is there'],
        'who is': ['who is there'],
        'who is there': [],
        'world is': ['world is there'],
        'world is there': [],
    }
    atomic_patterns_order_true = {bip.NgramSetPattern([k]): {bip.NgramSetPattern([v]) for v in vs}
                                  for k, vs in atomic_patterns_order_true.items()}
    assert ps.atomic_patterns_order == atomic_patterns_order_true


def test_builtin_premaximal_patterns():
    ps = PatternStructure()

    patterns = [bip.ItemSetPattern({1, 2, 3}), bip.ItemSetPattern({4}), bip.ItemSetPattern({1, 2, 4})]
    context = dict(zip('abc', patterns))
    ps.fit(context)
    assert ps.premaximal_patterns == {patterns[0]: {'a'}, patterns[2]: {'c'}}

    patterns = [bip.IntervalPattern('[0, 10]'), bip.IntervalPattern('(2, 11]'), bip.IntervalPattern('[5, 10]')]
    context = dict(zip('abc', patterns))
    ps.fit(context)
    assert ps.premaximal_patterns == {patterns[2]: {'c'}}

    patterns = [['hello world', 'who is there'], ['hello world'], ['world is there']]
    patterns = [bip.NgramSetPattern(ngram) for ngram in patterns]
    context = dict(zip('abc', patterns))
    ps.fit(context)
    assert ps.premaximal_patterns == {patterns[0]: {'a'}, patterns[2]: {'c'}}
