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
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)
        self.controller = swap(self.sw_name, 'load_balancer')

    def see_load(self):
        print("Total counter: ")
        self.controller.counter_read('count_in', 0)
        print("\u200B")

    def add_line_table(self, port_src, mc_address_port_in, port_in):
        self.controller.table_add("port_to_nhop", "set_nhop", [port_src], [mc_address_port_in, port_in])
        print("Line added : port_to_nhop" + str(port_src) + "to" + str(port_in))
        print("\u200B")    

def matches_regex(string, regex):
    return re.match(regex, string) is not None

if __name__ == '__main__':
    if matches_regex(sys.argv[1], r's[0-9]+$') and matches_regex(sys.argv[2], r'[0-9]+$'):
        app = LoadBalancerController(sys.argv[1],sys.argv[2])
        app.cmdloop()