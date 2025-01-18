import math

import pytest

from paspailleur.pattern_structures import built_in_patterns as bip


def test_ItemSetPattern():
    a = bip.ItemSetPattern([1, 3, 2])
    a2 = bip.ItemSetPattern({1, 2, 3})
    b = bip.ItemSetPattern([1, 2])
    c = bip.ItemSetPattern([1, 2, 6, 2])
    c2 = bip.ItemSetPattern([1, 2, 6])
    z = bip.ItemSetPattern('123')

    assert a == a2
    assert c == c2
    assert b <= a
    assert not (a <= b)

    assert z.value == frozenset({1, 2, 3})


    a = bip.ItemSetPattern(range(1, 5))
    b = bip.ItemSetPattern(range(3, 7))
    meet = bip.ItemSetPattern(range(3, 5))
    join = bip.ItemSetPattern(range(1, 7))
    assert a & b == meet
    assert a | b == join

    try:
        {a, b, meet, join}
    except TypeError as e:
        assert e

    assert {bip.ItemSetPattern({2, 3})}  # test if hashable
    assert {bip.ItemSetPattern([2, 3])}  # test if hashable

    a = bip.ItemSetPattern(range(1, 5))
    assert str(a) == "ItemSetPattern({1, 2, 3, 4})"

    a = bip.ItemSetPattern({1, 2, 3, 4})
    b = bip.ItemSetPattern({3, 4, 5, 6, 7})
    sub = bip.ItemSetPattern({1, 2})
    assert a - b == sub

    assert a.min_pattern == bip.ItemSetPattern(set())
    assert b.max_pattern is None

    pattern = bip.ItemSetPattern([1, 2, 3])
    a = bip.ItemSetPattern("[1, 2, 3]")
    assert a == pattern

    a = bip.ItemSetPattern("1,2,3")
    assert a == pattern

    a = bip.ItemSetPattern('abc')
    assert a == bip.ItemSetPattern(['a','b','c'])


def test_IntervalPattern():
    a = bip.IntervalPattern(((1, True), (10, False)))
    a2 = bip.IntervalPattern('[1, 10)')
    assert a.value == ((1, True), (10, False))
    assert a == a2

    a = bip.IntervalPattern('[-inf, ∞)')
    assert a.lower_bound == -math.inf
    assert a.upper_bound == math.inf

    a = bip.IntervalPattern('[1, 10]')
    b = bip.IntervalPattern('[1, 20]')
    assert a & b == b
    assert a | b == a
    assert a >= b
    assert a.issuperpattern(b)
    assert b <= a
    assert b.issubpattern(a)
    assert not a.issubpattern(b)

    a = bip.IntervalPattern('[1, 10)')
    b = bip.IntervalPattern('(1, 10]')
    meet = bip.IntervalPattern('[1, 10]')
    join = bip.IntervalPattern('(1, 10)')
    assert a & b == meet
    assert a | b == join

    c = bip.IntervalPattern('[-20, 1)')
    assert a | c == a.max_pattern
    assert a.max_pattern | a.min_pattern == a.max_pattern
    assert a.max_pattern & a.min_pattern == a.min_pattern

    assert str(a) == 'IntervalPattern([1.0, 10.0))'

    assert {a, b}  # Test if hashable

    assert a.min_pattern == bip.IntervalPattern('[-inf, +inf]')
    assert a.max_pattern == bip.IntervalPattern('ø')
    assert {a.max_pattern}  # Test if max pattern is hashable


def test_ClosedIntervalPattern():
    a = bip.ClosedIntervalPattern((1, 10))
    a2 = bip.ClosedIntervalPattern('[1, 10]')
    assert a.value == (1, 10)
    assert a == a2

    with pytest.raises(ValueError):
        bip.ClosedIntervalPattern('(10, 25)')
        bip.ClosedIntervalPattern('(10, 25]')
        bip.ClosedIntervalPattern('[10, 25)')

    a = bip.ClosedIntervalPattern('[-inf, ∞]')
    assert a.lower_bound == -math.inf
    assert a.upper_bound == math.inf

    a = bip.ClosedIntervalPattern('[1, 10]')
    b = bip.ClosedIntervalPattern('[1, 20]')
    assert a & b == b
    assert a | b == a
    assert a >= b
    assert a.issuperpattern(b)
    assert b <= a
    assert b.issubpattern(a)
    assert not a.issubpattern(b)

    c = bip.ClosedIntervalPattern('[-20, 0]')
    assert a | c == a.max_pattern
    assert a.max_pattern | a.min_pattern == a.max_pattern
    assert a.max_pattern & a.min_pattern == a.min_pattern

    assert str(a) == 'ClosedIntervalPattern([1.0, 10.0])'

    assert {a, b}  # Test if hashable

    assert a.min_pattern == bip.ClosedIntervalPattern('[-inf, +inf]')
    assert a.max_pattern == bip.ClosedIntervalPattern('ø')
    assert {a.max_pattern}  # Test if max pattern is hashable


def test_NgramSetPattern():
    a = bip.NgramSetPattern({('hello', 'world')})
    a2 = bip.NgramSetPattern(['hello     world   '])
    assert a.value == {('hello', 'world')}
    assert a == a2

    a = bip.NgramSetPattern(['hello world', 'who is there'])
    b = bip.NgramSetPattern(['hello there'])
    meet = bip.NgramSetPattern(['hello', 'there'])
    join = bip.NgramSetPattern(['hello world', 'who is there', 'hello there'])
    assert a & b == meet
    assert a | b == join
    assert meet <= a
    assert a <= join

    a = bip.NgramSetPattern(['hello world', 'who is there'])
    assert str(a) == "NgramSetPattern({'who is there', 'hello world'})"

    assert {a, b, meet, join}  # Test if hashable

    assert a.min_pattern == bip.NgramSetPattern([])
    assert b.max_pattern is None

    atomic_patterns_true = {'hello', 'world', 'hello world',
                            'who', 'is', 'there', 'who is', 'is there', 'who is there'
                            }
    atomic_patterns_true = {bip.NgramSetPattern({ngram}) for ngram in atomic_patterns_true}
    assert a.atomic_patterns == atomic_patterns_true


def test_parse_string_description():
    value = {1, 2, 3}
    value_parsed = bip.ItemSetPattern.parse_string_description('[1,2,3]')
    assert value_parsed == value

    value_parsed = bip.ItemSetPattern.parse_string_description('1,2,3')
    assert value_parsed == value

    value_parsed = bip.ItemSetPattern.parse_string_description('123')
    assert value_parsed == value

    value = {'a', 'b', 'c'}
    value_parsed = bip.ItemSetPattern.parse_string_description('abc')
    assert value_parsed == value

    value = {'abc'}
    value_parsed = bip.ItemSetPattern.parse_string_description('[abc]')
    assert value == value_parsed
