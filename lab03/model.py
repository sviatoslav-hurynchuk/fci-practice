import json
import os
from typing import Optional


class BattleshipBoard:
    def __init__(self, field_size: int, ships: list[int], reefs: list[list[int]]):
        self.field_size = field_size
        self.ships = list(ships)
        self.reefs = set((r[0], r[1]) for r in reefs)
        self._validate_input()

    def _validate_input(self):
        for rx, ry in self.reefs:
            if not (0 <= rx < self.field_size and 0 <= ry < self.field_size):
                raise ValueError(f"Reef ({rx}, {ry}) out of field bounds {self.field_size}x{self.field_size}")
        for s in self.ships:
            if s <= 0 or s > self.field_size:
                raise ValueError(f"Ship length {s} invalid for field size {self.field_size}")

    @classmethod
    def from_json(cls, filepath: str) -> "BattleshipBoard":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            field_size=data["field_size"],
            ships=data["ships"],
            reefs=data["reefs"]
        )

    def get_ship_cells(self, x: int, y: int, ori: int, length: int) -> list[tuple[int, int]]:
        if ori == 0:
            return [(x + i, y) for i in range(length)]
        else:
            return [(x, y + i) for i in range(length)]

    def evaluate(self, chromosome: list[tuple[int, int, int]]) -> dict:
        reef_hits = 0
        ship_cells_list = []
        bounds_violations = 0

        for i, (x, y, ori) in enumerate(chromosome):
            length = self.ships[i]
            cells = self.get_ship_cells(x, y, ori, length)
            for cx, cy in cells:
                if not (0 <= cx < self.field_size and 0 <= cy < self.field_size):
                    bounds_violations += 1
                elif (cx, cy) in self.reefs:
                    reef_hits += 1
            ship_cells_list.append(cells)

        overlaps = 0
        touches = 0
        k = len(self.ships)

        for i in range(k):
            cells_i = ship_cells_list[i]
            for j in range(i + 1, k):
                cells_j = ship_cells_list[j]
                for xi, yi in cells_i:
                    for xj, yj in cells_j:
                        dx = abs(xi - xj)
                        dy = abs(yi - yj)
                        if dx == 0 and dy == 0:
                            overlaps += 1
                        elif max(dx, dy) == 1:
                            touches += 1

        total_violations = bounds_violations * 10 + reef_hits * 3 + overlaps * 5 + touches * 2
        fitness = 1000.0 / (1.0 + total_violations)
        energy = float(total_violations)
        is_valid = (total_violations == 0)

        return {
            "violations": total_violations,
            "bounds": bounds_violations,
            "reef_hits": reef_hits,
            "overlaps": overlaps,
            "touches": touches,
            "fitness": fitness,
            "energy": energy,
            "is_valid": is_valid,
            "ship_cells": ship_cells_list
        }
