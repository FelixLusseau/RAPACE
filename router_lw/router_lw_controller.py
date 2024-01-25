import sys
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import cmd2
import re

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from swap import swap


class RouterlwController(cmd2.Cmd):
    prompt = 'Router_CLI> '

    def __init__(self, sw_name):
        super().__init__()  # Call the cmd2.Cmd __init__ method
        self.topo = load_topo('topology.json')
        self.sw_name = sw_name
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)
        self.controller = swap(self.sw_name, 'router_lw')
        self.reset_state()
        self.set_table_defaults()
        self.route(self.sw_name)

    def reset_state(self):
        self.controller.reset_state()
        self.controller.table_clear("encap_routing")

    def set_table_defaults(self):
        self.controller.table_set_default("encap_routing", "drop", [])

    def route(self, sw_name):

        # Parcourir tous les commutateurs
        for sw_dst in self.topo.get_p4switches():
            # Obtenir l'adresse de bouclage du commutateur
            loopback_ip = self.topo.get_nodes()[sw_dst].get('loopback')

            # Obtenir les chemins les plus courts vers le commutateur
            paths = self.topo.get_shortest_paths_between_nodes(sw_name, sw_dst)
            # print("paths from {} to {} : {}".format(sw_name, sw_dst, paths))

            if len(paths) == 1:
                if len(paths[0]) == 1:
                    continue
                else:  
                    next_hop = paths[0][1]
                sw_port = self.topo.node_to_node_port_num(sw_name, next_hop)
                dst_sw_mac = self.topo.node_to_node_mac(next_hop, sw_name)

                # Ajouter la règle
                print("table_add at {}:".format(sw_name))
                print("encap_routing segRoute_port " + str(sw_dst[1:]) + " => " + str(dst_sw_mac) + " " + str(sw_port))
                self.controller.table_add("encap_routing", "segRoute_port", str(sw_dst[1:]), [str(dst_sw_mac), str(sw_port)])

            elif len(paths) > 1:
                next_hops = [x[1] for x in paths]
                dst_macs_ports = [(self.topo.node_to_node_mac(next_hop, sw_name),
                                self.topo.node_to_node_port_num(sw_name, next_hop))
                                for next_hop in next_hops]

                # Ajouter la règle pour chaque chemin
                for dst_mac, sw_port in dst_macs_ports:
                    print("table_add at {}:".format(sw_name))
                    print("encap_routing segRoute_port " + str(sw_dst[1:]) + " => " + str(dst_mac) + " " + str(sw_port))
                    self.controller.table_add("encap_routing", "segRoute_port", str(sw_dst[1:]), [str(dst_mac), str(sw_port)])


    def see_load(self):
        print("Total counter: ")
        self.controller.counter_read('count_in', 0)
        print("\u200B")

    
    # cmd2 methods
    def do_see(self, args):
        if args == 'load':
            self.see_load()

    def do_routes_reload(self, args):
        self.controller.table_clear("encap_routing")
        self.controller.table_set_default("encap_routing", "drop", [])
        self.route(self.sw_name)
    

def matches_regex(string, regex):
    return re.match(regex, string) is not None

if __name__ == '__main__':
    if matches_regex(sys.argv[1], r's[0-9]+$'):
        app = RouterlwController(sys.argv[1])
        app.cmdloop()
