def cross_correlate(signal: list[float], pulse: list[float]) -> list[float]:
    n = len(signal)
    m = len(pulse)
    corr = []
    for k in range(n - m + 1):
        dot = 0.0
        for j in range(m):
            dot += signal[k + j] * pulse[j]
        corr.append(dot)
    return corr


def find_peak_delay_and_depth(correlation: list[float], sample_rate: float, sound_speed: float):
    k_max = 0
    max_val = correlation[0]
    for k in range(1, len(correlation)):
        if correlation[k] > max_val:
            max_val = correlation[k]
            k_max = k
    delay_time = k_max / sample_rate
    depth = (delay_time * sound_speed) / 2.0
    return k_max, max_val, delay_time, depth


def average_signals(signals_list: list[list[float]]) -> list[float]:
    count = len(signals_list)
    length = len(signals_list[0])
    avg = [0.0] * length
    for sig in signals_list:
        for i in range(length):
            avg[i] += sig[i]
    return [v / count for v in avg]


def calculate_max_depth(signal_len: int, pulse_len: int, sample_rate: float, sound_speed: float) -> dict:
    k_limit = signal_len - pulse_len
    t_max = k_limit / sample_rate
    h_max = (t_max * sound_speed) / 2.0
    return {
        "signal_len": signal_len,
        "pulse_len": pulse_len,
        "k_limit": k_limit,
        "t_max": t_max,
        "h_max": h_max
    }


class SonarProcessor:
    def __init__(self, sample_rate: float, sound_speed: float, pulse: list[float]):
        self.sample_rate = sample_rate
        self.sound_speed = sound_speed
        self.pulse = pulse
        self.pulse_len = len(pulse)

    def calculate_max_depth(self, signal_len: int) -> dict:
        return calculate_max_depth(signal_len, self.pulse_len, self.sample_rate, self.sound_speed)

    def process_signal(self, signal: list[float]) -> dict:
        corr = cross_correlate(signal, self.pulse)
        k_max, max_r, delay_t, depth = find_peak_delay_and_depth(
            corr, self.sample_rate, self.sound_speed
        )
        return {
            "correlation": corr,
            "k_max": k_max,
            "max_r": max_r,
            "delay_time": delay_t,
            "depth": depth
        }

    def process_step(self, signals_list: list[list[float]]) -> dict:
        single_res = self.process_signal(signals_list[0])
        avg_signal = average_signals(signals_list)
        avg_res = self.process_signal(avg_signal)
        return {
            "single": single_res,
            "averaged": avg_res,
            "single_signal": signals_list[0],
            "averaged_signal": avg_signal
        }
