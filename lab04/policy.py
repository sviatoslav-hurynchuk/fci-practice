import json
import math
import os


class TabularPolicy:
    def __init__(self, chromosome: list = None, mode: str = "separate"):
        self.mode = mode
        if chromosome is None:
            self.chromosome = self.get_default_chromosome(mode)
        else:
            self.chromosome = list(chromosome)
        self._unpack()

    @staticmethod
    def get_default_chromosome(mode: str = "separate") -> list:
        if mode == "separate":
            turn_table = [0, -1, -1, 1, 0, -1, 1, 1, 0]
            thrust_table = [0, 1, 1, 0, -1, -1]
            reals = [0.045, 0.09, 2.2, 7.5, 0.34, 0.38]
            return turn_table + thrust_table + reals
        else:
            single_table = [0] * 54
            reals = [0.045, 0.09, 2.2, 7.5, 0.34, 0.38]
            return single_table + reals

    def _unpack(self):
        if self.mode == "separate":
            self.turn_table = [int(x) for x in self.chromosome[0:9]]
            self.thrust_table = [int(x) for x in self.chromosome[9:15]]
            reals = self.chromosome[15:21]
        else:
            self.single_table = [int(x) for x in self.chromosome[0:54]]
            reals = self.chromosome[54:60]

        self.a = float(reals[0])
        self.w = float(reals[1])
        self.e1 = float(reals[2])
        self.e2 = float(reals[3])
        self.T = float(reals[4])
        self.k_h = float(reals[5])

    def get_features(self, state: dict) -> tuple:
        ship = state["ship"]
        station = state["station"]
        debris = state["debris"]

        pad_x = station["x"]
        pad_y = station["y"]

        dx_deb = debris["x"] - ship["x"]
        dy_deb = debris["y"] - ship["y"]
        dist_deb = math.hypot(dx_deb, dy_deb)

        target_x = pad_x
        if ship["y"] > debris["y"] - 25 and dist_deb < debris["r"] + 75:
            if pad_x > debris["x"]:
                target_x = max(debris["x"] + debris["r"] + 58, pad_x)
            else:
                target_x = min(debris["x"] - debris["r"] - 58, pad_x)

        dx = target_x - ship["x"]

        if ship["y"] > 180:
            des_vx = max(-38.0, min(38.0, dx * self.k_h))
        else:
            des_vx = max(-5.5, min(5.5, (pad_x - ship["x"]) * 0.42))

        evx = des_vx - ship["vx"]

        tilt = max(-0.28, min(0.28, evx * 0.016))
        if ship["y"] < 90:
            tilt = max(-0.07, min(0.07, (pad_x - ship["x"]) * 0.005 - ship["vx"] * 0.012))

        psi_star = math.pi / 2 - tilt

        pred_theta = ship["angle"] + ship["omega"] * self.T
        delta = psi_star - pred_theta
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta <= -math.pi:
            delta += 2 * math.pi

        l_delta = 0 if delta < -self.a else (2 if delta > self.a else 1)
        l_omega = 0 if ship["omega"] < -self.w else (2 if ship["omega"] > self.w else 1)

        if ship["y"] > 250:
            des_vy = -18.0
        elif ship["y"] > 100:
            des_vy = -10.0
        else:
            des_vy = -5.0

        evy = des_vy - ship["vy"]
        l_dir = 0 if evy >= 0 else 1
        abs_evy = abs(evy)

        if abs_evy < self.e1:
            l_mag = 0
        elif abs_evy < self.e2:
            l_mag = 1
        else:
            l_mag = 2

        return l_delta, l_omega, l_dir, l_mag, evx, evy, tilt

    def get_action(self, state: dict) -> tuple[int, int]:
        l_delta, l_omega, l_dir, l_mag, evx, evy, tilt = self.get_features(state)
        ship = state["ship"]

        if self.mode == "separate":
            turn_idx = l_delta * 3 + l_omega
            turn = self.turn_table[turn_idx]

            thrust_idx = l_dir * 3 + l_mag
            thrust = self.thrust_table[thrust_idx]
        else:
            cell_idx = (l_delta * 3 + l_omega) * 6 + (l_dir * 3 + l_mag)
            action_code = self.single_table[cell_idx]
            thrust = (action_code // 3) - 1
            turn = (action_code % 3) - 1

        if ship["y"] > 150:
            if ship["vy"] < -22.0:
                thrust = 1
            elif ship["vy"] > -8.0:
                thrust = -1
            elif abs(evx) > 14.0 and abs(tilt) > 0.08:
                thrust = 1
        elif ship["y"] > 80:
            if ship["vy"] < -12.0:
                thrust = 1
            elif ship["vy"] > -5.0:
                thrust = -1
            elif abs(evx) > 6.0 and abs(tilt) > 0.05:
                thrust = 1
        else:
            if ship["y"] < 58:
                if ship["vy"] < -7.0:
                    thrust = 1
                elif ship["vy"] > -2.0 and ship["y"] > 52:
                    thrust = -1
            elif abs(ship["vx"]) > 4.5:
                thrust = 1

        return int(thrust), int(turn)

    def to_dict(self) -> dict:
        data = {
            "mode": self.mode,
            "chromosome": self.chromosome,
            "params": {
                "a": self.a,
                "w": self.w,
                "e1": self.e1,
                "e2": self.e2,
                "T": self.T,
                "k_h": self.k_h
            }
        }
        if self.mode == "separate":
            data["turn_table"] = self.turn_table
            data["thrust_table"] = self.thrust_table
        else:
            data["single_table"] = self.single_table
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "TabularPolicy":
        return cls(chromosome=data["chromosome"], mode=data.get("mode", "separate"))

    def save_json(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_json(cls, filepath: str) -> "TabularPolicy":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
