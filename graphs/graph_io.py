"""Text-file input and output."""
from .degree_stats import DegreeStats
from .graph import Graph


class GraphReader:
    @staticmethod
    def read(path: str, representation: str = "list") -> Graph:
        with open(path) as f:
            n = int(f.readline())
            edges = (tuple(map(int, line.split()[:2])) for line in f if line.strip())
            return Graph(n, edges, representation)


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
