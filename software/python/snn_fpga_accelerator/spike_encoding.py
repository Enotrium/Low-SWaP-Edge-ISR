"""Spike event encoding for the SNN accelerator."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SpikeEvent:
    """A single spike event for the SNN."""
    neuron_id: int
    timestamp: float
    weight: float = 1.0


class SpikeEncoder:
    """Encode sensor data into spike trains."""

    @staticmethod
    def rate_encode(values: List[float], num_neurons: int,
                    time_window_ms: float = 100.0) -> List[SpikeEvent]:
        """Rate-based encoding: probability of spiking proportional to value."""
        import random
        spikes = []
        for i, val in enumerate(values[:num_neurons]):
            if val > 0 and random.random() < min(val, 1.0):
                for t in range(int(time_window_ms)):
                    spikes.append(SpikeEvent(
                        neuron_id=i,
                        timestamp=t / 1000.0,  # Convert to seconds
                        weight=val
                    ))
        return spikes

    @staticmethod
    def latency_encode(values: List[float], num_neurons: int,
                       time_window_ms: float = 100.0) -> List[SpikeEvent]:
        """Latency encoding: spike time inversely proportional to value."""
        spikes = []
        for i, val in enumerate(values[:num_neurons]):
            if val > 0:
                latency = int(time_window_ms * (1.0 - min(val, 1.0)))
                spikes.append(SpikeEvent(
                    neuron_id=i,
                    timestamp=latency / 1000.0,
                    weight=1.0
                ))
        return spikes

    @staticmethod
    def encode_sensor(sensor_type: str, data: List[float]) -> List[SpikeEvent]:
        """Encode sensor data based on type."""
        if sensor_type == "radar":
            return SpikeEncoder.rate_encode(data, 128, 50.0)
        elif sensor_type == "acoustic":
            return SpikeEncoder.latency_encode(data, 128, 100.0)
        elif sensor_type == "rf":
            return SpikeEncoder.rate_encode(data, 128, 10.0)
        else:
            return SpikeEncoder.rate_encode(data, 128, 100.0)
