from .config.DefaultParameters import DefaultParameters

class H2SSensor():
    _instance = None

    def __init__(self):
        self._type = "H2S"
        self._value = False
        self._timestamp = None
    
    @property
    def timestamp(self):
        return self._timestamp
    
    @timestamp.setter
    def timestamp(self, timestamp):
        self._timestamp = timestamp

    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, value):
        self._value = value
    
    @property
    def type(self):
        return self._type
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
