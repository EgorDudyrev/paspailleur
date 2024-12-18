from paspailleur.pattern_structures.pattern import Pattern
from bitarray import frozenbitarray as fbarray


def test_init():
    a = Pattern(frozenset({1, 2, 3}))
    b = Pattern(fbarray('10011'))

    try:
        pattern_set = {a, b}
    except TypeError as e:
        assert False, e


def test_eq():
    a = Pattern(frozenset({1,2,3}))
    b = Pattern(frozenset({1,2,3}))
    c = Pattern(frozenset({3}))

    assert a == a
    assert a == b
    assert not (a != b)
    assert a != c

    a = Pattern(fbarray('111'))
    b = Pattern(fbarray('111'))
    c = Pattern(fbarray('001'))

    assert a == a
    assert a == b
    assert not (a != b)
    assert a != c


def test_and():
    a = Pattern(frozenset({1, 2, 3}))
    b = Pattern(frozenset({0, 2, 3}))
    meet = Pattern(frozenset({2, 3}))
    assert a & b == meet
    assert a.intersection(b) == meet

    a = Pattern(fbarray('10011'))
    b = Pattern(fbarray('01011'))
    meet = Pattern(fbarray('00011'))
    assert a & b == meet
    assert a.intersection(b) == meet


def test_or():
    a = Pattern(frozenset({1, 2, 3}))
    b = Pattern(frozenset({0, 2, 3}))
    join = Pattern(frozenset({0, 1, 2, 3}))
    assert a | b == join
    assert a.union(b) == join

    a = Pattern(fbarray('10011'))
    b = Pattern(fbarray('01011'))
    join = Pattern(fbarray('11011'))
    assert a | b == join
    assert a.union(b) == join


def test_substraction():
    a = Pattern(frozenset({1, 2, 3}))
    b = Pattern(frozenset({0, 2, 3}))
    sub = Pattern(frozenset({1}))
    assert a - b == sub
    assert a.difference(b) == sub


def test_comparisons():
    a = Pattern(frozenset({1, 2, 3}))
    b = Pattern(frozenset({0, 2, 3}))
    c = Pattern(frozenset({2, 3}))
    d = Pattern(frozenset({2, 3}))
    e = Pattern(frozenset({10, 11}))

    assert not (a <= b)
    assert not a.issubpattern(b)
    assert not (b >= a)
    assert not b.issuperpattern(a)

    assert not (a <= c)
    assert not a.issubpattern(c)
    assert c <= a
    assert c.issubpattern(a)
    assert a.issuperpattern(c)
    assert c <= c
    assert c.issubpattern(c)
    assert c.issuperpattern(c)
    assert not c.issuperpattern(e)

    assert c < a
    assert c == d
    assert b > c
    assert not (b > b)


def test_repr():
    a = Pattern(frozenset({1, 2, 3}))
    assert str(a) == "Pattern(frozenset({1, 2, 3}))"

    a = Pattern(fbarray('10011'))
    assert str(a) == "Pattern(frozenbitarray('10011'))"