import pandas as pd
import pytest

from paspailleur.pattern_structures import pattern_factory as pf, built_in_patterns as bip


def test_pattern_factory():
    new_pattern = pf.pattern_factory(bip.IntervalPattern)
    assert isinstance(new_pattern(42), bip.IntervalPattern)
    assert new_pattern.__name__ == "FactoredPattern"

    new_pattern = pf.pattern_factory(bip.IntervalPattern, 'CustomName')
    assert new_pattern.__name__ == "CustomName"

    new_pattern = pf.pattern_factory(bip.IntervalPattern, BoundsUniverse=tuple(range(5)))
    assert new_pattern.__name__ == "FactoredPattern"
    assert new_pattern.BoundsUniverse == tuple(range(5))

    with pytest.raises(ValueError):
        new_pattern = pf.pattern_factory(bip.IntervalPattern, RandomV = 42)

    new_pattern = pf.pattern_factory('IntervalPattern', BoundsUniverse=tuple(range(5)))
    assert isinstance(new_pattern(2), bip.IntervalPattern)


def test_from_pandas():
    df = pd.DataFrame({'age': {'Alex': 10, 'Bob': 20}, 'country': {'Alex': 'Argentina', 'Bob': 'Belgium'}})

    class Age(bip.IntervalPattern):
        BoundsUniverse = (10, 20)
    class Country(bip.CategorySetPattern):
        Universe = {'Argentina', 'Belgium'}

    class DataPattern(bip.CartesianPattern):
        DimensionTypes = {'age': Age, 'country': Country}

    factored = pf.from_pandas(df)
    assert issubclass(factored, bip.CartesianPattern)
    assert set(factored.DimensionTypes) == {'age', 'country'}
    assert issubclass(factored.DimensionTypes['age'], bip.IntervalPattern)
    assert issubclass(factored.DimensionTypes['country'], bip.CategorySetPattern)
    assert factored.DimensionTypes['age'].BoundsUniverse == (10, 20)
    assert factored.DimensionTypes['country'].Universe == {'Argentina', 'Belgium'}

