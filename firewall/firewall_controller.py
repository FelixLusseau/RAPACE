import sys
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import cmd2
import re

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from swap import swap


class FirewallController(cmd2.Cmd):
    prompt = 'Firewall_CLI> '

    def __init__(self, sw_name):
        super().__init__()  # Call the cmd2.Cmd __init__ method
        self.topo = load_topo('logical_topology.json')
        self.sw_name = sw_name
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)
        self.controller = swap(self.sw_name, 'firewall')
        self.reset_state()
        self.set_table_defaults()
        self.fill_mac_table(sw_name)
        print(f"\033[32mFirewall {sw_name} ready\033[0m", flush=True)
        print("\u200B")

    def reset_state(self):
        self.controller.reset_state()
        self.controller.table_clear("fw")
        self.controller.table_clear("forward")

    def set_table_defaults(self):
        self.controller.table_set_default("forward", "drop", [])
    
    def fill_mac_table(self, sw_name):
        """ Fill the forward table with the mac addresses of the hosts and switches connected to the switch"""
        print(self.topo.get_interfaces_to_node(sw_name))
        interfaces = self.topo.get_interfaces_to_node(sw_name)
        parsed_interfaces = {re.search(r'eth(\d+)', key).group(1): value for key, value in interfaces.items()}
        for switch in self.topo.get_switches_connected_to(sw_name):
            switch_mac = self.topo.node_to_node_mac(switch, sw_name)
            egress_port = self.topo.node_to_node_port_num(sw_name, switch)
            ingress_port = get_other_key(str(egress_port), parsed_interfaces)
            self.controller.table_add("forward", "forward_packet", [str(ingress_port)], [str(switch_mac), str(egress_port)])
            print("table_add at {}:".format(sw_name))
        
        for host in self.topo.get_hosts_connected_to(sw_name):
            host_mac = self.topo.node_to_node_mac(host, sw_name)
            egress_port = self.topo.node_to_node_port_num(sw_name, host)
            ingress_port = get_other_key(str(egress_port), parsed_interfaces)
            self.controller.table_add("forward", "forward_packet", [str(ingress_port)], [str(host_mac), str(egress_port)])
            print("table_add at {}:".format(sw_name))

    def see_filters(self):
        """ Display the rules of the firewall and the associated counter of dropped packets"""
        nb_entries = self.controller.table_num_entries('fw')
        if nb_entries == 0:
            print("\033[33mNo rule to display !\033[31m")
            print("\u200B")
            return
        for i in range(0,nb_entries):
            print("\nRule " + str(i) + " : ")
            print(str(self.controller.table_dump_entry('fw', i)))
            self.controller.counter_read('rule_counter', i)
        print("\u200B")

    def see_load(self):
        self.controller.counter_read('count_in', 0)
        print("\u200B")

    def add_fw_rule(self, flow):
        if flow[3] == 'tcp':
            flow[3] = '6'
        elif flow[3] == 'udp':
            flow[3] = '17'
        elif flow[3] == 'icmp':
            flow[3] = '1'
            flow[2] = '0' # No port for icmp
        else:
            print("\033[31mError: protocol " + flow[3] + " not supported ! Use one of 'icmp', 'tcp' or 'udp'\033[0m")
            print("\u200B")
            return
        
        self.controller.table_add("fw", "drop", flow, [])
        print("Rule : drop " + str(flow) + " added")
        print("\u200B")
    
    # cmd2 methods
    def do_see(self, args):
        if args == 'filters':
            self.see_filters()
        elif args == 'load':
            self.see_load()

    def do_add_fw_rule(self, args):
        self.add_fw_rule(args.split())

    def do_routes_reload(self, args):
        self.controller.table_clear("forward")
        self.controller.table_set_default("forward", "drop", [])
        self.topo = load_topo('logical_topology.json')
        self.fill_mac_table(self.sw_name)


def matches_regex(string, regex):
    return re.match(regex, string) is not None

def get_other_key(matched_key, data_dict):
        # Get all keys in the dictionary
        keys = list(data_dict.keys())
        
        # Find the index of the matched key
        matched_index = keys.index(matched_key)
        
        # Get the other index (0 if the matched index is 1, and 1 if the matched index is 0)
        other_index = 1 - matched_index
        
        # Return the other key
        return keys[other_index]

if __name__ == '__main__':
    if matches_regex(sys.argv[1], r's[0-9]+$'):
        app = FirewallController(sys.argv[1])
        app.cmdloop()
