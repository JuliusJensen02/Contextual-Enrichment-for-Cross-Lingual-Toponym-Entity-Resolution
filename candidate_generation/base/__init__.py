"""What the blocking methods in methods/ are built on: the interface (BlockingMethod) and the
shared base class of the nearest-neighbour methods (KNNMethod)."""
from .blocking_method import BlockingMethod
from .knn_method import KNNMethod

__all__ = ["BlockingMethod", "KNNMethod"]
