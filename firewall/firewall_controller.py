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
        self.topo = load_topo('topology.json')
        self.sw_name = sw_name
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)
        self.controller = swap(self.sw_name, 'firewall')
        self.reset_state()
        self.set_table_defaults()
        self.fill_mac_table(sw_name)

    def reset_state(self):
        self.controller.reset_state()
        self.controller.table_clear("fw")
        self.controller.table_clear("forward")

    def set_table_defaults(self):
        self.controller.table_set_default("forward", "drop", [])
    
    def fill_mac_table(self, sw_name):
        for switch in self.topo.get_switches_connected_to(sw_name):
            switch_mac = self.topo.node_to_node_mac(switch, sw_name)
            port = self.topo.node_to_node_port_num(sw_name, switch)
            port = port % 2 + 1 # invert the ports
            self.controller.table_add("forward", "forward_packet", [str(port)], [str(switch_mac)])
            print("table_add at {}:".format(sw_name))
            print("forward forward_packet " + str(switch_mac) + " => " + str(port))
        
        for host in self.topo.get_hosts_connected_to(sw_name):
            host_mac = self.topo.node_to_node_mac(host, sw_name)
            port = self.topo.node_to_node_port_num(sw_name, host)
            port = port % 2 + 1 # invert the ports
            self.controller.table_add("forward", "forward_packet", [str(port)], [str(host_mac)])
            print("table_add at {}:".format(sw_name))
            print("forward forward_packet " + str(host_mac) + " => " + str(port))

    def see_filters(self):
        nb_entries = self.controller.table_num_entries('fw')
        if nb_entries == 0:
            print("No rule")
            print("\u200B")
            return
        for i in range(0,nb_entries):
            print("\nRule " + str(i) + " : ")
            print(str(self.controller.table_dump_entry('fw', i)))
            self.controller.counter_read('rule_counter', i)
        print("\u200B")

    def see_load(self):
        print("Total counter: ")
        self.controller.counter_read('count_in', 0)
        print("\u200B")

    def add_fw_rule(self, flow):
        if flow[3] == 'tcp':
            flow[3] = '6'
        elif flow[3] == 'udp':
            flow[3] = '17'
        elif flow[3] == 'icmp':
            flow[3] = '1'
            flow[2] = '0'
        else:
            print("Error: protocol not supported")
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
        self.fill_mac_table(self.sw_name)


def matches_regex(string, regex):
    return re.match(regex, string) is not None

if __name__ == '__main__':
    if matches_regex(sys.argv[1], r's[0-9]+$'):
        app = FirewallController(sys.argv[1])
        app.cmdloop()
