#Standard libraries
import json
import os
import shutil
from enum import Enum

class Trace:
    def __init__(self, name):
        self.name = name
        self.nodes = {}
        self.links = {}
        self.marked = False
        self.probability = 0.0

    def __str__(self):
        return_val = ""

        return_val += "\n" + self.name + " has a " + str(self.probability) + " chance of occuring: "

        return_val += "\nNodes:"
        for node in self.nodes:
            return_val += str(self.nodes[node])
        
        return_val += "\nLinks:"
        for link in self.links:
            return_val += str(self.links[link])

        return return_val