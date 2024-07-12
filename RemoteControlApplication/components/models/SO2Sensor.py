from config.DefaultParameters import DefaultParameters

class SO2Sensor():
    _instance = None

    def __init__(self):
        self._value = False
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, value):
        self._value = value

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
