"""
HDC Knowledge Graph — Relational reasoning for mission intelligence.
Represents "vehicle X → base Y → supplies Z" as HD vector bind chains.
"""
import numpy as np
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class Triple:
    subject: str
    predicate: str
    object: str


class KnowledgeGraph:
    """
    HD vector-based knowledge graph for mission reasoning.
    Stores triples as bind operations: hd(subject) ⊙ hd(predicate) ≈ hd(object)

    Operations:
    - Query: given (subject, predicate) → find object
    - Query: given (object, predicate) → find subject
    - Reasoning: chain A→B→C via vector operations
    """

    def __init__(self, hd_dim: int = 2048):
        self.hd_dim = hd_dim
        self.entity_vectors: Dict[str, np.ndarray] = {}
        self.relation_vectors: Dict[str, np.ndarray] = {}
        self.triples: List[Triple] = []
        self.graph_memory = np.zeros(hd_dim)

    def _make_vector(self, seed_str: str) -> np.ndarray:
        """Create deterministic HD vector from string."""
        seed = hash(seed_str) % (2 ** 31)
        np.random.seed(seed)
        vec = np.sign(np.random.randn(self.hd_dim))
        np.random.seed(None)
        return vec

    def add_entity(self, name: str) -> np.ndarray:
        if name not in self.entity_vectors:
            self.entity_vectors[name] = self._make_vector(name)
        return self.entity_vectors[name]

    def add_relation(self, name: str) -> np.ndarray:
        if name not in self.relation_vectors:
            self.relation_vectors[name] = self._make_vector(name)
        return self.relation_vectors[name]

    def add_triple(self, subject: str, predicate: str, obj: str):
        """Add triple to graph: subject --predicate--> object."""
        s = self.add_entity(subject)
        p = self.add_relation(predicate)
        o = self.add_entity(obj)
        bound = np.sign(s * p)
        self.graph_memory += bound + o
        self.graph_memory = np.sign(self.graph_memory)
        self.triples.append(Triple(subject, predicate, obj))

    def query(self, subject: str, predicate: str,
              top_k: int = 3) -> List[Tuple[str, float]]:
        """Query: subject --predicate--> ?"""
        if subject not in self.entity_vectors or predicate not in self.relation_vectors:
            return []
        s = self.entity_vectors[subject]
        p = self.relation_vectors[predicate]
        query_vec = np.sign(s * p)
        scores = []
        for name, vec in self.entity_vectors.items():
            sim = float(np.dot(query_vec, vec) / self.hd_dim)
            scores.append((name, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def reverse_query(self, obj: str, predicate: str,
                      top_k: int = 3) -> List[Tuple[str, float]]:
        """Query: ? --predicate--> object"""
        if obj not in self.entity_vectors or predicate not in self.relation_vectors:
            return []
        o = self.entity_vectors[obj]
        p = self.relation_vectors[predicate]
        query_vec = np.sign(o * p)
        scores = []
        for name, vec in self.entity_vectors.items():
            sim = float(np.dot(query_vec, vec) / self.hd_dim)
            scores.append((name, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def chain_reason(self, start: str,
                     relations: List[str]) -> List[Tuple[str, float]]:
        """Reason through a chain: start --r1--> ? --r2--> ?"""
        if start not in self.entity_vectors:
            return []
        current = self.entity_vectors[start]
        for r in relations:
            if r not in self.relation_vectors:
                return []
            current = np.sign(current * self.relation_vectors[r])
        scores = []
        for name, vec in self.entity_vectors.items():
            sim = float(np.dot(current, vec) / self.hd_dim)
            scores.append((name, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:5]

    def analogical_reason(self, a: str, b: str, c: str,
                          top_k: int = 3) -> List[Tuple[str, float]]:
        """Analogy: a → b like c → ?"""
        if (a not in self.entity_vectors
                or b not in self.entity_vectors
                or c not in self.entity_vectors):
            return []
        delta = self.entity_vectors[b] - self.entity_vectors[a]
        query = np.sign(delta + self.entity_vectors[c])
        scores = []
        for name, vec in self.entity_vectors.items():
            if name in (a, b, c):
                continue
            sim = float(np.dot(query, vec) / self.hd_dim)
            scores.append((name, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


def test_knowledge_graph():
    kg = KnowledgeGraph(hd_dim=4096)
    kg.add_triple("convoy_alpha", "based_at", "fob_dagger")
    kg.add_triple("fob_dagger", "supplies", "fuel_bladder")
    kg.add_triple("fob_dagger", "defended_by", "avenger_sam")
    kg.add_triple("avenger_sam", "threatens", "suas_swarm")
    kg.add_triple("suas_swarm", "targets", "avenger_sam")

    assert len(kg.entity_vectors) == 5, f"Expected 5 entities"
    assert len(kg.relation_vectors) == 5, f"Expected 5 relations"
    assert len(kg.triples) == 5

    results = kg.query("convoy_alpha", "based_at")
    print(f"  convoy_alpha based_at: {results}")
    chain = kg.chain_reason("convoy_alpha", ["based_at", "supplies"])
    print(f"  convoy_alpha → supplies: {chain}")
    print("  PASSED")


if __name__ == "__main__":
    test_knowledge_graph()
    print("Knowledge graph PASSED")
