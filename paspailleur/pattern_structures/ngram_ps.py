from functools import reduce
from itertools import product, chain
from math import ceil
from typing import Iterator, Iterable, Union, Literal

from bitarray import frozenbitarray as fbarray, bitarray
from bitarray.util import zeros as bazeros

from .abstract_ps import AbstractPS


class NgramPS(AbstractPS):
    PatternType = frozenset[tuple[str, ...]]  # Every tuple represents an ngram of words. A pattern is a set of incomparable ngrams
    MAX_PATTERN_PLACEHOLDER = frozenset({('<MAX_NGRAM>',)})
    min_pattern: PatternType = frozenset()  # Empty set of ngrams contained in any other set of ngrams
    max_pattern: PatternType = MAX_PATTERN_PLACEHOLDER  # the set of the most specific ngrams for the data. Might be huge
    min_n: int = 1  # Minimal size of an ngram to consider

    def __init__(self, min_n: int = 1):
        self.min_n = min_n

    def preprocess_data(
            self,
            data: Iterable[str], separator=' ',
            update_params_mode:  Literal['write', 'append', False] = 'append'
    ) -> Iterator[PatternType]:
        for text in data:
            if not text:
                yield set()
                continue

            if isinstance(text, str):
                pattern = {tuple(text.split(separator))}
            else:
                pattern = text
            pattern = {tuple(ngram) for ngram in pattern if len(ngram) >= self.min_n}
            yield frozenset(pattern)

    def join_patterns(self, a: PatternType, b: PatternType) -> PatternType:
        """Return the maximal sub-ngrams contained both in `a` and in `b`

        Example:
        >> join_patterns({('hello', 'world'), ('who', 'is', 'there')}, {('hello', 'there')}) == {('hello',), ('there',)}
        as 'hello' is contained both in 'hello world' and 'hello there'
        and 'there' is contained both in 'who is there' and 'hello there'
        """
        if a == self.max_pattern:
            return b
        if b == self.max_pattern:
            return a

        # Find common ngrams (not necessarily maximal)
        common_ngrams = []
        for ngram_a in a:
            words_pos_a = dict()
            for i, word in enumerate(ngram_a):
                words_pos_a[word] = words_pos_a.get(word, []) + [i]

            for ngram_b in b:
                if ngram_a == ngram_b:
                    common_ngrams.append(ngram_a)
                    continue

                for j, word in enumerate(ngram_b):
                    if word not in words_pos_a:
                        continue
                    # word in words_a
                    for i in words_pos_a[word]:
                        ngram_size = next(
                            s for s in range(len(ngram_b)+1)
                            if i+s >= len(ngram_a) or j+s >= len(ngram_b) or ngram_a[i+s] != ngram_b[j+s]
                        )
                        if ngram_size >= self.min_n:
                            common_ngrams.append(ngram_a[i:i+ngram_size])

        # Delete common n-grams contained in other common n-grams
        common_ngrams = sorted(common_ngrams, key=lambda ngram: len(ngram), reverse=True)
        for i in range(len(common_ngrams)):
            n_ngrams = len(common_ngrams)
            if i == n_ngrams:
                break

            ngram = common_ngrams[i]
            ngrams_to_pop = (j for j in reversed(range(i + 1, n_ngrams))
                             if self.is_less_precise({common_ngrams[j]}, {ngram}))
            for j in ngrams_to_pop:
                common_ngrams.pop(j)

        return frozenset(common_ngrams)

    def meet_patterns(self, a: PatternType, b: PatternType) -> PatternType:
        """Return the least precise pattern, described by both `a` and `b`"""
        if a == self.min_pattern:
            return b
        if b == self.min_pattern:
            return a

        return self.filter_max_ngrams(a | b)

    def is_less_precise(self, a: PatternType, b: PatternType) -> bool:
        """Return True if pattern `a` is less precise than pattern `b`"""
        if b == self.max_pattern:
            return True
        if a == self.max_pattern:  # and b != max_pattern
            return False

        for smaller_tuple in a:
            small_size = len(smaller_tuple)
            small_words = set(smaller_tuple)
            for larger_tuple in b:
                if not (small_words <= set(larger_tuple)):
                    continue

                if small_size == 1:
                    break  # inclusion found

                inclusion_found = False
                for i, word_start in enumerate(larger_tuple[:-small_size+1]):
                    if word_start != smaller_tuple[0]:
                        continue

                    inclusion_found = all(word_a == word_b for word_a, word_b in zip(smaller_tuple, larger_tuple[i:]))
                    if inclusion_found:
                        break

                if inclusion_found:
                    break
            else:  # no break, i.e. no inclusion found
                return False
        return True

    def iter_attributes(self, data: list[PatternType], min_support: Union[int, float] = 0)\
            -> Iterator[tuple[PatternType, fbarray]]:
        """Iterate binary attributes obtained from `data` (from the most general to the most precise ones)

        :parameter
            data: list[PatternType]
             list of object descriptions
            min_support: int
                Minimal amount of objects a binary attribute should cover
        :return
            iterator of (description: PatternType, extent of the description: frozenbitarray)
        """
        min_support = ceil(len(data) * min_support) if 0 < min_support < 1 else int(min_support)

        def compute_words_extents(ptrns):
            n_patterns = len(ptrns)
            words_extents: dict[str, bitarray] = {}
            for i, pattern in enumerate(ptrns):
                words = {word for ngram in pattern for word in ngram}
                for word in words:
                    if word not in words_extents:
                        words_extents[word] = bazeros(n_patterns)
                    words_extents[word][i] = True
            return words_extents

        def drop_rare_words(words_exts, min_supp):
            rare_words = [w for w, ext in words_exts.items() if ext.count() < min_supp]
            for rare_word in rare_words:
                del words_exts[rare_word]

        def setup_search_space(prev_lvl_ngrams, n_words_):
            if n_words_ <= len(prev_lvl_ngrams):
                for prev_ngrm, word_i in product(prev_lvl_ngrams, range(n_words_)):
                    if prev_ngrm[1:] + (word_i,) in prev_lvl_ngrams:
                        yield prev_ngrm, word_i
                return

            # len(prev_level_ngrams) < n_words:
            prefixes_dict: dict[tuple[int, ...], list[int]] = {}
            for prev_ngrm in prev_lvl_ngrams:
                prefix, word_i = prev_ngrm[:-1], prev_ngrm[-1]
                if prefix not in prefixes_dict:
                    prefixes_dict[prefix] = []
                prefixes_dict[prefix].append(word_i)

            for prev_ngrm in prev_lvl_ngrams:
                if prev_ngrm[1:] not in prefixes_dict:
                    continue

                for word_i in prefixes_dict[prev_ngrm[1:]]:
                    yield prev_ngrm, word_i

        def refine_extent(ext, ngram_verb, min_supp, ptrns):
            supp_delta = ext.count() - max(min_supp, 1)
            # the use of str `words` is important because of the way is_less_precise function works
            for ptrn_i in ext.search(True):
                if self.is_less_precise({ngram_verb}, ptrns[ptrn_i]):
                    continue
                # new_ngram is not contained in i-th pattern
                ext[ptrn_i] = False
                supp_delta -= 1
                if supp_delta < 0:
                    break
            else:  # no break, i.e. new_ext.count() >= min_supp
                return ext
            return None

        yield frozenset(), fbarray(~bazeros(len(data)))

        words_extents = compute_words_extents(data)
        drop_rare_words(words_extents, min_support)
        words, extents = zip(*words_extents.items())
        n_words = len(words)

        # Yield 1grams
        ngrams = {(word_i,): ext for word_i, ext in enumerate(extents)}
        for (word_i,), ext in ngrams.items():
            yield (words[word_i],), fbarray(ext)

        # Iterate 2_and_more-grams
        while ngrams:
            prev_ngrams, ngrams = ngrams, {}

            #search_space = setup_search_space(prev_ngrams, n_words)
            search_space = list(setup_search_space(prev_ngrams, n_words))
            for prev_ngram, word_i in search_space:
                # Get the approximate extent of the new ngram (which is a superset of the exact extent)
                new_ngram: tuple[int, ...] = prev_ngram + (word_i,)
                proto_extent = prev_ngrams[prev_ngram] & prev_ngrams[new_ngram[1:]]
                if not proto_extent.any() or proto_extent.count() < min_support:
                    continue

                # Get the exact extent of the new ngram
                new_ngram_verb = tuple([words[word_j] for word_j in new_ngram])
                new_extent = refine_extent(proto_extent, new_ngram_verb, min_support, data)
                if new_extent is None:
                    continue

                # Yield the new ngram if its extent is new.
                # If not, the extended version of the new ngram can still output some new extent
                ngrams[new_ngram] = new_extent
                if new_extent != extents[word_i] and new_extent != prev_ngrams[prev_ngram]\
                        and len(new_ngram) >= self.min_n:
                    yield new_ngram_verb, fbarray(new_extent)

        if min_support == 0:
            yield None, fbarray(bazeros(len(data)))

    def verbalize(self, description: PatternType, ngram_separator: str = '; ') -> str:
        """Convert `description` into human-readable string"""
        if not description:
            return '∅'
        return ngram_separator.join([' '.join(ngram) for ngram in sorted(description, key=lambda ngram: -len(ngram))])

    def closest_less_precise(self, description: PatternType, use_lectic_order: bool = False) -> Iterator[PatternType]:
        """Return closest descriptions that are less precise than `description`

        Use lectic order for optimisation of description traversal.

        IMPORTANT: Lectic order is not yet implemented
        """
        if description == self.min_pattern:
            return iter([])

        for ngram in description:
            if len(ngram) == 1:
                yield description - {ngram}
            else:
                shortened_right = self.filter_max_ngrams(description - {ngram} | {ngram[:-1], ngram[-1:]})
                shortened_left = self.filter_max_ngrams(description - {ngram} | {ngram[1:], ngram[:1]})

                if shortened_left != description:
                    yield shortened_left
                if shortened_right != shortened_left and shortened_right != description:
                    yield shortened_right

    def closest_more_precise(
            self, description: PatternType, use_lectic_order: bool = False, vocabulary: set[str] = None
    ) -> Iterator[PatternType]:
        """Return closest descriptions that are more precise than `description`

        Use lectic order for optimisation of description traversal.
        Note that the resulting descriptions may repeat in case `use_lectic_order` is set to False
        """
        if vocabulary is None:
            vocabulary = reduce(set.__or__, map(set, description), set())

        for word in vocabulary:
            wordgram = word,
            new_ngrams = chain(
                [wordgram],
                (ngram + wordgram for ngram in description),
                (wordgram + ngram for ngram in description) if not use_lectic_order else []
            )
            next_descriptions = (self.filter_max_ngrams(description | {new_ngram}) for new_ngram in new_ngrams
                                 if new_ngram not in description)

            for next_descr in next_descriptions:
                if next_descr != description:
                    yield next_descr

    def filter_max_ngrams(self, description: PatternType) -> PatternType:
        description = sorted(description, key=lambda ngram: len(ngram), reverse=True)
        i = 0
        while i < len(description):
            cur_ngram = ' '.join(description[i])
            if any(cur_ngram in ' '.join(ngram) for ngram in description[:i]):
                description.pop(i)
                continue
            i += 1
        return frozenset(description)


if __name__ == '__main__':
    texts = ['a b', 'a', 'b']
    ps = NgramPS()
    data = list(ps.preprocess_data(texts))
    colnames, itsets = ps.binarize(data)
    print(colnames)
