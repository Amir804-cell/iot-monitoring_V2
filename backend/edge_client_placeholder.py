# This file is a placeholder module required by the unit tests 
# (backend/tests/test_edge_client_logic.py) for successful patching.
# The contents are dummy definitions for the names being mocked in the unit tests.
# These definitions allow the 'unittest.mock.patch' function to find the attributes 
# it needs to replace (e.g., 'Serial.println', 'time', 'random').

# Dummy class definitions for objects we mock (like PubSubClient, WiFi)
class PubSubClient: pass
class WiFi: pass
class Serial:
    """Mock structure for the Serial object, to allow patching print methods."""
    def println(self, *args, **kwargs): pass
    def print(self, *args, **kwargs): pass

# Dummy function definitions for sensor reading
def readScaledReg(*args, **kwargs): pass
def readRawReg(*args, **kwargs): pass

# Dummy module definitions for Python/MicroPython standard libraries
import time
import random

# Note: The test file will override all these definitions with its own Mock objects.
