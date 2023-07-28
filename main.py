#Standard libraries
import json
import os
import shutil
from enum import Enum

#Other files
from node import Node
from node import NODE_TYPE
from link import Link
from link import LINK_TYPE
from trace import Trace

from parse_mp import parse_traces_from_gry
from parse_mp import parse_traces_from_wng

################################################################################
#Creating MOOS files
################################################################################

#Part -1: Helper methods for the process
################################################################################

#Helper method to generate a ProcessConfig
def write_processconfig(file, process, variable_value_pairs):
    #Creating the header of the ProcessConfig
    file.write("\nProcessConfig = " + process + "\n")
    file.write("{\n")
    
    #Iterate through each of the variable-value pairs
    for variable, values in variable_value_pairs.items():

        #Loop used in case of duplicate entries for one variable
        for value in values:
            file.write("  " + variable + " = " + value + "\n")

    #Closing the ProcessConfig
    file.write("}\n")

#Part 0: preparing to begin making files
################################################################################

#Pulling the traces from the desired input file using above methods
traces = parse_traces_from_gry("input/NSA_SAR_scope_1.gry")

#Finding the path for the output directory
cwd = os.getcwd()
output_dir = os.path.join(cwd, "output/")
input_dir = os.path.join(cwd, "input/")

#Removing the output directory if it exists
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)

#Creating a new output directory
os.mkdir(output_dir)

#Constants for generation
timewarp = "4"
shoreside_ip = "localhost"
shoreside_port_affix = "00"
tif_name = "popolopen"

#Part 1: Shoreside moos file
################################################################################

#Creating the shoreside moos file
shoreside = open(os.path.join(cwd, "output/shoreside.moos"), "x")
shoreside.close()

#Opening the file for editing
shoreside = open(os.path.join(cwd, "output/shoreside.moos"), "a")

#Copy over config variables
shoreside.write("MOOSTimeWarp = " + timewarp + "\n")
shoreside.write("LatOrigin  = 41.34928" + "\n")
shoreside.write("LongOrigin = -74.063645" + "\n")

#Copy over community variables
shutil.copyfile(input_dir + tif_name + ".tif", "output/" + tif_name + ".tif")
shutil.copyfile(input_dir + tif_name + ".info", "output/" + tif_name + ".info")

shoreside.write("ServerHost = " + shoreside_ip + "\n")
shoreside.write("ServerPort = 90" + shoreside_port_affix + "\n")
shoreside.write("Community = shoreside")

#Create ANTLER processconfig
write_processconfig(shoreside, "ANTLER", {
    "MSBetweenLaunches" : [ "100" ],
    "Run" : [
        "MOOSDB @ NewConsole = false",

        "uProcessWatch @ NewConsole = false",
        "uFldNodeComms @ NewConsole = false",
        "pTimeWatch @ NewConsole = false",
        "pHostInfo @ NewConsole = false",

        "pShare @ NewConsole = false",
        "uFldShoreBroker @ NewConsole = false",

        "pMarineViewer @ NewConsole = false",

        "uTimerScript @ NewConsole = false"
    ]
})

#Create uProcessWatch processconfig
write_processconfig(shoreside, "uProcessWatch", {
    "AppTick" : [ "1" ],
    "CommsTick" : [ "1" ],

    "allow_retractions" : [ "true" ],
    "watch_all" : [ "true" ],
    "nowatch" : [ 
        "uXMS*", 
        "uPokeDB*" 
    ],
    "summary_wait" : [ "10" ]
})

#Create uFldNodeComms processconfig
write_processconfig(shoreside, "uFldNodeComms", {
    "AppTick" : [ "2" ],
    "CommsTick" : [ "2" ],

    "comms_range" : [ "5000" ],
    "critical_range" : [ "25" ],
    "min_msg_interval" : [ "0" ],
    "max_msg_length" : [ "10000" ],
    "groups" : [ "false" ],
    "view_node_rpt_pulses" : [ "false" ]
})

#Create pTimeWatch processconfig
write_processconfig(shoreside, "pTimeWatch", {
    "AppTick" : [ "4" ],
    "CommsTick" : [ "4" ],

    "comms_range" : [ "NODE_REPORT" ],
    "critical_range" : [ "30" ]
})

#Create pHostInfo processconfig
write_processconfig(shoreside, "pHostInfo", {
    "AppTick" : [ "2" ],
    "CommsTick" : [ "2" ]
})

#Create pmarineviewer processconfig

#Looking for all buttons throughout all the traces
#A button node is defined as a child of the SHORESIDE_pMarineViewer node 
#that is written in all caps that is not a comment
#Ex: DEPLOY
buttons = {}

for trace in traces:
    #For each trace, finding the SHORESIDE_pMarineViewer node

    #Looking through the nodes to find the correct node
    for node in trace.nodes:
        if trace.nodes[node].name == "SHORESIDE pMarineViewer":
            pMarineViewerNode = node

            #Finding all button nodes
            for link in trace.nodes[pMarineViewerNode].links_out:
                #Each match is a unique button
                target_node = trace.nodes[link.destination]
                button_name = target_node.name

                for link2 in target_node.links_out:
                    #Should be the moos variable being updated
                    destination_node = link2.destination

                    for link3 in trace.nodes[destination_node].links_in:
                        if trace.nodes[link3.source].name == "MOOSDB":
                            var_string = trace.nodes[destination_node].name

                            button_adj_var_string = var_string.replace("  ", " = ")

                            if button_name not in buttons:
                                buttons[button_name] = [ button_adj_var_string ]
                            else:
                                buttons[button_name].append(button_adj_var_string)             

pMarineViewerConfig = {
    "AppTick" : [ "4" ],
    "CommsTick" : [ "4" ],

    "set_pan_x" : [ "0" ],
    "set_pan_y" : [ "0" ],
    "zoom" : [ "1" ],
    "vehicles_shape_scale" : [ "1.5" ],
    "vehicles_name_mode" : [ "names" ],
    "circle_viewable_all" : [ "true" ],
    "appcast_viewable" : [ "true" ],
    "appcast_color_scheme" : [ "indigo" ],

    "TIFF_FILE" : [ tif_name + ".tif" ] #Note: eventually make this dynamic
}

index = 1
for button, button_vars in buttons.items():
    current_button_name = ""
    match index:
        case 1:
            current_button_name = "button_one"
        case 2:
            current_button_name = "button_two"
        case 3:
            current_button_name = "button_three"
        case 4:
            current_button_name = "button_four"
        case _:
            pass
    
    button_string = button

    #Removing duplicate entries found across duplicate traces
    button_vars = [*set(button_vars)]

    for button_var in button_vars:
        button_string += " # " + button_var

    pMarineViewerConfig[current_button_name] = [ button_string ]

    index += 1

write_processconfig(shoreside, "pMarineViewer", pMarineViewerConfig)

#pShare process config
write_processconfig(shoreside, "pShare", {
    "AppTick" : [ "2" ],
    "CommsTick" : [ "2" ],
    "input" : [ "route = " + shoreside_ip + ":93" + shoreside_port_affix ]
})

#uFldShoreBroker process config
#This needs to be made custom to bridge all necessary variables from the
#Shoreside moos community to the Robot moos communities and vice versa
uFldShoreBrokerConfig = {
    "AppTick" : [ "1" ],
    "CommsTick" : [ "1" ],
    "bridge": [
        "src=HELM_MAP_CLEAR, alias=HELM_MAP_CLEAR",
        "src=MULTI_NOTIFY",
        "src=FOUND_OBJ"
    ],
    "qbridge" : [ 
        "NODE_REPORT",
        "NODE_MESSAGE",
        #"MOOS_MANUAL_OVERRIDE", this one should be handled by the model
        "APPCAST_REQ",
        "UMFG_HEARTBEAT"
    ]
}

#uhh this code is good but incorrect - not all variables in moosdb should
#get qbridged, only ones that shoreside posts
qbridge_list = []

for trace in traces:
    for node in trace.nodes:
        if trace.nodes[node].name == "MOOSDB":
            for link_out in trace.nodes[node].links_out:
                var_node = trace.nodes[link_out.destination]

                if var_node.name == "initialize moosdb":
                    continue

                var_name = var_node.name.split("  ", 1)[0]

                if var_name.startswith("set "):
                    var_name = var_name.split(" ", 1)[1]

                if var_name.endswith(" "):
                    var_name = var_name.replace(" ", "_")

                    qbridge_list.append(var_name + "X")
                    qbridge_list.append(var_name + "Y")
                else:
                    var_name = var_name.replace(" ", "_")

                    qbridge_list.append(var_name)

#Removing any duplicate variable assignments
qbridge_list = [*set(qbridge_list)]

uFldShoreBrokerConfig["qbridge"] += qbridge_list

write_processconfig(shoreside, "uFldShoreBroker", uFldShoreBrokerConfig)

#Copy over additional DEFAULT processconfigs
extra_moos_apps = []

for trace in traces:
    for node in trace.nodes:
        if trace.nodes[node].name == "SHORESIDE":
            for link in trace.nodes[node].links_out:
                moos_app = trace.nodes[link.destination].name

                moos_app = moos_app.split(" ", 1)[1]

                if moos_app != "pMarineViewer":
                    #An additional moos app is found
                    extra_moos_apps.append(moos_app)

extra_moos_apps = [*set(extra_moos_apps)]

for moos_app in extra_moos_apps:
    if os.path.isfile(input_dir + "shoreside/" + moos_app):
        config_file = open(input_dir + "shoreside/" + moos_app)

        shoreside.write("\n" + config_file.read() + "\n")

shoreside.close()

exit()

#Part 2: Robot moos files
################################################################################

robots = []
for trace in traces:
    for node in trace.nodes:
        node_obj = trace.nodes[node]
        if node_obj.node_type == NODE_TYPE.ROOT:
            if node_obj.name != "MOOSDB" and node_obj.name != "SHORESIDE" and node_obj.name != "EXTERNAL TO MOOS":
                robots.append(node_obj)

for robot in robots:
    robot = open(robot.name + ".moos", "x")

    #Copy over basic variables
    robot.write("")

    #Copy over community variables

    #Create ANTLER processconfig

    #Create fully default processconfigs

    #Create either iM18 or uSimMarine processconfig

    #Create phelmivp processconfig

    #Copy over additional DEFAULT processconfigs

    #Copy over additional NON DEFAULT processconfigs

    robot.close()

#Part 3: Robot bhv files
################################################################################
for robot in robots:
    robot = open(robot.name + ".bhv", "x")

    robot.write("")
    
    robot.close()

#Part 4: copypasta
################################################################################

#Create launch.sh file

#clean.sh

#popolopen.tif

#popolopen.info