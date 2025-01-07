from functools import reduce
from typing import Iterator, OrderedDict
from bitarray import bitarray
from bitarray.util import zeros as bazeros

from paspailleur.algorithms import base_functions as bfuncs
from paspailleur.pattern_structures import AbstractPS
from paspailleur.pattern_structures.pattern import Pattern


def list_intents_via_Lindig_complex(data: list, pattern_structure: AbstractPS) -> list['PatternDescription']:
    """Get the list of intents of pattern concepts from `data` described by `pattern_structure` running Lindig algorithm
    from "Fast Concept Analysis" by Christian Lindig, Harvard University, Division of Engineering and Applied Sciences

    Parameters
    ----------
    data:
        list of objects described by a pattern structure
    pattern_structure:
        type of pattern structure related to data

    Returns
    -------
    Lattice_data_intents:
        list of intents of pattern concepts
    """

    class NotFound(Exception):
        pass

    def compute_bits_intersection(bits: list[bitarray], len_bitarray):
        if bits == []:
            return(bitarray([1 for _ in range(len_bitarray)]))
        bit = bits[0]
        for obj in bits[1:]:
            bit = bit & obj
        return(bit)

    def find_upper_neighbors(data: list, concept_extent: list, objects_indices: list):
        min_set = [obj for obj in objects_indices if obj not in concept_extent]
        concept_extent_values = [data[i] for i in concept_extent]
        neighbors = []

        for g in [obj for obj in objects_indices if obj not in concept_extent]:
            B1 = ps.intent(concept_extent_values + [data[g]])
            A1 = list(ps.extent(B1, data))
            if len(set(min_set) & set([obj for obj in A1 if obj not in concept_extent and obj not in [g]])) == 0:
                neighbors.append(A1)
            else:
                min_set.remove(g)
        return neighbors

    def find_next_concept_extent(data: list, concept_extent: list, List_extents: list):
        bin_col_names, rows = ps.binarize(data)
        next_concept_extent = None
        concept_extent_bit = compute_bits_intersection([rows[i] for i in concept_extent], len(rows[0]))
        for extent in List_extents:
            extent_bit = compute_bits_intersection([rows[i] for i in extent], len(rows[0]))
            if extent_bit < concept_extent_bit and (next_concept_extent is None or extent_bit > next_concept_extent_bit):
                next_concept_extent = extent
                next_concept_extent_bit = compute_bits_intersection([rows[i] for i in next_concept_extent], len(rows[0]))
        if next_concept_extent is not None:
            return next_concept_extent
        raise NotFound("Next concept not found in Lattice")

    ps = pattern_structure
    Lattice_data_extents = []  # extents set
    concept_extent = []  # Initial concept extent
    objects_indices = list(ps.extent([], data))
    Lattice_data_extents.append(concept_extent)  # Insert the initial concept extent into Lattice

    while True:
        for parent in find_upper_neighbors(data, concept_extent, objects_indices):
            if parent not in Lattice_data_extents:
              Lattice_data_extents.append(parent)

        try:
            concept_extent = find_next_concept_extent(data, concept_extent, Lattice_data_extents)
        except NotFound:
            break

    Lattice_data_intents = []
    for i in range(len(Lattice_data_extents)):
        Lattice_data_intents.append(ps.intent([data[j] for j in Lattice_data_extents[i]]))

    return Lattice_data_intents


def iter_intents_via_ocbo(
        patterns: list[Pattern]
) -> Iterator[Pattern]:
    """Iterate intents in patterns by running object-wise version of Close By One algorithm"""
    # TODO: Update the function to return extents too? As they are already computed?
    objects_per_pattern = bfuncs.group_objects_by_patterns(patterns)

    n_objects = len(patterns)
    # create a stack of pairs: 'known_extent', 'object_to_add'
    stack: list[tuple[bitarray, int]] = [(bazeros(n_objects), -1)]
    while stack:
        known_extent, object_to_add = stack.pop()
        proto_extent = known_extent.copy()
        if object_to_add >= 0:
            proto_extent[object_to_add] = True

        intent = bfuncs.intention(proto_extent, objects_per_pattern)
        extent = bfuncs.extension(intent, objects_per_pattern)

        has_objects_not_in_lex_order = (object_to_add >= 0) and (extent & ~proto_extent)[:object_to_add].any()
        if has_objects_not_in_lex_order:
            continue

        yield intent
        next_steps = [(extent, g) for g in extent.search(False, object_to_add+1)]
        stack.extend(next_steps[::-1])


def iter_all_patterns(atomic_patterns_extents: OrderedDict[Pattern, bitarray], min_support: int = 0) -> Iterator[tuple[Pattern, bitarray]]:
    # The algo is inspired by CloseByOne
    # For the start, let us just rewrite CloseByOne algorithm
    # with no though on how to optimise it for this particular case
    atomic_patterns = list(atomic_patterns_extents)
    first_pattern = atomic_patterns[0]
    total_extent = atomic_patterns_extents[first_pattern] | ~atomic_patterns_extents[first_pattern]
    meet_func, join_func = first_pattern.__class__.__and__, first_pattern.__class__.__or__

    min_pattern = reduce(meet_func, atomic_patterns) if first_pattern.min_pattern is None else first_pattern.min_pattern
    yield min_pattern, total_extent

    # create a stack of pairs: 'involved_patterns', 'pattern_to_add'
    n_atoms = len(atomic_patterns_extents)
    stack: list[tuple[bitarray, int]] = [(bazeros(n_atoms), i) for i in range(n_atoms)][::-1]
    while stack:
        involved_patterns, pattern_to_add = stack.pop()
        proto_closure = involved_patterns.copy()
        proto_closure[pattern_to_add] = True

        proto_closure_extents = (atomic_patterns_extents[atomic_patterns[i]] for i in proto_closure.search(True))
        extent = reduce(bitarray.__and__, proto_closure_extents, total_extent)
        if extent.count() < min_support:
            continue

        new_pattern = reduce(join_func, (atomic_patterns[i] for i in proto_closure.search(True)), min_pattern)
        has_atoms_not_in_lex_order = any(atomic_patterns[i] <= new_pattern
                                         for i in involved_patterns.search(False, 0, pattern_to_add))
        if has_atoms_not_in_lex_order:
            continue

        yield new_pattern, extent

        closure = proto_closure.copy()
        for i in proto_closure.search(False, pattern_to_add+1):
            closure[i] = atomic_patterns[i] <= new_pattern
        next_steps = [(closure, i) for i in closure.search(False, pattern_to_add+1)]
        stack.extend(next_steps[::-1])