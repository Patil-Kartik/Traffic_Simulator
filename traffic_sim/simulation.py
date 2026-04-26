from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, deque
import math
import random
import csv
import json

from .models import Junction, Road, Vehicle, TrafficSource, Sink
from .routing import shortest_path


@dataclass
class Snapshot:
    time: int
    vehicle_positions: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    vehicle_colors: Dict[str, str] = field(default_factory=dict)
    queue_lengths: Dict[str, int] = field(default_factory=dict)


class Simulation:
    def __init__(self):
        self.junctions: Dict[str, Junction] = {}
        self.roads: Dict[str, Road] = {}
        self.vehicles: Dict[str, Vehicle] = {}
        self.sources: List[TrafficSource] = []
        self.sinks: Dict[str, Sink] = {}
        self.time: int = 0
        self.next_vehicle_idx: int = 1
        self.snapshots: List[Snapshot] = []
        self.stats = {
            "generated": 0,
            "entered_network": 0,
            "exited_network": 0,
            "total_wait_time": 0.0,
            "total_travel_time": 0.0,
            "max_queue": 0,
        }

    def add_junction(self, jid: str, x: float, y: float):
        self.junctions[jid] = Junction(jid, x, y)

    def add_road(self, rid: str, start: str, end: str, length: Optional[float] = None,
                 capacity: int = 5, speed: float = 1.0):
        if length is None:
            x1, y1 = self.junctions[start].pos()
            x2, y2 = self.junctions[end].pos()
            length = math.hypot(x2 - x1, y2 - y1)
        self.roads[rid] = Road(rid=rid, start=start, end=end, length=float(length), capacity=capacity, speed=speed)
        self.junctions[start].outgoing_roads.append(rid)
        self.junctions[end].incoming_roads.append(rid)

    def add_sink(self, junction_id: str):
        self.sinks[junction_id] = Sink(junction_id)

    def add_source(self, junction_id: str, destination_id: str, rate: float = 1.0,
                   mode: str = "constant", color: str = "tab:blue", start_time: int = 0,
                   end_time: Optional[int] = None):
        self.sources.append(TrafficSource(junction_id, destination_id, rate, mode, color, start_time, end_time))

    def _edge_weights(self) -> Dict[Tuple[str, str], float]:
        return {(r.start, r.end): r.length for r in self.roads.values()}

    def route_vehicle(self, vehicle: Vehicle):
        node_path = shortest_path(
            {jid: j.pos() for jid, j in self.junctions.items()},
            self._edge_weights(),
            vehicle.source,
            vehicle.destination
        )
        road_path = []
        for u, v in zip(node_path[:-1], node_path[1:]):
            found = None
            for rid, road in self.roads.items():
                if road.start == u and road.end == v:
                    found = rid
                    break
            if found is None:
                raise ValueError(f"No road found for edge {u}->{v}")
            road_path.append(found)
        vehicle.route_nodes = node_path
        vehicle.route_roads = road_path
        vehicle.current_road_index = 0

    def _spawn_vehicle(self, source: TrafficSource):
        vid = f"V{self.next_vehicle_idx}"
        self.next_vehicle_idx += 1
        v = Vehicle(
            vid=vid,
            source=source.junction_id,
            destination=source.destination_id,
            created_time=self.time,
            color=source.color,
        )
        self.route_vehicle(v)
        v.entered_network_time = self.time
        self.vehicles[vid] = v
        self.stats["generated"] += 1
        self.stats["entered_network"] += 1
        self._try_enter_first_road(v)

    def _try_enter_first_road(self, vehicle: Vehicle):
        rid = vehicle.next_road_id()
        if rid is None:
            # source == destination
            vehicle.finished = True
            vehicle.exit_time = self.time
            self.stats["exited_network"] += 1
            self.sinks[vehicle.destination].received.append(vehicle.vid)
            return

        road = self.roads[rid]
        if road.can_enter():
            road.vehicles.append(vehicle.vid)
            vehicle.road_progress = 0.0
            vehicle.current_road_index = 0
        else:
            road.entry_queue.append(vehicle.vid)
            vehicle.waiting_since = self.time

    def _process_entry_queues(self):
        # Try to admit vehicles waiting at the start of roads.
        for road in self.roads.values():
            while road.entry_queue and road.can_enter():
                vid = road.entry_queue.popleft()
                vehicle = self.vehicles[vid]
                if vehicle.finished:
                    continue
                road.vehicles.append(vid)
                if vehicle.waiting_since is not None:
                    vehicle.total_wait_time += self.time - vehicle.waiting_since
                    vehicle.waiting_since = None

    def _advance_roads(self):
        # Move vehicles along each road.
        arrivals = defaultdict(list)  # junction -> [vehicle ids arriving at end]
        for rid, road in self.roads.items():
            if not road.vehicles:
                continue

            moved_ids = []
            for vid in list(road.vehicles):
                v = self.vehicles[vid]
                v.road_progress += road.travel_distance_per_step(1.0)
                if v.road_progress >= road.length:
                    moved_ids.append(vid)
                    arrivals[road.end].append(vid)

            for vid in moved_ids:
                road.vehicles.remove(vid)
                v = self.vehicles[vid]
                v.road_progress = road.length
        return arrivals

    def _next_road_for_vehicle(self, vehicle: Vehicle) -> Optional[str]:
        nxt = vehicle.current_road_index + 1
        if nxt < len(vehicle.route_roads):
            return vehicle.route_roads[nxt]
        return None

    def _process_junctions(self, arrivals: Dict[str, List[str]]):
        # Simple scheduler: each junction processes one vehicle per incoming road per step,
        # in a round-robin-like order over incoming roads.
        for jid, arriving_vids in arrivals.items():
            if jid in self.sinks:
                for vid in arriving_vids:
                    v = self.vehicles[vid]
                    if not v.finished:
                        v.finished = True
                        v.exit_time = self.time
                        v.total_travel_time = self.time - v.created_time
                        self.stats["exited_network"] += 1
                        self.stats["total_travel_time"] += v.total_travel_time
                        self.sinks[jid].received.append(vid)
                continue

            incoming_by_road = defaultdict(deque)
            for vid in arriving_vids:
                v = self.vehicles[vid]
                rid = v.route_roads[v.current_road_index]
                incoming_by_road[rid].append(vid)

            # Process roads in deterministic order for reproducibility.
            for in_rid in sorted(incoming_by_road.keys()):
                if not incoming_by_road[in_rid]:
                    continue
                vid = incoming_by_road[in_rid][0]
                v = self.vehicles[vid]
                next_rid = self._next_road_for_vehicle(v)

                if next_rid is None:
                    # Destination sink reached
                    v.finished = True
                    v.exit_time = self.time
                    v.total_travel_time = self.time - v.created_time
                    self.stats["exited_network"] += 1
                    self.stats["total_travel_time"] += v.total_travel_time
                    self.sinks.setdefault(jid, Sink(jid)).received.append(vid)
                    continue

                next_road = self.roads[next_rid]
                if next_road.can_enter():
                    next_road.vehicles.append(vid)
                    v.current_road_index += 1
                    v.road_progress = 0.0
                else:
                    next_road.entry_queue.append(vid)
                    v.current_road_index += 1
                    v.road_progress = 0.0
                    v.waiting_since = self.time

    def _snapshot(self):
        pos = {}
        cols = {}
        for rid, road in self.roads.items():
            if road.length <= 0:
                continue
            start = self.junctions[road.start].pos()
            end = self.junctions[road.end].pos()
            for vid in road.vehicles:
                v = self.vehicles[vid]
                frac = min(max(v.road_progress / road.length, 0.0), 1.0)
                x = start[0] + frac * (end[0] - start[0])
                y = start[1] + frac * (end[1] - start[1])
                pos[vid] = (x, y)
                cols[vid] = v.color
        self.snapshots.append(Snapshot(
            time=self.time,
            vehicle_positions=pos,
            vehicle_colors=cols,
            queue_lengths={rid: len(r.entry_queue) for rid, r in self.roads.items()}
        ))
        self.stats["max_queue"] = max(self.stats["max_queue"], max((len(r.entry_queue) for r in self.roads.values()), default=0))

    def step(self):
        # 1) Generate new vehicles.
        for src in self.sources:
            for _ in range(src.should_generate(self.time)):
                self._spawn_vehicle(src)

        # 2) Admit waiting vehicles if space is available.
        self._process_entry_queues()

        # 3) Advance road movement.
        arrivals = self._advance_roads()

        # 4) Process junction transitions.
        self._process_junctions(arrivals)

        # 5) Try again to admit queued vehicles created during junction processing.
        self._process_entry_queues()

        # 6) Snapshot.
        self._snapshot()

        # 7) Aggregate waiting stats.
        for v in self.vehicles.values():
            if v.waiting_since is not None and not v.finished:
                v.total_wait_time += 1.0

        self.time += 1

    def run(self, steps: int = 100):
        for _ in range(steps):
            self.step()

    def summary(self) -> Dict[str, float]:
        active = len([v for v in self.vehicles.values() if not v.finished])
        avg_tt = self.stats["total_travel_time"] / self.stats["exited_network"] if self.stats["exited_network"] else 0.0
        avg_wait = sum(v.total_wait_time for v in self.vehicles.values()) / len(self.vehicles) if self.vehicles else 0.0
        return {
            "generated": self.stats["generated"],
            "entered_network": self.stats["entered_network"],
            "exited_network": self.stats["exited_network"],
            "active": active,
            "avg_travel_time": avg_tt,
            "avg_wait_time": avg_wait,
            "max_queue": self.stats["max_queue"],
        }

    def save_stats_csv(self, path: str):
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            for k, v in self.summary().items():
                writer.writerow([k, v])

    def save_stats_json(self, path: str):
        with open(path, "w") as f:
            json.dump(self.summary(), f, indent=2)


