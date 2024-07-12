from abc import ABC, abstractmethod

class Sensor(ABC):
    def __init__(self, min_value=None, max_value=None, delta=None, value=0):
        self._min = min_value
        self._max = max_value
        self._delta = delta
        self._value = value

    @property
    def min(self):
        return self._min

    @min.setter
    def min(self, min_value):
        self._min = min_value

    @property
    def max(self):
        return self._max

    @max.setter
    def max(self, max_value):
        self._max = max_value
    
    @property
    def delta(self):
        return self._delta
    
    @delta.setter
    def delta(self, delta):
        self._delta = delta

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
