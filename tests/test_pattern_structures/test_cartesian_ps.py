from paspailleur.pattern_structures import CartesianPS, IntervalPS, SuperSetPS, SubSetPS, NgramPS
from bitarray import frozenbitarray as fbarray
import math


def test_intersect_patterns():
    a = ((1, 2), (3, 5))
    b = ((0, 2), (3, 5))
    cps = CartesianPS(basic_structures=[IntervalPS(), IntervalPS()])
    assert cps.join_patterns(a, b) == b
    assert cps.join_patterns(b, a) == b

    assert cps.join_patterns(cps.max_pattern, a) == a
    assert cps.join_patterns(a, cps.max_pattern) == a


def test_bin_attributes():
    data = [
        ((0, 1), (10, 20)),
        ((1, 2), (10, 20))
    ]
    patterns_true = (
        (0, (0, 2)), (0, (1, 2)), (0, (0, 1)), (0, (math.inf, -math.inf)),
        (1, (10, 20)), (1, (math.inf, -math.inf)),
    )
    flags_true = (
        '11',  # (0, (0, 2))
        '01',  # (0, (1, 2))
        '10',  # (0, (0, 1))
        '00',  # (0, None)
        '11',  # (1, (10, 20)
        '00',  # (1, None))
    )
    flags_true = tuple([fbarray(flag) for flag in flags_true])

    cps = CartesianPS(basic_structures=[IntervalPS(), IntervalPS()])
    patterns, flags = list(zip(*list(cps.iter_bin_attributes(data))))
    assert patterns == patterns_true
    assert flags == flags_true

    patterns, flags = list(zip(*list(cps.iter_bin_attributes(data, min_support=0.5))))
    assert set(flags) == {flg for flg in flags_true if flg.count() > 0}

    patterns, flags = list(zip(*list(cps.iter_bin_attributes(data, min_support=1))))
    assert set(flags) == {flg for flg in flags_true if flg.count() > 0}


def test_is_subpattern():
    cps = CartesianPS(basic_structures=[IntervalPS(), IntervalPS()])

    assert cps.is_less_precise([(0, 1), (3, 5)], [(1, 1), (3, 4)])
    assert not cps.is_less_precise([(0, 1), (3, 5)], [(1, 1), (2, 4)])


def test_n_bin_attributes():
    data = [
        ((0, 1), (10, 20)),
        ((1, 2), (10, 20))
    ]

    cps = CartesianPS(basic_structures=[IntervalPS(), IntervalPS()])
    assert cps.n_bin_attributes(data) == 6


def test_binarize():
    data = [
        ((0, 1), (10, 20)),
        ((1, 2), (10, 20))
    ]
    patterns_true = [
        (0, (0, 2)), (0, (1, 2)), (0, (0, 1)), (0, (math.inf, -math.inf)),
        (1, (10, 20)), (1, (math.inf, -math.inf)),
    ]
    itemsets_true = [
        '101010',
        '110010',
    ]
    itemsets_true = [fbarray(itemset) for itemset in itemsets_true]

    cps = CartesianPS(basic_structures=[IntervalPS(), IntervalPS()])
    patterns, itemsets = cps.binarize(data)
    assert patterns == patterns_true
    assert itemsets == itemsets_true


def test_intent():
    data = [
        ((0, 1), (10, 20)),
        ((1, 2), (10, 20))
    ]

    cps = CartesianPS(basic_structures=[IntervalPS(), IntervalPS()])
    assert cps.intent(data) == ((0, 2), (10, 20))


def test_extent():
    data = [
        [(0, 1), (10, 20)],
        [(1, 2), (10, 20)]
    ]

    cps = CartesianPS(basic_structures=[IntervalPS(), IntervalPS()])
    assert list(cps.extent(data, [(1, 2), (10, 20)])) == [1]


def test_preprocess_data():
    data = [
        [(0, 1), 'x', 'hello world'],
        [(0, 3), 'y', 'hello']
    ]

    cps = CartesianPS(basic_structures=[IntervalPS(), SuperSetPS(), NgramPS()])
    assert list(cps.preprocess_data(data)) == [
        ((0., 1.), frozenset({'x'}), frozenset({('hello', 'world')})),
        ((0., 3.), frozenset({'y'}), frozenset({('hello',)}))
    ]


def test_verbalize():
    ps = CartesianPS(basic_structures=[IntervalPS(), NgramPS(), SuperSetPS(), SubSetPS()])
    description = [(1, 2.43), {('hello', 'world'), ('hello',)}, {'a', 'b'}, set()]
    verbose = "0: [1.00, 2.43], 1: hello world; hello, 2: a, b, 3: ∅"
    assert ps.verbalize(description) == verbose

    params = {0: {'number_format': '.0f'}, 1: {'ngram_separator': ', '}}
    verbose = "0: [1, 2]\n1: hello world, hello\n2: a, b\n3: ∅"
    assert ps.verbalize(description, basic_structures_params=params, separator='\n') == verbose
