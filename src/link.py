#Standard libraries
import json
import os
import shutil
from enum import Enum

class LINK_TYPE(Enum):
    UNDEFINED = -1
    DIRECTED = 0
    INCLUDES = 1
    PRECEDES = 2

class Link:
    def __init__(self, source, destination, guid):
        self.source = source
        self.destination = destination
        self.guid = guid
        self.link_type = LINK_TYPE.UNDEFINED
    
    def __str__(self):
        return "\nSource: " + str(self.source) + ", Desination: " + str(self.destination) + ", GUID: " + self.guid