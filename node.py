#Standard libraries
import json
import os
import shutil
from enum import Enum

class NODE_TYPE(Enum):
    UNDEFINED = -1
    ROOT = 0
    ATOMIC = 1
    COMPOSITE = 2
    GRAPH_PARENT = 3
    GRAPH_CHILD = 4
    SAY = 5
    REPORT = 6
    TABLE = 7

class Node:
    def __init__(self, name, guid, node_type):
        self.name = name
        self.guid = guid
        self.node_type = node_type
        self.links_out = []
        self.links_in = []
        self.report_array = []
    
    def __str__(self):
        return_str = "\nName: " + self.name + ", GUID: " + str(self.guid) + ", Type: " + self.node_type.name
        
        if self.node_type == NODE_TYPE.SAY:
            return_str += "\nSay: " + self.name
            return_str += "\n"

        if self.node_type == NODE_TYPE.REPORT and len(self.report_array) != 0:
            return_str += "\nReport:"
            for row in self.report_array:
                return_str += "\n" + row
            
            return_str += "\n"

        if self.node_type == NODE_TYPE.TABLE and len(self.report_array) != 0:
            return_str += "\nTable:"
            for row in self.report_array:
                return_str += "\n"

                for col in row:
                    return_str += str(col) + "     "
            
            return_str += "\n"
        
        return return_str