import sys
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import cmd2
import re

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from swap import swap


class RouterController(cmd2.Cmd):
    prompt = 'Router_CLI> '

    def __init__(self, sw_name):
        super().__init__()  # Call the cmd2.Cmd __init__ method
        self.topo = load_topo('topology.json')
        self.sw_name = sw_name
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)
        self.controller = swap(self.sw_name, 'router')
        self.set_table_defaults()
        self.route(self.sw_name)
        self.controller.register_write('device_id_register', 0, sw_name[1:])

    def set_table_defaults(self):
        self.controller.table_set_default("ipv4_lpm", "drop", [])
        self.controller.table_set_default("ecmp_group_to_nhop", "drop", [])

    def route(self, sw_name):

        switch_ecmp_groups = {sw_name:{} for sw_name in self.topo.get_p4switches().keys()}

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
                # print("ipv4_lpm set_nhop " + str(loopback_ip) + " => " + str(dst_sw_mac) + " " + str(sw_port))
                self.controller.table_add("ipv4_lpm", "set_nhop", [str(loopback_ip)],
                                        [str(dst_sw_mac), str(sw_port)])
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
                    # print("ipv4_lpm set_nhop " + str(loopback_ip) + " => " + str(dst_mac) + " " + str(sw_port))
                    self.controller.table_add("ipv4_lpm", "set_nhop", [str(loopback_ip)],
                                            [str(dst_mac), str(sw_port)])
                    print("encap_routing segRoute_port " + str(sw_dst[1:]) + " => " + str(dst_sw_mac) + " " + str(sw_port))
                    self.controller.table_add("encap_routing", "segRoute_port", str(sw_dst[1:]), [str(dst_sw_mac), str(sw_port)])

        for sw_dst in self.topo.get_p4switches():

            #if its ourselves we create direct connections
            if sw_name == sw_dst:
                for host in self.topo.get_hosts_connected_to(sw_name):
                    sw_port = self.topo.node_to_node_port_num(sw_name, host)
                    host_ip = self.topo.get_host_ip(host) + "/32"
                    host_mac = self.topo.get_host_mac(host)

                    #add rule
                    print("table_add at {}:".format(sw_name))
                    # print("ipv4_lpm set_nhop " + str(host_ip) + " => " + str(host_mac) + " " + str(sw_port))
                    self.controller.table_add("ipv4_lpm", "set_nhop", [str(host_ip)], [str(host_mac), str(sw_port)])

            #check if there are directly connected hosts
            else:
                if self.topo.get_hosts_connected_to(sw_dst):
                    paths = self.topo.get_shortest_paths_between_nodes(sw_name, sw_dst)
                    # print("paths hosts from {} to {} : {}".format(sw_name, sw_dst, paths))
                    for host in self.topo.get_hosts_connected_to(sw_dst):

                        if len(paths) == 1:
                            next_hop = paths[0][1]

                            host_ip = self.topo.get_host_ip(host) + "/32" #"/24"
                            sw_port = self.topo.node_to_node_port_num(sw_name, next_hop)
                            dst_sw_mac = self.topo.node_to_node_mac(next_hop, sw_name)

                            #add rule
                            print("table_add at {}:".format(sw_name))
                            # print("ipv4_lpm set_nhop " + str(host_ip) + " => " + str(dst_sw_mac) + " " + str(sw_port))
                            self.controller.table_add("ipv4_lpm", "set_nhop", [str(host_ip)],
                                                                [str(dst_sw_mac), str(sw_port)])

                        elif len(paths) > 1:
                            next_hops = [x[1] for x in paths]
                            dst_macs_ports = [(self.topo.node_to_node_mac(next_hop, sw_name),
                                                self.topo.node_to_node_port_num(sw_name, next_hop))
                                                for next_hop in next_hops]
                            host_ip = self.topo.get_host_ip(host) + "/32" #"/24"

                            #check if the ecmp group already exists. The ecmp group is defined by the number of next
                            #ports used, thus we can use dst_macs_ports as key
                            if switch_ecmp_groups[sw_name].get(tuple(dst_macs_ports), None):
                                ecmp_group_id = switch_ecmp_groups[sw_name].get(tuple(dst_macs_ports), None)
                                print("table_add at {}:".format(sw_name))
                                self.controller.table_add("ipv4_lpm", "ecmp_group", [str(host_ip)],
                                                                    [str(ecmp_group_id), str(len(dst_macs_ports))])

                            #new ecmp group for this switch
                            else:
                                new_ecmp_group_id = len(switch_ecmp_groups[sw_name]) + 1
                                switch_ecmp_groups[sw_name][tuple(dst_macs_ports)] = new_ecmp_group_id

                                #add group
                                for i, (mac, port) in enumerate(dst_macs_ports):
                                    print("table_add at {}:".format(sw_name))
                                    self.controller.table_add("ecmp_group_to_nhop", "set_nhop",
                                                                        [str(new_ecmp_group_id), str(i)],
                                                                        [str(mac), str(port)])

                                #add forwarding rule
                                print("table_add at {}:".format(sw_name))
                                self.controller.table_add("ipv4_lpm", "ecmp_group", [str(host_ip)],
                                                                    [str(new_ecmp_group_id), str(len(dst_macs_ports))])


    def see_load(self):
        print("Total counter: ")
        self.controller.counter_read('count_in', 0)
        print("\u200B")

    def see_tunnelled(self):
        print("Tunnelled packets counter: ")
        self.controller.counter_read('count_tunnelled', 0)
        print("\u200B")

    def add_encap_node(self, flow, node_id):
        self.controller.table_add("encap_rules", "segRoute_encap", flow, node_id[1])
        print("Rule : segRoute_encap " + str(flow) + " to " + node_id + " added")
        print("\u200B")
    
    # cmd2 methods
    def do_see(self, args):
        if args == 'load':
            self.see_load()
        elif args == 'tunnelled':
            self.see_tunnelled()
    
    def do_add_encap_node(self, args):
        flow = [f for f in args.split(" ")]
        node_id = flow.pop()
        self.add_encap_node(flow, node_id)

def matches_regex(string, regex):
    return re.match(regex, string) is not None

if __name__ == '__main__':
    if matches_regex(sys.argv[1], r's[0-9]+$'):
        app = RouterController(sys.argv[1])
        app.cmdloop()
