import sys
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import cmd2
import re

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from swap import swap

class LoadBalancerController(cmd2.Cmd):
    prompt = 'Loadbalancer_CLI> '

    def __init__(self, sw_name, port_in):
        super().__init__()
        self.topo = load_topo('topology.json')
        self.sw_name = sw_name
        self.port_in = int(port_in)
        self.host_connected = [] #mac_adress, port source
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)
        self.controller = swap(self.sw_name, 'load_balancer')
        self.reset_state()
        self.update_neighbor()
        
    def reset_state(self):
        self.controller.reset_state()
        self.controller.table_clear("port_to_nhop")

    #get the mac address of the interface of the switch facing port in
    def get_mac_address_port_in(self):
        for sw in self.topo.get_switches_connected_to(self.sw_name):
            if self.port_in == self.topo.node_to_node_port_num(self.sw_name, sw):
                return self.topo.node_to_node_mac(sw, self.sw_name)


    def update_neighbor(self):
        
        mac_address_port_in = self.get_mac_address_port_in()
        if mac_address_port_in is None:
            print(f"No switches facing port_in: {self.port_in}")
            return 0

        #we scan neighboor
        for sw in self.topo.get_switches_connected_to(self.sw_name):
            sw_port = self.topo.node_to_node_port_num(self.sw_name, sw)
            sw_mac = self.topo.node_to_node_mac(self.sw_name, sw)
            
            #If it comes from port_in return 0 for port_out
            if sw_port == self.port_in:
                self.controller.table_add("port_to_nhop", "set_nhop", [str(sw_port)], [str(sw_mac), str(0)])
            #Else send it to port_in
            else:
                self.controller.table_add("port_to_nhop", "set_nhop", [str(sw_port)], [str(mac_address_port_in), str(self.port_in)])


    def see_load(self,args):
        print("Total counter: ")
        self.controller.counter_read('count_in', 0)
        print("\u200B")

    def see_table(self):
        nb_entries = self.controller.table_num_entries("port_to_nhop")
        if nb_entries == 0 or nb_entries is None:
            print("No rule")
            print("\u200B")
            return
        for i in range(0, nb_entries):
            print("\nRule " + str(i) + " : ")
            print(str(self.controller.table_dump_entry('port_to_nhop', i)))
        print("\u200B")                        

    def do_see(self, args):
        if args == 'table':
            self.see_table()
        elif args == 'load':
            self.see_load()

def matches_regex(string, regex):
    return re.match(regex, string) is not None

if __name__ == '__main__':
    if matches_regex(sys.argv[1], r's[0-9]+$') and matches_regex(sys.argv[2], r'[0-9]+$'):
        app = LoadBalancerController(sys.argv[1],sys.argv[2])
        app.cmdloop()