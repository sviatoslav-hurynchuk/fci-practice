from lab04.client import DockSimClient


class ManualController:
    @staticmethod
    def keys_to_action(keys: list[str]) -> tuple[int, int]:
        thrust = 0
        turn = 0
        if "up" in keys and "down" not in keys:
            thrust = 1
        elif "down" in keys and "up" not in keys:
            thrust = -1

        if "left" in keys and "right" not in keys:
            turn = 1
        elif "right" in keys and "left" not in keys:
            turn = -1

        return thrust, turn

    @classmethod
    def run_session(cls, client: DockSimClient, max_episodes: int = 10, seed_start: int = None, callback=None):
        results = []
        ep_count = 0
        while ep_count < max_episodes:
            seed = None if seed_start is None else (seed_start + ep_count)
            try:
                state = client.reset(seed)
            except Exception:
                break
            ep_count += 1
            if callback:
                callback("episode_start", {"episode": ep_count, "state": state})

            while not state.get("done", False):
                keys = state.get("keys", [])
                thrust, turn = cls.keys_to_action(keys)
                if client.realtime:
                    client.step(thrust, turn)
                    try:
                        state = client.recv()
                    except ConnectionError:
                        break
                else:
                    state = client.step(thrust, turn)
                if callback:
                    callback("step", {"state": state, "action": (thrust, turn)})

            results.append(state)
            if callback:
                callback("episode_end", {"episode": ep_count, "state": state})
            if client.last_report:
                break

        return results
