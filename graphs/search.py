"""Search algorithms (Strategy): BFS and DFS share the same interface."""
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import List


@dataclass
class SearchResult:
    """Search tree: parent[v] (0 for the root) and level[v] (-1 if unreached)."""
    root: int
    parent: List[int]
    level: List[int]

    def farthest(self) -> int:
        return max(range(1, len(self.level)), key=self.level.__getitem__)

    def eccentricity(self) -> int:
        return self.level[self.farthest()]


class Search(ABC):
    name = ""

    def run(self, graph, root: int) -> SearchResult:
        parent = [-1] * (graph.n + 1)
        level = [-1] * (graph.n + 1)
        parent[root], level[root] = 0, 0
        self._traverse(graph, root, parent, level)
        return SearchResult(root, parent, level)

    @abstractmethod
    def _traverse(self, graph, root, parent, level) -> None:
        ...


class BFS(Search):
    name = "BFS"

    def _traverse(self, graph, root, parent, level):
        queue = deque([root])
        while queue:
            u = queue.popleft()
            for v in graph.neighbors(u):
                if level[v] < 0:
                    level[v], parent[v] = level[u] + 1, u
                    queue.append(v)


class DFS(Search):
    """Iterative DFS (avoids Python's recursion limit)."""
    name = "DFS"

    def _traverse(self, graph, root, parent, level):
        stack = [(root, iter(graph.neighbors(root)))]
        while stack:
            u, it = stack[-1]
            for v in it:
                if level[v] < 0:
                    level[v], parent[v] = level[u] + 1, u
                    stack.append((v, iter(graph.neighbors(v))))
                    break
            else:
                stack.pop()
