from abc import ABC, abstractmethod

INF = float("inf")


class PriorityQueue(ABC):
    """Queue of vertices 1..n, each present at most once."""
    name = ""

    def __init__(self, n: int):
        self.n = n

    @abstractmethod
    def insert(self, v: int, key: float) -> None:
        """Add v, which must not be in the queue, with priority `key`."""

    @abstractmethod
    def decrease_key(self, v: int, key: float) -> None:
        """Lower the priority of v, which must be in the queue."""

    @abstractmethod
    def pop_min(self) -> int:
        """Remove and return a vertex of smallest key."""

    @abstractmethod
    def __len__(self) -> int:
        ...


class VectorQueue(PriorityQueue):
    name = "vector"

    def __init__(self, n):
        super().__init__(n)
        self._key = [INF] * (n + 1)
        self._size = 0

    def insert(self, v, key):
        self._key[v] = key
        self._size += 1

    def decrease_key(self, v, key):
        self._key[v] = key

    def pop_min(self):
        key = self._key
        v = key.index(min(key))  # two linear scans of the vector
        key[v] = INF
        self._size -= 1
        return v

    def __len__(self):
        return self._size


class IndexedMinHeap(PriorityQueue):
    name = "heap"

    def __init__(self, n):
        super().__init__(n)
        self._heap = []
        self._pos = [-1] * (n + 1)
        self._key = [INF] * (n + 1)

    def insert(self, v, key):
        self._key[v] = key
        self._heap.append(v)
        self._sift_up(len(self._heap) - 1)

    def decrease_key(self, v, key):
        if key > self._key[v]:
            raise ValueError(f"new key {key} is larger than the current key of {v}")
        self._key[v] = key
        self._sift_up(self._pos[v])

    def pop_min(self):
        heap, pos = self._heap, self._pos
        top = heap[0]
        last = heap.pop()
        pos[top] = -1
        if heap:
            heap[0] = last
            self._sift_down(0)
        return top

    def __len__(self):
        return len(self._heap)

    def __contains__(self, v):
        return self._pos[v] >= 0

    def _sift_up(self, i):
        heap, pos, key = self._heap, self._pos, self._key
        v = heap[i]
        k = key[v]
        while i > 0:
            parent = (i - 1) >> 1
            p = heap[parent]
            if key[p] <= k:
                break
            heap[i] = p
            pos[p] = i
            i = parent
        heap[i] = v
        pos[v] = i

    def _sift_down(self, i):
        heap, pos, key = self._heap, self._pos, self._key
        size = len(heap)
        v = heap[i]
        k = key[v]
        while True:
            child = 2 * i + 1
            if child >= size:
                break
            c = heap[child]
            right = child + 1
            if right < size and key[heap[right]] < key[c]:
                child = right
                c = heap[right]
            if k <= key[c]:
                break
            heap[i] = c
            pos[c] = i
            i = child
        heap[i] = v
        pos[v] = i


QUEUES = {"vector": VectorQueue, "heap": IndexedMinHeap}
