"""The interface every blocking method implements."""
from abc import ABC, abstractmethod


class BlockingMethod(ABC):
    """One way of deciding which names are worth comparing.

    A method only ever sees names: {name_id: name} for the source and for the target side. It
    returns the (source name_id, target name_id) pairs it considers candidates. Everything
    around that (picking the names out of the records, turning name pairs into record pairs,
    the geo restriction) is done by the CandidateGenerator the method is injected into.

    A method's parameters (q, tau, k, ...) are set in its constructor.
    """

    name: str  # label used on the command line and in result tables

    # False: the method gets the normalised phonetic (IPA) encodings of the names, or the
    #        normalised names when the generator has phonetic switched off (the letter-based
    #        methods).
    # True:  the method gets the names as written (language models want raw text).
    raw_names: bool = False

    # True:  `candidates` takes `blocked` and leaves out the pairs the geo filter rules out
    #        BEFORE it picks its candidates (the nearest-neighbour methods: their k neighbours
    #        are then the k best among the places that are close enough).
    # False: the generator removes those pairs from the method's candidates afterwards. For a
    #        method that decides about each pair on its own that gives the same result.
    geo_first: bool = False

    @abstractmethod
    def candidates(self, source: dict, target: dict) -> set:
        """source, target: {name_id: name}. Returns a set of (source name_id, target name_id)."""
