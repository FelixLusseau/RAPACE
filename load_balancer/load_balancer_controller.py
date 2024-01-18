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
        self.port_in = port_in
        self.host_connected = [] #mac_adress, port source
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)
        self.controller = swap(self.sw_name, 'load_balancer')

    def see_load(self,args):
        print("Total counter: ")
        self.controller.counter_read('count_in', 0)
        print("\u200B")

    def add_line_table(self, port_src, mc_address_port_in, port_in):
        self.controller.table_add("port_to_nhop", "set_nhop", [port_src], [mc_address_port_in, port_in])
        print("Line added : port_to_nhop" + str(port_src) + "to" + str(port_in))
        print("\u200B")

    def get_neighbor(self,args):
        neighbor = self.topo.get_hosts_connected_to(self.sw_name)
        neighbor_list=[]
        for i in neighbor:
            neighbor_list.append([self.topo.get_host_mac(i), self.topo.node_to_node_port_num(self.sw_name,i)])
        return neighbor_list

    def do_update_neighbor(self,args):
        find = 0 
        neighbor_list = self.get_neighbor(self)
        node_to_delete = []
        node_to_add = []

        #get a current neighbor see if it's inside the database
        #update the database in case
        for i in neighbor_list:
            for j in self.host_connected:
                if i == j:
                    find = 1
                elif i[1] == j[1]:
                    node_to_delete.append(j)
                    node_to_add.append(i)
            if find == 0:
                node_to_add.append(i)
            find = 0

        self.remove_to_list(self, node_to_delete)
        self.add_to_list(self, node_to_add)


    def add_to_list(self, node_to_add):
        for i in node_to_add:
            self.host_connected.append(i)
            self.add_line_table(self, i[1], i[0], self.port_in)

    def remove_to_list(self, node_list):
        for i in node_list:
            self.host_connected.remove(i)
            self.controller.table_delete_match("port_to_nhop",[i[1]])

    def do_show_table(self, args):
        self.controller.table_dump("port_to_nhop")

def matches_regex(string, regex):
    return re.match(regex, string) is not None

if __name__ == '__main__':
    if matches_regex(sys.argv[1], r's[0-9]+$') and matches_regex(sys.argv[2], r'[0-9]+$'):
        app = LoadBalancerController(sys.argv[1],sys.argv[2])
        app.cmdloop()