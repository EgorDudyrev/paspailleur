from collections import OrderedDict

from bitarray import bitarray

import paspailleur.pattern_structures.built_in_patterns as bip
import paspailleur.algorithms.mine_equivalence_classes as mec


def test_iter_intents_via_ocbo():
    # data is inspired by newzealand_en context from FCA_repository
    data = {
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
    data = {obj: bip.ItemSetPattern(descr) for obj, descr in data.items()}
    objects_order = ['Stewart Island', 'Fjordland NP', 'Invercargill', 'Milford Sound', 'MT. Aspiring NP', 'Te Anau',
                     'Dunedin', 'Oamaru', 'Queenstown', 'Wanaka', 'Otago Peninsula', 'Haast', 'Catlins']
    data_list = [data[k] for k in objects_order]

    # the intents are ordered lexicographically w.r.t. their extents ordered w.r.t. objects_order
    intents_true = OrderedDict([
        (('Bungee Jumping', 'Hiking', 'Jet Boating', 'Observing Nature', 'Parachute Gliding', 'Sightseeing Flights',
         'Skiing', 'Wildwater Rafting'), bitarray('0000000000000')),  # extent: []
        (('Hiking', 'Observing Nature', 'Sightseeing Flights'), bitarray('1111111000000')),  # extent: [0, 1, 2, 3, 4, 5, 6]
        (('Hiking', 'Observing Nature'), bitarray('1111111100111')),  # extent: [0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 12]
        (('Hiking',), bitarray('1111111111111')),  # extent: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        (('Hiking', 'Sightseeing Flights'), bitarray('1111111011000')),  # extent: [0, 1, 2, 3, 4, 5, 6, 8, 9]
        (('Hiking', 'Jet Boating', 'Observing Nature', 'Sightseeing Flights'), bitarray('0000010000000')),  # extent: [5]
        (('Hiking', 'Jet Boating', 'Sightseeing Flights'), bitarray('0000010011000')),  # extent: [5, 8, 9]
        (('Bungee Jumping', 'Hiking', 'Jet Boating', 'Parachute Gliding', 'Sightseeing Flights', 'Skiing',
         'Wildwater Rafting'), bitarray('0000000011000'))  # extent: [8, 9]
    ])
    intents_true = OrderedDict([(bip.ItemSetPattern(intent), extent) for intent, extent in intents_true.items()])

    intents = OrderedDict(mec.iter_intents_via_ocbo(data_list))
    assert len(intents) == len(intents_true)
    assert list(intents) == list(intents_true)
    assert intents == intents_true


def test_iter_all_patterns():
    #######################################################################
    # Tests for ItemSetPattern where all atomic patterns are incomparable #
    #######################################################################
    atomic_patterns_extents = OrderedDict([
        ('Hiking', bitarray('111111111')),
        ('Observing Nature', bitarray('111111001')),
        ('Sightseeing Flights', bitarray('001111111')),
    ])
    atomic_patterns_extents = OrderedDict([(bip.ItemSetPattern({k}), v) for k, v in atomic_patterns_extents.items()])

    all_patterns_true = OrderedDict([
        ('', bitarray('111111111')),
        ('Hiking', bitarray('111111111')),
        ('Hiking, Observing Nature', bitarray('111111001')),
        ('Hiking, Observing Nature, Sightseeing Flights', bitarray('001111001')),
        ('Hiking, Sightseeing Flights', bitarray('001111111')),
        ('Observing Nature', bitarray('111111001')),
        ('Observing Nature, Sightseeing Flights', bitarray('001111001')),
        ('Sightseeing Flights', bitarray('001111111'))
    ])
    all_patterns_true = OrderedDict([(bip.ItemSetPattern(k.split(', ') if k else []), v)
                                     for k, v in all_patterns_true.items()])

    all_patterns = OrderedDict(list(mec.iter_all_patterns(atomic_patterns_extents, min_support=0)))
    assert len(all_patterns) == len(all_patterns_true)
    assert list(all_patterns) == list(all_patterns_true)
    assert all_patterns == all_patterns_true

    all_patterns = OrderedDict(list(mec.iter_all_patterns(atomic_patterns_extents, min_support=7)))
    assert all_patterns == OrderedDict([(k, v) for k, v in all_patterns_true.items() if v.count() >= 7])

    ######################################################################
    # Test for NgramSetPattern where some atomic patterns are comparable #
    ######################################################################
    atomic_patterns_extents = OrderedDict([
        ('hello', bitarray('111111111')),
        ('world', bitarray('111111001')),
        ('hello world', bitarray('001111001')),
        ('!', bitarray('110111111'))
    ])
    atomic_patterns_extents = OrderedDict([(bip.NgramSetPattern([k]), v) for k, v in atomic_patterns_extents.items()])

    all_patterns_true = OrderedDict([
        ('', bitarray('111111111')),
        ('hello', bitarray('111111111')),
        ('hello, world', bitarray('111111001')),
        ('hello world', bitarray('001111001')),
        ('hello world, !', bitarray('000111001')),
        ('hello, world, !', bitarray('110111001')),
        ('hello, !', bitarray('110111111')),
        ('world', bitarray('111111001')),
        ('world, !', bitarray('110111001')),
        ('!', bitarray('110111111')),
    ])
    all_patterns_true = OrderedDict([(bip.NgramSetPattern(k.split(', ') if k else []), v)
                                     for k, v in all_patterns_true.items()])

    all_patterns = OrderedDict(list(mec.iter_all_patterns(atomic_patterns_extents, min_support=0)))
    assert len(all_patterns) == len(all_patterns_true)
    assert list(all_patterns) == list(all_patterns_true)
    assert all_patterns == all_patterns_true

    ######################################################
    # Test for NgramSetPattern with breadth-first search #
    ######################################################
    all_patterns_true_breadth = OrderedDict([
        ('', bitarray('111111111')),
        ('hello', bitarray('111111111')),
        ('world', bitarray('111111001')),
        ('!', bitarray('110111111')),
        ('hello, world', bitarray('111111001')),
        ('hello, !', bitarray('110111111')),
        ('world, !', bitarray('110111001')),
        ('hello world', bitarray('001111001')),
        ('hello, world, !', bitarray('110111001')),
        ('hello world, !', bitarray('000111001')),
    ])
    all_patterns_true_breadth = OrderedDict([(bip.NgramSetPattern(k.split(', ') if k else []), v)
                                             for k, v in all_patterns_true_breadth.items()])

    all_patterns = OrderedDict(list(mec.iter_all_patterns(atomic_patterns_extents, min_support=0, depth_first=False)))
    assert len(all_patterns) == len(all_patterns_true_breadth)
    assert list(all_patterns) == list(all_patterns_true_breadth)
    assert all_patterns == all_patterns_true_breadth

    #####################################################
    # Test NgramSetPattern with controllable navigation #
    #####################################################
    stop_pattern = bip.NgramSetPattern(['hello', 'world'])
    all_patterns_true_stopped = OrderedDict([(k, v) for k, v in all_patterns_true.items()
                                             if not k > stop_pattern])
    iterator = mec.iter_all_patterns(atomic_patterns_extents, controlled_iteration=True)
    _ = next(iterator)
    all_patterns_stopped, pattern = [], None
    while True:
        go_deeper = (pattern is None) or (pattern != stop_pattern)
        try:
            pattern, extent = iterator.send(go_deeper)
        except StopIteration:
            break
        all_patterns_stopped.append((pattern, extent))
    all_patterns_stopped = OrderedDict(all_patterns_stopped)
    assert len(all_patterns_stopped) == len(all_patterns_true_stopped)
    assert list(all_patterns_stopped) == list(all_patterns_true_stopped)
    assert all_patterns_stopped == all_patterns_true_stopped

    stop_pattern = bip.NgramSetPattern([])
    iterator = mec.iter_all_patterns(atomic_patterns_extents, controlled_iteration=True)
    _ = next(iterator)
    all_patterns_stopped, pattern = [], None
    while True:
        go_deeper = (pattern is None) or (pattern != stop_pattern)
        try:
            pattern, extent = iterator.send(go_deeper)
        except StopIteration:
            break
        all_patterns_stopped.append((pattern, extent))
    all_patterns_stopped = OrderedDict(all_patterns_stopped)
    assert len(all_patterns_stopped) == 1
