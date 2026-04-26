from __future__ import annotations

from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple
from collections import deque
import math
import random


@dataclass
class Junction:
    """A junction/node in the road network."""
    jid: str
    x: float
    y: float
    incoming_roads: List[str] = field(default_factory=list)
    outgoing_roads: List[str] = field(default_factory=list)

    def pos(self) -> Tuple[float, float]:
        return self.x, self.y


@dataclass
class Road:
    """Directional road from start_junction to end_junction."""
    rid: str
    start: str
    end: str
    length: float
    capacity: int = 5
    speed: float = 1.0
    vehicles: List[str] = field(default_factory=list)  # vehicle ids in road order
    # Vehicles waiting to enter at start if road is full
    entry_queue: Deque[str] = field(default_factory=deque)

    def free_space(self) -> int:
        return max(0, self.capacity - len(self.vehicles))

    def can_enter(self) -> bool:
        return len(self.vehicles) < self.capacity

    def travel_distance_per_step(self, dt: float = 1.0) -> float:
        return self.speed * dt


@dataclass
class Vehicle:
    vid: str
    source: str
    destination: str
    created_time: int
    color: str = "tab:blue"
    route_nodes: List[str] = field(default_factory=list)   # junction path
    route_roads: List[str] = field(default_factory=list)   # road id path
    current_road_index: int = 0
    road_progress: float = 0.0
    entered_network_time: Optional[int] = None
    exit_time: Optional[int] = None
    finished: bool = False
    waiting_since: Optional[int] = None
    total_wait_time: float = 0.0
    total_travel_time: float = 0.0

    def next_road_id(self) -> Optional[str]:
        if self.current_road_index < len(self.route_roads):
            return self.route_roads[self.current_road_index]
        return None

    def next_junction(self) -> Optional[str]:
        if self.current_road_index + 1 < len(self.route_nodes):
            return self.route_nodes[self.current_road_index + 1]
        return None


@dataclass
class TrafficSource:
    """Generates vehicles at a source junction."""
    junction_id: str
    destination_id: str
    rate: float = 1.0
    mode: str = "constant"  # constant or poisson
    color: str = "tab:blue"
    start_time: int = 0
    end_time: Optional[int] = None
    _carry: float = 0.0

    def should_generate(self, t: int) -> int:
        if t < self.start_time:
            return 0
        if self.end_time is not None and t > self.end_time:
            return 0

        if self.mode == "constant":
            self._carry += self.rate
            n = int(self._carry)
            self._carry -= n
            return n

        if self.mode == "poisson":
            # For educational toy simulator: use a Bernoulli approximation per step.
            # For rate > 1, generate floor(rate) + Bernoulli(frac).
            base = int(self.rate)
            frac = self.rate - base
            n = base + (1 if random.random() < frac else 0)
            return n

        return 0


@dataclass
class Sink:
    junction_id: str
    received: List[str] = field(default_factory=list)
