"""Connected components."""
from collections import deque
from typing import List


def connected_components(graph) -> List[List[int]]:
    """Components in decreasing order of size."""
    seen = bytearray(graph.n + 1)
    components = []
    for s in graph.vertices():
        if seen[s]:
            continue
        seen[s] = 1
        component, queue = [s], deque([s])
        while queue:
            for v in graph.neighbors(queue.popleft()):
                if not seen[v]:
                    seen[v] = 1
                    component.append(v)
                    queue.append(v)
        components.append(component)
    components.sort(key=len, reverse=True)
    return components
