import difflib
from collections import deque
from functools import reduce
from itertools import chain
from typing import Iterator, Iterable

from bitarray import frozenbitarray as fbarray, bitarray
from bitarray.util import zeros as bazeros
from paspailleur.pattern_structures import AbstractPS

import nltk
from nltk.util import ngrams
from nltk.corpus import wordnet
nltk.download('wordnet')


class NgramPS(AbstractPS):
    PatternType = set[tuple[str, ...]]  # Every tuple represents an ngram of words. A pattern is a set of incomparable ngrams
    bottom: PatternType = None  # the most specific ngram for the data. Equals to None for simplicity
    min_n: int = 1  # Minimal size of an ngram to consider
    
    def __init__(self, min_n: int = 1):
        self.min_n = min_n

    def preprocess_data(self, data: Iterable[str], separator=' ') -> list[PatternType]:
        ngrams = (tuple(text.split(separator)) if text != '' else tuple() for text in data)
        patterns = [{ngram} if len(ngram) >= self.min_n else set() for ngram in ngrams]
        return patterns

    def join_patterns(self, a: PatternType, b: PatternType) -> PatternType:
        """Return the maximal sub-ngrams contained both in `a` and in `b`

        Example:
        >> join_patterns({('hello', 'world'), ('who', 'is', 'there')}, {('hello', 'there')}) == {('hello',), ('there',)}
        as 'hello' is contained both in 'hello world' and 'hello there'
        and 'there' is contained both in 'who is there' and 'hello there'
        """
        # Transform the set of words into text
        seq_matcher = difflib.SequenceMatcher(isjunk=lambda ngram: len(ngram) < self.min_n)

        common_ngrams = []
        for ngram_a in a:
            seq_matcher.set_seq1(ngram_a)
            for ngram_b in b:
                seq_matcher.set_seq2(ngram_b)

                blocks = seq_matcher.get_matching_blocks()[:-1]  # the last block is always empty, so skip it
                common_ngrams.extend((ngram_a[block.a: block.a+block.size] for block in blocks
                                      if block.size >= self.min_n))

        # Delete common n-grams contained in other common n-grams
        common_ngrams = sorted(common_ngrams, key=lambda ngram: len(ngram), reverse=True)
        for i in range(len(common_ngrams)):
            n_ngrams = len(common_ngrams)
            if i == n_ngrams:
                break

            ngram = common_ngrams[i]
            ngrams_to_pop = (j for j in reversed(range(i+1, n_ngrams)) if self.is_less_precise(common_ngrams[j], ngram))
            for j in ngrams_to_pop:
                common_ngrams.pop(j)

        return set(common_ngrams)

    def iter_bin_attributes(self, data: list[PatternType], min_support: int = 0) -> Iterator[tuple[PatternType, fbarray]]:
        """Iterate binary attributes obtained from `data` (from the most general to the most precise ones)

        :parameter
            data: list[PatternType]
             list of object descriptions
        :return
            iterator of (description: PatternType, extent of the description: frozenbitarray)
        """
        empty_extent = bazeros(len(data))

        words_extents: dict[str, bitarray] = {}
        for i, pattern in enumerate(data):
            for ngram in pattern:
                for word in ngram:
                    if word not in words_extents:
                        words_extents[word] = empty_extent.copy()
                    words_extents[word][i] = True

        total_pattern = set()
        if any(extent.all() for extent in words_extents.values()):
            total_pattern = reduce(self.join_patterns, data[1:], data[0])

        yield total_pattern, fbarray(~empty_extent)

        words_to_pop = [word for word, extent in words_extents.items() if extent.count() < min_support]
        for word in words_to_pop:
            del words_extents[word]

        queue = deque([((word,), extent) for word, extent in words_extents.items() if not extent.all()])
        while queue:
            ngram, extent = queue.popleft()
            yield ngram, fbarray(extent)

            for word, word_extent in words_extents.items():
                next_extent = word_extent & extent
                if not next_extent.any() or next_extent.count() < min_support:
                    continue

                support_delta = next_extent.count() - max(min_support, 1)

                next_ngram = ngram + (word, )
                for i in next_extent.itersearch(True):
                    if self.is_less_precise({next_ngram}, data[i]):
                        continue

                    next_extent[i] = False
                    support_delta -= 1
                    if support_delta < 0:
                        break
                else:  # no break, i.e. enough support
                    queue.append((next_ngram, next_extent))

        if min_support == 0:
            yield None, fbarray(empty_extent)

    def is_less_precise(self, a: PatternType, b: PatternType) -> bool:
        """Return True if pattern `a` is less precise than pattern `b`"""
        b_texts_sizes = [(len(ngram), ' '.join(ngram)) for ngram in sorted(b, key=lambda ngram: len(ngram), reverse=True)]

        for smaller_tuple in a:
            smaller_text = ' '.join(smaller_tuple)
            smaller_size = len(smaller_tuple)

            inclusion_found = False
            for larger_size, larger_text in b_texts_sizes:
                if smaller_size > larger_size:
                    break

                if smaller_text in larger_text:
                    inclusion_found = True
                    break

            if not inclusion_found:
                return False

        return True

    def n_bin_attributes(self, data: list[PatternType], min_support: int = 0) -> int:
        """Count the number of attributes in the binary representation of `data`"""
        return sum(1 for _ in self.iter_bin_attributes(data, min_support))



class SynonymsPS(NgramPS):
    PatternType = set[tuple[str]]
    num_synonyms : int
    
    def __init__(self, num_synonyms = 1):
        self.num_synonyms = num_synonyms # number of synonyms for a word

    def get_synonyms(self, word):
      synonyms = set()
      for synset in wordnet.synsets(word):
          for lemma in synset.lemmas():
              synonyms.add(lemma.name())
              if self.num_synonyms is not None and len(synonyms) >= self.num_synonyms:
                  return synonyms
      return synonyms

    def get_synonyms_set_for_text(self, a: PatternType) -> PatternType:
      synonym_list = []
      words_list = list(a)[0]
      for i in range(len(words_list)):
          for synonym in list(self.get_synonyms(words_list[i], self.num_synonyms)):
            synonym_list.append(synonym)
      synonym_tuple = [tuple(synonym_list)]
      return(set(synonym_tuple))


    def join_synonyms_patterns(self, a: PatternType, b: PatternType) -> PatternType:
        """Return the common synonyms between both patterns `a` and `b`"""
        synonyms_text1 = self.get_synonyms_set_for_text(a, self.num_synonyms)
        synonyms_text2 = self.get_synonyms_set_for_text(b, self.num_synonyms)
        return(self.join_patterns(synonyms_text1, synonyms_text2))


    def n_bin_attributes(self, data: list[PatternType]) -> int:
        """Count the number of attributes in the binary representation of `data`"""
        n = 0
        for i in range(len(data)):
            n += len(list(list(data[i])[0]))
        return (n * (n + 1)) // 2


class AntonymsPS(NgramPS):
    PatternType = set[tuple[str]]
    num_antonyms : int
    
    def __init__(self, num_antonyms = 1):
        self.num_antonyms = num_antonyms

    def get_antonyms(self, word):
        antonyms = set()
        for synset in wordnet.synsets(word):
            for lemma in synset.lemmas():
                if lemma.antonyms():
                    antonyms.add(lemma.antonyms()[0].name())
                    if self.num_antonyms is not None and len(antonyms) >= self.num_antonyms:
                        return antonyms
        return antonyms


    def get_antonyms_set_for_text(self, a: PatternType) -> PatternType:
      antonyms_list = []
      words_list = list(a)[0]
      for i in range(len(words_list)):
          for antonym in list(self.get_antonyms(words_list[i], self.num_antonyms)):
            antonyms_list.append(antonym)
      antonyms_tuple = [tuple(antonyms_list)]
      return(set(antonyms_tuple))


    def join_antonyms_patterns(self, a: PatternType, b: PatternType) -> PatternType:
        """Return the common antonyms between both patterns `a` and `b`"""
        antonyms_text1 = self.get_antonyms_set_for_text(a, self.num_antonyms)
        antonyms_text2 = self.get_antonyms_set_for_text(b, self.num_antonyms)
        return(self.join_patterns(antonyms_text1, antonyms_text2))


    def n_bin_attributes(self, data: list[PatternType]) -> int:
        """Count the number of attributes in the binary representation of `data`"""
        n = 0
        for i in range(len(data)):
            n += len(list(list(data[i])[0]))
        return (n * (n + 1)) // 2










