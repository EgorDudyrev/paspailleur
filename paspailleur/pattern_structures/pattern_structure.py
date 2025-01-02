from collections import deque, OrderedDict
from functools import reduce
from typing import Type, TypeVar, Union, Collection, Optional, Iterator
from bitarray import bitarray, frozenbitarray as fbarray
from bitarray.util import zeros as bazeros, subset as basubset

from caspailleur.order import sort_intents_inclusion, inverse_order
from .pattern import Pattern


class PatternStructure:
    PatternType = TypeVar('PatternType', bound=Pattern)

    def __init__(self, pattern_type: Type[Pattern] = Pattern):
        self.PatternType = pattern_type
        # patterns introduced by objects, related to what exact objects they introduce
        self._object_irreducibles: Optional[dict[pattern_type, fbarray]] = None
        self._object_names: Optional[list[str]] = None
        # smallest nontrivial patterns, related to what objects they describe
        self._atomic_patterns: Optional[OrderedDict[pattern_type, fbarray]] = None
        # list of indices of greater atomic patterns per every atomic pattern
        self._atomic_patterns_order: Optional[list[fbarray]] = None

    def extent(self, pattern: PatternType, return_bitarray: bool = False) -> Union[set[str], fbarray]:
        if not self._object_irreducibles or not self._object_names:
            raise ValueError('The data is unknown. Fit the PatternStructure to your data using .fit(...) method')

        n_objects = len(self._object_names)
        empty_extent = fbarray(bazeros(n_objects))
        sub_extents = (extent for ptrn, extent in self._object_irreducibles.items() if pattern <= ptrn)
        extent = reduce(fbarray.__or__, sub_extents, empty_extent)

        if return_bitarray:
            return fbarray(extent)
        return {self._object_names[g] for g in extent.search(True)}

    def intent(self, objects: Union[Collection[str], fbarray]) -> PatternType:
        if not self._object_irreducibles or not self._object_names:
            raise ValueError('The data is unknown. Fit the PatternStructure to your data using .fit(...) method')

        if not isinstance(objects, bitarray):
            objects_ba = bazeros(len(self._object_names))
            for object_name in objects:
                objects_ba[self._object_names.index(object_name)] = True
        else:
            objects_ba = objects

        super_patterns = [ptrn for ptrn, irr_ext in self._object_irreducibles.items() if basubset(irr_ext, objects_ba)]
        if super_patterns:
            return reduce(self.PatternType.__and__, super_patterns)
        return reduce(self.PatternType.__or__, self._object_irreducibles)

    def fit(self, object_descriptions: dict[str, PatternType], compute_atomic_patterns: bool = None):
        n_objects = len(object_descriptions)
        empty_extent = bazeros(n_objects)

        object_names = []
        object_irreducibles = dict()
        for g, (object_name, object_description) in enumerate(object_descriptions.items()):
            object_names.append(object_name)
            if object_description not in object_irreducibles:
                object_irreducibles[object_description] = empty_extent.copy()
            object_irreducibles[object_description][g] = True
        object_irreducibles = {pattern: fbarray(extent) for pattern, extent in object_irreducibles.items()}

        self._object_names = object_names
        self._object_irreducibles = object_irreducibles

        if compute_atomic_patterns is None:
            # Set to True if the values can be computed
            pattern = list(object_irreducibles)[0]
            try:
                _ = pattern.atomic_patterns
                compute_atomic_patterns = True
            except NotImplementedError:
                compute_atomic_patterns = False
        if compute_atomic_patterns:
            self.init_atomic_patterns()

    @property
    def min_pattern(self) -> PatternType:
        if not self._object_irreducibles:
            raise ValueError('The data is unknown. Fit the PatternStructure to your data using .fit(...) method')
        some_pattern = list(self._object_irreducibles)[0]
        if some_pattern.min_pattern is None:
            min_pattern = reduce(self.PatternType.__and__, self._object_irreducibles, some_pattern)
        else:
            min_pattern = some_pattern.min_pattern
        return min_pattern

    @property
    def max_pattern(self) -> PatternType:
        if not self._object_irreducibles:
            raise ValueError('The data is unknown. Fit the PatternStructure to your data using .fit(...) method')

        some_pattern = list(self._object_irreducibles)[0]
        if some_pattern.max_pattern is None:
            max_pattern = reduce(self.PatternType.__or__, self._object_irreducibles, some_pattern)
        else:
            max_pattern = some_pattern.max_pattern
        return max_pattern

    def init_atomic_patterns(self):
        """Compute the set of all patterns that cannot be obtained by intersection of other patterns"""
        atomic_patterns = reduce(set.__or__, (p.atomic_patterns for p in self._object_irreducibles), set())

        # Step 1. Group patterns by their extents. For every extent, list patterns in topological sorting
        patterns_per_extent: dict[fbarray, deque[Pattern]] = dict()
        for atomic_pattern in atomic_patterns:
            extent: fbarray = self.extent(atomic_pattern, return_bitarray=True)
            if extent not in patterns_per_extent:
                patterns_per_extent[extent] = deque([atomic_pattern])
                continue
            # extent in patterns_per_extent, i.e. there are already some known patterns per extent
            equiv_patterns = patterns_per_extent[extent]
            greater_patterns = (i for i, other in enumerate(equiv_patterns) if atomic_pattern <= other)
            first_greater_pattern = next(greater_patterns, len(equiv_patterns))
            patterns_per_extent[extent].insert(first_greater_pattern, atomic_pattern)

        # Step 2. Find order on atomic patterns.
        def sort_extents_subsumption(extents):
            empty_extent = extents[0] & ~extents[0]
            if not extents[0].all():
                extents.insert(0, ~empty_extent)
            if extents[-1].any():
                extents.append(empty_extent)
            inversed_extents_subsumption_order = inverse_order(sort_intents_inclusion(extents[::-1], use_tqdm=False, return_transitive_order=True)[1])
            extents_subsumption_order = [ba[::-1] for ba in inversed_extents_subsumption_order[::-1]]
            if ~empty_extent not in patterns_per_extent:
                extents.pop(0)
                extents_subsumption_order = [ba[1:] for ba in extents_subsumption_order[1:]]
            if empty_extent not in patterns_per_extent:
                extents.pop(-1)
                extents_subsumption_order = [ba[:-1] for ba in extents_subsumption_order[:-1]]
            return extents_subsumption_order

        sorted_extents = sorted(patterns_per_extent, key=lambda ext: (-ext.count(), tuple(ext.search(True))))
        extents_order = sort_extents_subsumption(sorted_extents)
        extents_to_idx_map = {extent: idx for idx, extent in enumerate(sorted_extents)}

        atomic_patterns, atomic_extents = zip(*[(ptrn, ext) for ext in sorted_extents for ptrn in patterns_per_extent[ext]])
        pattern_to_idx_map = {pattern: idx for idx, pattern in enumerate(atomic_patterns)}
        n_patterns = len(atomic_patterns)

        # patterns pointing to the bitarray of indices of next greater patterns
        patterns_order: list[bitarray] = [None for _ in range(n_patterns)]
        for pattern in reversed(atomic_patterns):
            idx = pattern_to_idx_map[pattern]
            extent = atomic_extents[idx]
            extent_idx = extents_to_idx_map[extent]

            # select patterns that might be greater than the current one
            patterns_to_test = bazeros(n_patterns)
            n_greater_patterns_same_extent = len(patterns_per_extent[extent]) - patterns_per_extent[extent].index(pattern)-1
            patterns_to_test[idx+1:idx+n_greater_patterns_same_extent+1] = True
            for smaller_extent_idx in extents_order[extent_idx].search(True):
                other_extent = sorted_extents[smaller_extent_idx]
                first_other_pattern_idx = pattern_to_idx_map[patterns_per_extent[other_extent][0]]
                n_patterns_other_extent = len(patterns_per_extent[other_extent])
                patterns_to_test[first_other_pattern_idx:first_other_pattern_idx+n_patterns_other_extent] = True

            # find patterns that are greater than the current one
            super_patterns = bazeros(n_patterns)
            while patterns_to_test.any():
                other_idx = patterns_to_test.find(True)
                patterns_to_test[other_idx] = False

                other = atomic_patterns[other_idx]
                if pattern < other:
                    super_patterns[other_idx] = True
                    super_patterns |= patterns_order[other_idx]
                    patterns_to_test &= ~patterns_order[other_idx]
            patterns_order[idx] = super_patterns

        atomic_patterns = OrderedDict([(ptrn, ext) for ext in sorted_extents for ptrn in patterns_per_extent[ext]])
        self._atomic_patterns = atomic_patterns
        self._atomic_patterns_order = [fbarray(ba) for ba in patterns_order]

    def iter_atomic_patterns(self, return_extents: bool = True, return_bitarrays: bool = False) -> Union[
        Iterator[PatternType], Iterator[tuple[PatternType, set[str]]], Iterator[tuple[PatternType, fbarray]]
    ]:
        for pattern, extent in self._atomic_patterns.items():
            if return_extents:
                extent = extent if return_bitarrays else {self._object_names[g] for g in extent.search(True)}
                yield pattern, extent
            else:
                yield pattern

    @property
    def atomic_patterns(self) -> OrderedDict[PatternType, set[str]]:
        return OrderedDict(self.iter_atomic_patterns(return_extents=True, return_bitarrays=False))

    @property
    def atomic_patterns_order(self) -> dict[PatternType, set[PatternType]]:
        if self._atomic_patterns_order is None:
            return None
        atomic_patterns_list = list(self._atomic_patterns)
        return {atomic_patterns_list[idx]: {atomic_patterns_list[v] for v in vs.search(True)}
                for idx, vs in enumerate(self._atomic_patterns_order)}

    def iter_premaximal_patterns(self, return_extents: bool = True, return_bitarrays: bool = False) -> Union[
        Iterator[PatternType], Iterator[tuple[PatternType, set[str]]], Iterator[tuple[PatternType, fbarray]]
    ]:
        assert self._object_irreducibles is not None, \
            "Please define object-irreducible patterns (i.e. via .fit() function) " \
            "to be able to define premaximal_patterns"

        border_pattern_extents = {
            pattern: self.extent(pattern=pattern, return_bitarray=True) for pattern in self._object_irreducibles}
        premaximals = sorted(
            border_pattern_extents,
            key=lambda pattern: (border_pattern_extents[pattern].count(), border_pattern_extents[pattern].search(True)))
        # now smallest patterns at the start, maximals at the end

        i = 0
        while i < len(premaximals):
            pattern = premaximals[i]
            if any(other >= pattern for other in premaximals[:i]):
                del premaximals[i]
                continue
            # current pattern is premaximal, i.e. exists no bigger nontrivial pattern
            i += 1

            if not return_extents:
                yield pattern
            else:
                extent = border_pattern_extents[pattern]
                if return_bitarrays:
                    yield pattern, extent
                else:
                    yield pattern, {self._object_names[g] for g in extent.search(True)}

    @property
    def premaximal_patterns(self) -> dict[PatternType, set[str]]:
        """Maximal patterns that describe fewest objects (and their extents)"""
        return dict(self.iter_premaximal_patterns(return_extents=True, return_bitarrays=False))
