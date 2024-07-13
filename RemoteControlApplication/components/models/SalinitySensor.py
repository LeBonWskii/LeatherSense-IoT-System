from .Sensor import Sensor
from .config.DefaultParameters import DefaultParameters

class SalinitySensor(Sensor):
    _instance = None

    def __init__(self):
        super().__init__()
        self._type = "salinity"
        self._min = DefaultParameters.intervals["salinity"]["min"]
        self._max = DefaultParameters.intervals["salinity"]["max"]
        self._delta = DefaultParameters.intervals["salinity"]["delta"]

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

