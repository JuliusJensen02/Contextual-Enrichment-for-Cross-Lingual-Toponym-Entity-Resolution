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

    # False: the method gets normalised names, or the phonetic encodings when the generator has
    #        them (the letter-based methods).
    # True:  the method always gets the names as written (language models want raw text).
    raw_names: bool = False

    @abstractmethod
    def candidates(self, source: dict, target: dict) -> set:
        """source, target: {name_id: name}. Returns a set of (source name_id, target name_id)."""
