from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
from p4utils.utils.compiler import * 

def swap(p4switch, device):
    # Load the topology in a networkx graph
    topo = load_topo("topology.json")

    # Get thrift_port to initiate connection with p4switch
    thrift_port = topo.get_thrift_port(p4switch)

    # Open connection with the switch
    api = SimpleSwitchThriftAPI(thrift_port)

    # Compile the P4 program
    print("Compiling")
    source = P4C(device + "/" + device + ".p4", "/usr/local/bin/p4c")
    source.compile()

    # Load to the switch and swap the config 
    print("Pushing to switch")
    api.load_new_config_file(device + "/" + device + ".json")
    api.swap_configs()

    # Update the informations of the switch as known by mininet
    # to match the newly uploaded data-plane
    api.switch_info.load_json_config(api.client)
    api.table_entries_match_to_handle = api.create_match_to_handle_dict()
    api.load_table_entries_match_to_handle()

    return api
