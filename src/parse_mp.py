#Standard libraries
import json
import os
import shutil
from enum import Enum

#Other files
from src.node import Node
from src.node import NODE_TYPE
from src.link import Link
from src.link import LINK_TYPE
from src.trace import Trace

#Parsing traces from a .wng file. 
def parse_traces_from_wng(filename):
    #Reading the file and pulling the raw  text
    f = open(filename)

    #Converting it into a JSON dictionary
    raw = json.loads(f.read())

    #Extracting all nodes and lists, from all traces, stored in the file
    entities = raw["entities"]

    all_nodes_as_json = entities["nodes"]
    all_links_as_json = entities["links"]
    all_traces_as_json = entities["traces"]

    #Iterate through all traces and pull nodes and links from their respective traces
    all_traces = []

    for pho_active_trace in all_traces_as_json:
        active_trace = all_traces_as_json[pho_active_trace]

        #From that, retrieving a list of node and link GUIDs present in the trace
        current_trace_node_guids = active_trace["nodes"]
        current_trace_link_guids = active_trace["links"]

        #Then, cross-reference which nodes in the all_nodes_as_strings list are present in the current trace
        current_trace_node_strings = []

        for current_trace_node_guid in current_trace_node_guids:
            current_trace_node_strings.append(all_nodes_as_json[current_trace_node_guid])

        #Then, cross-reference which links in the all_links_as_strings list are present in the current trace
        current_trace_link_strings = []

        for current_trace_link_guid in current_trace_link_guids:
            current_trace_link_strings.append(all_links_as_json[current_trace_link_guid])

        #Create a new trace based on the collected data
        new_trace = Trace(pho_active_trace)

        if "marked" in all_traces_as_json[pho_active_trace]:
            if all_traces_as_json[pho_active_trace]["marked"] == "true":
                new_trace.marked = True
            else:
                new_trace.marked = False
        
        if "probability" in all_traces_as_json[pho_active_trace]:
            new_trace.probability = all_traces_as_json[pho_active_trace]["probability"]

        #Now, translate the string objects into node objects
        for node_string in current_trace_node_strings:
            #Determining the node type and translating it into the enum NODE_TYPE
            raw_node_type = node_string["type"]
            node_type = NODE_TYPE.UNDEFINED

            match raw_node_type:
                case "ATOM":
                    node_type = NODE_TYPE.ATOMIC
                case "COMPOSITE":
                    node_type = NODE_TYPE.COMPOSITE
                case "ROOT":
                    node_type = NODE_TYPE.ROOT
                case "GRAPH_GROUP":
                    node_type = NODE_TYPE.GRAPH_PARENT
                case "GRAPH_NODE":
                    node_type = NODE_TYPE.GRAPH_CHILD
                case "SAY":
                    node_type = NODE_TYPE.SAY
                case "REPORT":
                    node_type = NODE_TYPE.REPORT
                case "TABLE":
                    node_type = NODE_TYPE.TABLE
                case _:
                    node_type = NODE_TYPE.UNDEFINED

            #Constructing the new node
            new_node = Node(node_string["name"], node_string["guid"], node_type)

            #In case the node is a report node
            if new_node.node_type == NODE_TYPE.REPORT:
                new_node.report_array = node_string["itemArray"]
            
            #In case the node is a table node
            if new_node.node_type == NODE_TYPE.TABLE:
                index = 0

                new_node.report_array.append([])
                for element in node_string["headers"]: 
                        new_node.report_array[index].append(element["text"])

                index += 1

                for entry in node_string["itemArray"]:
                    new_node.report_array.append([])
                    for element in entry["columns"]: 
                        new_node.report_array[index].append(element["text"])
                    
                    index += 1

            #Adding the new node to the current trace nodes list
            new_trace.nodes[new_node.guid] = new_node

        #Now, translate the string objects into link objects
        for link_string in current_trace_link_strings:
            #Going through all of the nodes and checking for matches for the source and target on the current link
            source_node = ""
            target_node = ""

            #Make iterate point to begining and incerement it one by one till it reaches the end of list.
            for new_trace_node in new_trace.nodes:
                if link_string["source"] == new_trace_node:
                    source_node = new_trace_node
                if link_string["target"] == new_trace_node:
                    target_node = new_trace_node

            link_guid = link_string["guid"]

            #Creating a new link based on the source and target node found (the pair will always be found)
            new_link = Link(source_node, target_node, link_guid)

            raw_link_type = link_string["relation"]

            match raw_link_type:
                case "FOLLOWS":
                    new_link.link_type = LINK_TYPE.PRECEDES
                case "IN":
                    new_link.link_type = LINK_TYPE.INCLUDES
                case _:
                    new_link.link_type = LINK_TYPE.UNDEFINED
            
            if "text" in link_string:
                new_link.text = link_string["text"]

            #Then, updating the source and target nodes and adding to their links in/links out lists
            new_trace.nodes[source_node].links_out.append(link_guid)
            new_trace.nodes[target_node].links_in.append(link_guid)

            #Add the newly made link to the links list
            new_trace.links[new_link.guid] = new_link

        #Add the new trace to the total traces array
        all_traces.append(new_trace)

    return all_traces

#Parsing traces from a .gry file.
#Note:  Currently lacks some capabilities that .wng files have.
#       The original interface was built around .wng files and
#       this one is still formatted similarly.
def parse_traces_from_gry(filename):
    #Reading the file and pulling the raw  text
    f = open(filename)

    #Converting it into a JSON dictionary
    raw = json.loads(f.read())
    
    graphs = raw["graphs"]

    all_traces = []

    #Iterating through all of the Gryphon graphs 
    for active_graph in graphs:
        new_trace = Trace("")

        #If the graph is a trace:
        if "trace" in active_graph:
            if "mark" in active_graph["trace"]:
                if active_graph["trace"]["mark"] == "M":
                    new_trace.marked = True
                else:
                    new_trace.marked = False

            for node in active_graph["trace"]["nodes"]:
                raw_node_type = node["type"]
                node_type = NODE_TYPE.UNDEFINED

                match raw_node_type:
                    case "A":
                        node_type = NODE_TYPE.ATOMIC
                    case "C":
                        node_type = NODE_TYPE.COMPOSITE
                    case "R":
                        node_type = NODE_TYPE.ROOT
                    case _:
                        node_type = NODE_TYPE.UNDEFINED

                new_node = Node(node["label"], node["id"], node_type)

                new_trace.nodes[new_node.guid] = new_node
            
            index = 0
            for link in active_graph["trace"]["edges"]:
                new_link = Link(link["from_id"], link["to_id"], index)

                if "relation" in link:
                    raw_link_type = link["relation"]

                    match raw_link_type:
                        case "FOLLOWS":
                            new_link.link_type = LINK_TYPE.PRECEDES
                        case "IN":
                            new_link.link_type = LINK_TYPE.INCLUDES
                        case _:
                            new_link.link_type = LINK_TYPE.UNDEFINED

                if "text" in link:
                    new_link.text = link["text"]

                new_trace.nodes[link["to_id"]].links_in.append(new_link)
                new_trace.nodes[link["from_id"]].links_out.append(new_link)

                new_trace.links[index] = new_link

                index += 1
        
        #If the graph is not a trace (the global graph)
        else:
            #Nodes and links are stored in a graph instead of a trace
            if "graphs" in active_graph:
                #I haven't seen multiple graphs but just in case
                for graph in active_graph["graphs"]:
                    #Handled the same as for a trace
                    for node in graph["nodes"]:
                        new_node = Node(node["label"], node["id"], NODE_TYPE.UNDEFINED)

                        new_trace.nodes[new_node.guid] = new_node
                    
                    index = 0
                    for link in graph["edges"]:
                        new_link = Link(link["from_id"], link["to_id"], index)

                        if "relation" in link:
                            raw_link_type = link["relation"]

                            match raw_link_type:
                                case "FOLLOWS":
                                    new_link.link_type = LINK_TYPE.PRECEDES
                                case "IN":
                                    new_link.link_type = LINK_TYPE.INCLUDES
                                case _:
                                    new_link.link_type = LINK_TYPE.UNDEFINED

                        if "text" in link:
                            new_link.text = link["text"]

                        new_trace.nodes[link["to_id"]].links_in.append(new_link)
                        new_trace.nodes[link["from_id"]].links_out.append(new_link)

                        new_trace.links[index] = new_link

                        index += 1
            
        all_traces.append(new_trace)

    return all_traces