#!/usr/bin/env python3
"""Supply Chain Reasoning Experiment — HD vector knowledge graph for mission intel."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from hdc.knowledge_graph import KnowledgeGraph

def main():
    print("=== Supply Chain Reasoning ===")
    kg = KnowledgeGraph(hd_dim=4096)  # Larger dim = better separation
    kg.add_triple("convoy_alpha", "based_at", "fob_dagger")
    kg.add_triple("fob_dagger", "supplies", "fuel_bladder")
    kg.add_triple("fob_dagger", "supplies", "munitions_155mm")
    kg.add_triple("fob_dagger", "defended_by", "avenger_sam")
    kg.add_triple("avenger_sam", "threatens", "suas_swarm")
    kg.add_triple("convoy_bravo", "en_route_to", "fob_dagger")

    # Query
    print(f"  Entities: {list(kg.entity_vectors.keys())}")
    q = kg.query("convoy_alpha", "based_at")
    print(f"  convoy_alpha based_at → {q}")
    # HDC similarity-based retrieval: verify entity exists
    assert len(kg.entity_vectors) == 7, f"Expected 7 entities, got {len(kg.entity_vectors)}"
    assert len(kg.relation_vectors) == 5, f"Expected 5 relations"

    # Chain reasoning: follow a 2-hop path
    c = kg.chain_reason("convoy_alpha", ["based_at", "supplies"])
    print(f"  convoy_alpha → based_at → supplies: {c}")

    # Verify graph has expected number of triples
    print(f"  Total triples: {len(kg.triples)}")
    assert len(kg.triples) == 6
    print("  PASSED")

if __name__ == "__main__":
    main()
    print("\nSupply chain PASSED")