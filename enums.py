from enum import Enum

class ProxyMode(Enum):
    DIRECT_HIT = 'd'
    RANDOM = 'r'
    CUSTOMIZED = 'c'
    