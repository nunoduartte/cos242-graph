"""Text-file input and output."""
from typing import Dict, List, Optional

from .degree_stats import DegreeStats
from .graph import Graph


class GraphReader:
    @staticmethod
    def read(path: str, representation: str = "list", weighted: Optional[bool] = None) -> Graph:
        """First line: number of vertices; then one edge per line, "u v" or "u v w".

        `weighted=None` detects it from the first edge line (3 columns = weighted).
        The file is streamed line by line, never held in memory as a whole.
        """
        with open(path) as f:
            n = GraphReader._parse_n(f.readline(), path)
            first = GraphReader._first_edge_line(f)
            if weighted is None:
                weighted = first is not None and len(first.split()) >= 3
            edges = GraphReader._edges(f, first, weighted, path)
            return Graph(n, edges, representation, weighted)

    @staticmethod
    def _parse_n(line: str, path: str) -> int:
        try:
            n = int(line)
        except ValueError:
            raise ValueError(f"{path}:1: expected the number of vertices, got {line.strip()!r}")
        if n < 0:
            raise ValueError(f"{path}:1: negative number of vertices {n}")
        return n

    @staticmethod
    def _first_edge_line(f):
        for line in f:
            if line.strip():
                return line
        return None

    @staticmethod
    def _edges(f, first, weighted, path):
        if first is None:
            return
        lineno = 2
        try:
            for lineno, line in enumerate(_chain_first(first, f), 2):
                parts = line.split()
                if not parts:
                    continue
                if weighted:
                    a, b, c = parts  # exactly 3 columns
                    yield int(a), int(b), float(c)
                else:
                    yield int(parts[0]), int(parts[1])
        except (ValueError, IndexError) as e:
            # the line number is approximate when blank lines precede the first edge
            raise ValueError(f"{path}:{lineno}: invalid edge line ({e})") from None


def _chain_first(first, rest):
    yield first
    yield from rest


class VertexLabels:
    """Names of the vertices, read from "id,name" lines (UTF-8).

    Only the first comma separates the id, so names may contain spaces or commas.
    """

    def __init__(self, names: Dict[int, str]):
        self._name = names
        self._id = {name: v for v, name in names.items()}

    @classmethod
    def read(cls, path: str) -> "VertexLabels":
        names = {}
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.rstrip("\r\n")
                if not line:
                    continue
                vid, sep, name = line.partition(",")
                if not sep:
                    raise ValueError(f"{path}:{lineno}: expected 'id,name', got {line!r}")
                names[int(vid)] = name
        return cls(names)

    def name(self, v: int) -> str:
        return self._name[v]

    def id_of(self, name: str) -> Optional[int]:
        """Vertex with exactly this name, or None."""
        return self._id.get(name)

    def names(self, vertices: List[int]) -> List[str]:
        return [self._name[v] for v in vertices]

    def __len__(self):
        return len(self._name)


class ReportWriter:
    @staticmethod
    def summary(graph: Graph, path: str, components=None) -> None:
        s = DegreeStats.of(graph)
        components = components or graph.connected_components()
        with open(path, "w") as f:
            f.write(f"Number of vertices: {s.vertices}\n"
                    f"Number of edges: {s.edges}\n"
                    f"Minimum degree: {s.min_degree}\n"
                    f"Maximum degree: {s.max_degree}\n"
                    f"Mean degree: {s.mean_degree:.4f}\n"
                    f"Median degree: {s.median_degree}\n"
                    f"Number of connected components: {len(components)}\n")
            for i, c in enumerate(components, 1):
                f.write(f"Component {i} (size {len(c)}): {' '.join(map(str, sorted(c)))}\n")

    @staticmethod
    def tree(result, name: str, path: str) -> None:
        with open(path, "w") as f:
            f.write(f"# {name} from {result.root}: vertex parent level\n")
            for v, level in enumerate(result.level):
                if v and level >= 0:
                    f.write(f"{v} {result.parent[v] or '-'} {level}\n")
