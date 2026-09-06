from __future__ import annotations

from typing import Dict

from .algo import CPFBlockAlgo
from .algo import HEFTBlockAlgo
from .algo import TLevelBlockAlgo
from .algo import WCETFirstBlockAlgo
from .algo import Zhao2020BlockAlgo
from .algo.base import AlgoPlugin

ALGO_REGISTRY: Dict[str, AlgoPlugin] = {
    "LPF": CPFBlockAlgo(),
    "FIFO": WCETFirstBlockAlgo(),
    "heft": HEFTBlockAlgo(),
    "t_level": TLevelBlockAlgo(),
    "zhao2020": Zhao2020BlockAlgo(),
}


def list_algos() -> Dict[str, AlgoPlugin]:
    return dict(ALGO_REGISTRY)


def get_algo(algo_name: str) -> AlgoPlugin:
    if algo_name not in ALGO_REGISTRY:
        known = ", ".join(sorted(ALGO_REGISTRY.keys())) if ALGO_REGISTRY else "(none)"
        raise KeyError(f"unknown algo '{algo_name}'; known: {known}")
    return ALGO_REGISTRY[algo_name]
