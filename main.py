#Standard libraries
import json
import os
import sys
import stat
import shutil
from enum import Enum

#Other files
from src.node import *
from src.link import *
from src.trace import *

from src.parse_mp import *

################################################################################
#Creating MOOS files
################################################################################

#Part -1: Helper methods for the process
################################################################################

#Automatically add a newline to the end for readability
def writeline(file):
    file.write("\n")

def writeline(file, text):
    file.write(text + "\n")

#Helper method to generate a ProcessConfig
def write_processconfig(file, process, variable_value_pairs):
    #Creating the header of the ProcessConfig
    writeline(file, f"\nProcessConfig = {process}")
    writeline(file, "{")
    
    #Iterate through each of the variable-value pairs
    for variable, values in variable_value_pairs.items():

        #Loop used in case of duplicate entries for one variable
        for value in values:
            writeline(file, f"  {variable} = {value}")

    #Closing the ProcessConfig
    writeline(file, "}")

#Stands for join path, just shorthand
def jp(path1, path2):
    return os.path.join(path1, path2)

#A comment node is defined as a node surrounded by underscores/spaces
def is_comment_node(node):
    if node.name[0] == " " and node.name[-1] == " ":
        return True
    else:
        return False

#A method to assign the ServerHost, Community, etc variables at the top of a moos file
def set_header_vars(file, timewarp, lat, lng, ip, port_affix, community):
    writeline(file, f"MOOSTimeWarp = {timewarp}")
    writeline(file, f"LatOrigin  = {str(lat)}")
    writeline(file, f"LongOrigin = {str(lng)}")

    writeline(file)

    writeline(file, f"ServerHost = {shoreside_ip}")
    writeline(file, f"ServerPort = 90{shoreside_port_affix}")
    writeline(file, f"Community = {community}")

#Part 0: preparing to begin making files
################################################################################

#Finding the path for the output directory
cwd = os.getcwd()
output_dir = jp(cwd, "output/")
input_dir = jp(cwd, "input/")

#Pulling the traces from the desired input file using above methods
traces = parse_traces_from_gry(jp(input_dir, "demo-NSA_SAR_scope_2.gry"))

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
shoreside = open(jp(output_dir, "shoreside.moos"), "x")

#Copy over community variables
shutil.copyfile(jp(input_dir, f"{tif_name}.tif"), jp("output/", f"{tif_name}.tif"))
shutil.copyfile(jp(input_dir, f"{tif_name}.info"), jp("output/", f"{tif_name}.info"))

#Copy over config variables
set_header_vars(shoreside, timewarp, 41.34928, -74.063645, shoreside_ip, shoreside_port_affix, "shoreside")

#Create ANTLER processconfig
write_processconfig(shoreside, "ANTLER", {
    "MSBetweenLaunches" : [ "100" ],
    "Run" : [
        "MOOSDB @ NewConsole = false",

        #"uProcessWatch @ NewConsole = false",
        "uFldNodeComms @ NewConsole = false",
        #"pTimeWatch @ NewConsole = false",
        "pHostInfo @ NewConsole = false",

        "pShare @ NewConsole = false",
        "uFldShoreBroker @ NewConsole = false",

        "pMarineViewer @ NewConsole = false",

        "uTimerScript @ NewConsole = false"
    ]
})

#Create uProcessWatch processconfig
'''
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
'''

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
'''
write_processconfig(shoreside, "pTimeWatch", {
    "AppTick" : [ "4" ],
    "CommsTick" : [ "4" ],

    "watch_var" : [ "NODE_REPORT" ],
    "threshhold" : [ "30" ]
})
'''

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
                            var_string = trace.nodes[destination_node].name.replace(" ", "_")

                            button_adj_var_string = var_string.replace("__", " = ")

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

    "TIFF_FILE" : [ f"{tif_name}.tif" ]
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
        button_string += f" # {button_var}"

    pMarineViewerConfig[current_button_name] = [ button_string ]

    index += 1

write_processconfig(shoreside, "pMarineViewer", pMarineViewerConfig)

#pShare process config
write_processconfig(shoreside, "pShare", {
    "AppTick" : [ "2" ],
    "CommsTick" : [ "2" ],
    "input" : [ f"route = {shoreside_ip}:93{shoreside_port_affix}" ]
})

#uFldShoreBroker process config
#This needs to be made custom to bridge all necessary variables from the
#Shoreside moos community to the Robot moos communities and vice versa
uFldShoreBrokerConfig = {
    "AppTick" : [ "1" ],
    "CommsTick" : [ "1" ],
    "bridge": [
        "src=HELM_MAP_CLEAR, alias=HELM_MAP_CLEAR",
        "src=MULTI_NOTIFY"
    ],
    "qbridge" : [ 
        "NODE_REPORT",
        "NODE_MESSAGE",
        "APPCAST_REQ",
        "UMFG_HEARTBEAT"
    ]
}

qbridge_list = []

for trace in traces:
    for node in trace.nodes:
        if trace.nodes[node].name == "MOOSDB":
            for link_out in trace.nodes[node].links_out:
                var_node = trace.nodes[link_out.destination]

                if var_node.name == "initialize moosdb":
                    continue
                    
                for link_in in var_node.links_in:
                    if link_in.link_type == LINK_TYPE.PRECEDES:
                        prior_node = link_in.source

                        if is_comment_node(trace.nodes[prior_node]):
                            continue

                        for link_in2 in trace.nodes[prior_node].links_in:
                            if link_in2.link_type == LINK_TYPE.INCLUDES:
                                prior_node2 = trace.nodes[link_in2.source]

                                if prior_node2.name == "MOOSDB":
                                    continue

                                prior_node3 = trace.nodes[prior_node2.links_in[0].source]

                                if prior_node3.name == "SHORESIDE":
                                    var_name = var_node.name.split("  ", 1)[0]

                                    if var_name.startswith("set "):
                                        var_name = var_name.split(" ", 1)[1]

                                        var_name = var_name.replace(" ", "_")

                                    if var_name.endswith(" "):
                                        qbridge_list.append(f"src={var_name}X")
                                        qbridge_list.append(f"src={var_name}Y")
                                    else:
                                        qbridge_list.append(f"src={var_name}")

#Removing any duplicate variable assignments
qbridge_list = [*set(qbridge_list)]

uFldShoreBrokerConfig["bridge"] += qbridge_list

write_processconfig(shoreside, "uFldShoreBroker", uFldShoreBrokerConfig)

#Copy over additional processconfigs
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
    shoreside_path = jp(input_dir, "shoreside/")
    moos_app_path = jp(shoreside_path, moos_app)

    if os.path.isfile(moos_app_path):
        config_file = open(moos_app_path)

        writeline(shoreside)
        writeline(shoreside, config_file.read())

shoreside.close()

#Part 2: Robot moos files
################################################################################

robots = []
for trace in traces:
    for node in trace.nodes:
        node_obj = trace.nodes[node]
        if node_obj.node_type == NODE_TYPE.ROOT:
            if node_obj.name != "MOOSDB" and node_obj.name != "SHORESIDE" and node_obj.name != "EXTERNAL TO MOOS":
                robots.append(node_obj.name)

robots = [*set(robots)]

index = 1
for robot_name in robots:
    robot_name = robot_name.replace(" ", "_")

    robot_path = jp(output_dir, f"{robot_name}.moos")

    robot = open(robot_path, "x")

    robot_ip = "localhost"
    robot_port_affix = str(10 + index)

    #Copy over config variables
    set_header_vars(robot, timewarp, 41.34928, -74.063645, robot_ip, robot_port_affix, robot_name)

    #Create ANTLER processconfig
    write_processconfig(robot, "ANTLER", {
        "MSBetweenLaunches" : [ "100" ],
        "Run" : [
            "MOOSDB @ NewConsole = false",

            #"uProcessWatch @ NewConsole = false",
            "pMarinePID @ NewConsole = false",
            "pHostInfo @ NewConsole = false",
            "uFldMessageHandler @ NewConsole = false",
            "pNodeReportParse @ NewConsole = false",
            "pNodeReporter @ NewConsole = false",
            "pHelmIvP @ NewConsole = false",

            "pShare @ NewConsole = false",
            "uFldNodeBroker @ NewConsole = false",

            #"pYOLO @ NewConsole = false",
            #"pLocationCalculation @ NewConsole = false",

            #"iM1_8 @ NewConsole = false"
            "uSimMarine @ NewConsole = false"
        ]
    })

    #Create fully default processconfigs
    write_processconfig(robot, "pMarinePID", {
        "AppTick" : [ "10" ],
        "CommsTick" : [ "10" ],

        "VERBOSE" : [ "true" ],
        "DEPTH_CONTROl" : [ "false" ],
        "ACTIVE_START" : [ "true" ],

        "YAW_PID_KP" : [ "0.35" ],
        "YAW_PID_KD" : [ "0.07" ],
        "YAW_PID_KI" : [ "0.0" ],
        "YAW_PID_INTEGRAL_LIMIT" : [ "0.07" ],

        "SPEED_PID_KP" : [ "1.0" ],
        "SPEED_PID_KD" : [ "0.0" ],
        "SPEED_PID_KI" : [ "0.0" ],
        "SPEED_PID_INTEGRAL_LIMIT" : [ "0.07" ],

        "MAXRUDDER" : [ "100" ],
        "MAXTHRUST" : [ "84" ],
        "deprecated_ok" : [ "true" ]
    })

    #Create pHostInfo processconfig
    write_processconfig(robot, "pHostInfo", {
        "AppTick" : [ "1" ],
        "CommsTick" : [ "1" ]
    })

    #Create uFldMessageHandler processconfig
    write_processconfig(robot, "uFldMessageHandler", {
        "AppTick" : [ "3" ],
        "CommsTick" : [ "3" ],
        "STRICT_ADDRESSING": [ "true" ]
    })

    #Create uProcessWatch processconfig
    '''
    write_processconfig(robot, "uProcessWatch", {
        "AppTick" : [ "2" ],
        "CommsTick" : [ "2" ],

        "ALLOW_RETRACTIONS": [ "true" ],

        "WATCH_ALL" : [ "true" ],

        "NOWATCH" : [ 
            "uMAC*", 
            "uXMS*", 
            "uPokeDB*" 
        ],

        "WATCH" : [ 
            "pNodeReporter", 
            "pMarinePID", 
            "pHelmIvP", 
            "pShare" 
        ],

        "SUMMARY_WAIT" : [ "12" ]
    })
    '''

    #Create pNodeReportParse processconfig
    write_processconfig(robot, "pNodeReportParse", {
        "AppTick" : [ "4" ],
        "CommsTick" : [ "4" ]
    })

    #Create either iM18 and uSimMarine processconfig
    write_processconfig(robot, "iM1_8", {
        "ip_addr" : [ robot_ip ],
        "port" : [ "8003" ],
        "comms_type" : [ "client" ],

        "ignore_msg": [ 
            "$DEBUG, $OIVCQ",
            "$PSEAD, $PSEAE",
            "$PSEAG, $PSEAJ",
            "$PSEAF, $VCGLL",
            "$PTQM0, $PTQM1",
            "$PSEAX, $PSEAY"
        ]
    })

    write_processconfig(robot, "uSimMarine", {
        "AppTick" : [ "10" ],
        "CommsTick" : [ "10" ],

        "START_POS": [ "0.0,0.0,0.0" ],
        "PREFIX": [ "NAV" ],

        "deprecated_ok": [ "true" ]
    })

    #Create phelmivp processconfig
    write_processconfig(robot, "pHelmIvP", {
        "AppTick" : [ "4" ],
        "CommsTick" : [ "4" ],

        "Behaviors": [ f"{robot_name}.bhv" ],
        "Verbose": [ "false" ],
        "Domain": [ "course:0:359:360", "speed:0:1.5:26" ]
    })

    #Create pNodeReporter processconfig
    write_processconfig(robot, "pNodeReporter", {
        "AppTick" : [ "2" ],
        "CommsTick" : [ "2" ],

        "platform_type": [ "kayak" ],
        "platform_color": [ "red" ]
    })

    #Create pNodeReporter processconfig
    write_processconfig(robot, "pShare", {
        "AppTick" : [ "2" ],
        "CommsTick" : [ "2" ],

        "input" : [ f"route = {robot_ip}:93{robot_port_affix}" ]
    })

    #Write uFldNodeBroker processconfig
    uFldNodeBrokerConfig =  {
        "AppTick" : [ "1" ],
        "CommsTick" : [ "1" ],

        "TRY_SHORE_HOST": [ f"pshare_route={shoreside_ip}:93{shoreside_port_affix}" ],

        "BRIDGE" : [ 
            "src=VIEW_POLYGON", 
            "src=VIEW_POINT", 
            "src=VIEW_SEGLIST", 
            "src=VIEW_CIRCLE", 
            "src=AVDCOL_MODE", 
            "src=APPCAST", 
            "src=NODE_REPORT_LOCAL, alias=NODE_REPORT", 
            "src=NODE_MESSAGE_LOCAL, alias=NODE_MESSAGE"
        ]
    }

    bridge_list = []

    for trace in traces:
        for node in trace.nodes:
            if trace.nodes[node].name == "MOOSDB":
                for link_out in trace.nodes[node].links_out:
                    var_node = trace.nodes[link_out.destination]

                    if var_node.name == "initialize moosdb":
                        continue

                    for link_in in var_node.links_in:
                        if link_in.link_type == LINK_TYPE.INCLUDES:
                            if trace.nodes[link_in.source].name == "initialize moosdb":
                                continue
                    
                    for link_in in var_node.links_in:
                        if link_in.link_type == LINK_TYPE.PRECEDES:
                            prior_node = link_in.source

                            if is_comment_node(trace.nodes[prior_node]):
                                continue
                            
                            for link_in2 in trace.nodes[prior_node].links_in:
                                if link_in2.link_type == LINK_TYPE.INCLUDES:
                                    prior_node2 = trace.nodes[link_in2.source]

                                    if prior_node2.name == "MOOSDB":
                                        continue

                                    prior_node3 = trace.nodes[prior_node2.links_in[0].source]

                                    if prior_node3.name.replace(" ", "_") == robot_name:
                                        var_name = var_node.name.split("  ", 1)[0]

                                        if var_name.startswith("set "):
                                            var_name = var_name.split(" ", 1)[1]
                                        
                                        var_name = var_name.replace(" ", "_")

                                        if var_name.endswith(" "):
                                            bridge_list.append(f"src={var_name}X")
                                            bridge_list.append(f"src={var_name}Y")
                                        else:
                                            bridge_list.append(f"src={var_name}")

    #Removing any duplicate variable assignments
    bridge_list = [*set(bridge_list)]

    uFldNodeBrokerConfig["BRIDGE"] += bridge_list

    write_processconfig(robot, "uFldNodeBroker", uFldNodeBrokerConfig)

    #Copy over additional processconfigs
    extra_moos_apps = []

    for trace in traces:
        for node in trace.nodes:
            if trace.nodes[node].name.replace(" ", "_") == robot_name:
                for link in trace.nodes[node].links_out:
                    moos_app = trace.nodes[link.destination].name

                    moos_app = moos_app[(len(robot_name) + 1):]

                    if moos_app != "pHelmIvP":
                        #An additional moos app is found
                        extra_moos_apps.append(moos_app)

    extra_moos_apps = [*set(extra_moos_apps)]

    for moos_app in extra_moos_apps:
        robot_path = jp(input_dir, f"{robot_name}/")
        moos_app_path = jp(robot_path, moos_app)

        if os.path.isfile(moos_app_path):
            config_file = open(moos_app_path)

            writeline(robot)
            writeline(robot, config_file.read())

    robot.close()

#Part 3: Robot bhv files
################################################################################

class Mode:
    def __init__(self, name):
        self.name = name
        self.parent_mode = ""
        self.condition = {}
        self.anticondition = {}

modes = []

robots = [*set(robots)]

for robot_name in robots:
    robot_name = robot_name.replace(" ", "_")

    robot_path = jp(output_dir, f"{robot_name}.bhv")

    robot = open(robot_path, "x")

    initial_variables = {}

    states = []

    #First find the initial values of variables using initialize_moosdb
    for trace in traces:
        for node in trace.nodes:
            if trace.nodes[node].name == "initialize moosdb":
                for link_out in trace.nodes[node].links_out:
                    if link_out.link_type == LINK_TYPE.INCLUDES:
                        init_node = trace.nodes[link_out.destination]

                        init_node_text = init_node.name[4:]

                        variable = init_node_text.split("  ", 1)[0].replace(" ", "_")
                        value = init_node_text.split("  ", 1)[1].replace(" ", "_")

                        #This variable is hardcoded in so we don't need it in the behavior file
                        if variable != "MOOS_MANUAL_OVERRIDE":
                            initial_variables[variable] = value

    for variable, value in initial_variables.items():
        writeline(robot, f"initialize {variable} = {value}")
    
    writeline(robot)

    #Finding the trace with the robot's state machine in it
    for trace in traces:
        for parent_node_index in trace.nodes:
            if trace.nodes[parent_node_index].node_type == NODE_TYPE.GRAPH_PARENT:
                global_trace = trace
                parent_node = trace.nodes[parent_node_index]

                #if parent_node.name == robot_name + " State Diagram":
                #    pass
                #    #This will matter in the future but i haven't added support for multiple state machines yet

                undefined_nodes = []
                defined_modes = []
                defined_mode_names = []
                
                for node in trace.nodes:
                    if trace.nodes[node].node_type == NODE_TYPE.GRAPH_CHILD:
                        undefined_nodes.append(trace.nodes[node])
                        #Then the node is part of the state machine

                        current_node = trace.nodes[node]

                        if current_node.name == "ALLSTOP":
                            #this is some annoying hardcode, ideally in later versions it autodetects the initial node's name
                            for link_in in current_node.links_in:
                                transition_text = link_in.text

                                variable = transition_text.split("__", 1)[0]
                                value = transition_text.split("__", 1)[1]

                                new_mode = Mode("ALLSTOP")

                                new_mode.condition = { variable : value }

                                unique = True
                                for existing_defined_mode in defined_modes:
                                    if existing_defined_mode.name == new_mode.name:
                                        unique = False
                                    
                                if unique:
                                    defined_modes.append(new_mode)
                                    defined_mode_names.append(new_mode.name)

                while len(undefined_nodes) > len(defined_modes):
                    for undefined_node in undefined_nodes:
                        if undefined_node.name in defined_mode_names:
                            continue

                        for link_in in undefined_node.links_in:
                            if trace.nodes[link_in.source].name in defined_mode_names:
                                for defined_mode in defined_modes:
                                    if defined_mode.name == trace.nodes[link_in.source].name:
                                        #Found a defined node
                                        new_mode = Mode(undefined_node.name)

                                        transition_text = link_in.text
                                        
                                        variable = transition_text.split("__", 1)[0]
                                        value = transition_text.split("__", 1)[1]
                                        
                                        if variable in defined_mode.condition:
                                            #Node is adjacent with defined mode.
                                            new_mode.parent_mode = defined_mode.parent_mode
                                            new_mode.condition[variable] = value
                                        else:
                                            #Node is child of defined mode.
                                            new_mode.condition[variable] = value
                                            defined_mode.anticondition = { variable : value }

                                            if defined_mode.parent_mode == "":
                                                new_mode.parent_mode = defined_mode.name
                                            else:
                                                new_mode.parent_mode = f"{defined_mode.parent_mode}:{defined_mode.name}"
                                
                                defined_modes.append(new_mode)
                                defined_mode_names.append(new_mode.name)

                
                for defined_mode in defined_modes:
                    writeline(robot, f"set MODE = {defined_mode.name}{{")

                    for variable, value in defined_mode.condition.items():
                        writeline(robot, f"  {variable} = {value}")
                    for variable, value in defined_mode.anticondition.items():
                        writeline(robot, f"  {variable} != {value}")
                    
                    writeline(robot, "}")
                    writeline(robot)

                for defined_mode in defined_modes:
                    behavior_path = jp(robot_path, defined_mode.name)

                    if os.path.exists(behavior_path):
                        mode_behaviors = open(behavior_path, "r")

                        lines = mode_behaviors.readlines()

                        for line in lines:
                            if "condition" in line and "=" in line:
                                writeline(robot, f"  condition = MODE=={defined_mode.name}")
                            else:
                                robot.write(line)

                        writeline(robot)
                        writeline(robot)
    
    robot.close()

#Part 4: copypasta
################################################################################

#Create launch.sh file
launch_path = jp(output_dir, "launch.sh")

launch = open("launch_path", "w")

writeline(launch, "pAntler shoreside.moos &>/dev/null")

for robot_name in robots:
    writeline(launch, f"pAntler {robot_name.replace(" ", "_")}.moos &>/dev/null")

#Make the launch file executable
os.chmod(launch_path, stat.S_IRWXU)