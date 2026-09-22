"""Degree statistics."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DegreeStats:
    vertices: int
    edges: int
    min_degree: int
    max_degree: int
    mean_degree: float
    median_degree: float

    @classmethod
    def of(cls, graph) -> "DegreeStats":
        d = sorted(graph.degrees())
        n = len(d)
        median = d[n // 2] if n % 2 else (d[n // 2 - 1] + d[n // 2]) / 2
        return cls(graph.n, graph.m, d[0], d[-1], sum(d) / n, median)
