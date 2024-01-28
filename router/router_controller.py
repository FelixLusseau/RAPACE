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
        # # Save the original file descriptors for stdout and stderr
        # orig_stdout = os.dup(1)
        # orig_stderr = os.dup(2)

        # # Open /dev/null and replace stdout and stderr with it
        # devnull = os.open(os.devnull, os.O_WRONLY)
        # os.dup2(devnull, 1)
        # os.dup2(devnull, 2)
        # os.close(devnull)

        super().__init__()  # Call the cmd2.Cmd __init__ method
        self.topo = load_topo('logical_topology.json')
        self.sw_name = sw_name
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)
        self.controller = swap(self.sw_name, 'router')
        self.reset_state()
        self.set_table_defaults()
        self.route(self.sw_name)
        self.set_icmp_ingress_port_table(self.sw_name)
        self.controller.register_write('device_id_register', 0, sw_name[1:])

        # # Restore the original file descriptors for stdout and stderr
        # os.dup2(orig_stdout, 1)
        # os.dup2(orig_stderr, 2)
    
    def reset_state(self):
        self.controller.reset_state()
        self.controller.table_clear("ipv4_lpm")
        self.controller.table_clear("ecmp_group_to_nhop")
        self.controller.table_clear("encap_routing")
        self.controller.table_clear("encap_rules")
        self.controller.table_clear("encap_lw")

    def set_table_defaults(self):
        self.controller.table_set_default("ipv4_lpm", "drop", [])
        self.controller.table_set_default("ecmp_group_to_nhop", "drop", [])
        self.controller.table_set_default("encap_routing", "drop", [])

    def set_icmp_ingress_port_table(self, sw_name):
        """ Fill the icmp_ingress_port table with the ip addresses of the interfaces connected to the switch for Traceroute"""
        for intf, node in self.topo.get_interfaces_to_node(sw_name).items():
            ip = self.topo.node_to_node_interface_ip(sw_name, node).split("/")[0]
            port_number = self.topo.interface_to_port(sw_name, intf)

            print("table_add at {}:".format(sw_name))
            self.controller.table_add("icmp_ingress_port", "set_src_icmp_ip", [str(port_number)], [str(ip)])

    def route(self, sw_name):

        switch_ecmp_groups = {sw_name:{} for sw_name in self.topo.get_p4switches().keys()}

        # Browse all switches for routing rules to their loopback address
        for sw_dst in self.topo.get_p4switches():
            loopback_ip = self.topo.get_nodes()[sw_dst].get('loopback')

            # Calculate the shortest paths to the dest switch (if reachable)
            try:
                paths = self.topo.get_shortest_paths_between_nodes(sw_name, sw_dst)
            except:
                continue
            # print("paths from {} to {} : {}".format(sw_name, sw_dst, paths))

            if len(paths) == 1:
                if len(paths[0]) == 1:
                    continue
                else:  
                    next_hop = paths[0][1]
                sw_port = self.topo.node_to_node_port_num(sw_name, next_hop)
                dst_sw_mac = self.topo.node_to_node_mac(next_hop, sw_name)

                # Add the next hop
                print("table_add at {}:".format(sw_name))
                # print("ipv4_lpm set_nhop " + str(loopback_ip) + " => " + str(dst_sw_mac) + " " + str(sw_port))
                self.controller.table_add("ipv4_lpm", "set_nhop", [str(loopback_ip)], [str(dst_sw_mac), str(sw_port)])
                # print("encap_routing segRoute_port " + str(sw_dst[1:]) + " => " + str(dst_sw_mac) + " " + str(sw_port))
                self.controller.table_add("encap_routing", "segRoute_port", str(sw_dst[1:]), [str(dst_sw_mac), str(sw_port)])

            elif len(paths) > 1:
                next_hops = [x[1] for x in paths]
                dst_macs_ports = [(self.topo.node_to_node_mac(next_hop, sw_name),
                                self.topo.node_to_node_port_num(sw_name, next_hop))
                                for next_hop in next_hops]

                # Add the next hop for each path
                for dst_mac, sw_port in dst_macs_ports:
                    print("table_add at {}:".format(sw_name))
                    # print("ipv4_lpm set_nhop " + str(loopback_ip) + " => " + str(dst_mac) + " " + str(sw_port))
                    self.controller.table_add("ipv4_lpm", "set_nhop", [str(loopback_ip)],
                                            [str(dst_mac), str(sw_port)])
                    # print("encap_routing segRoute_port " + str(sw_dst[1:]) + " => " + str(dst_mac) + " " + str(sw_port))
                    self.controller.table_add("encap_routing", "segRoute_port", str(sw_dst[1:]), [str(dst_mac), str(sw_port)])

        # Browse all switches for routing rules to their directly connected hosts
        for sw_dst in self.topo.get_p4switches():

            # If its ourselves we create direct connections
            if sw_name == sw_dst:
                for host in self.topo.get_hosts_connected_to(sw_name):
                    sw_port = self.topo.node_to_node_port_num(sw_name, host)
                    host_ip = self.topo.get_host_ip(host) + "/32"
                    host_mac = self.topo.get_host_mac(host)

                    # Add rule
                    print("table_add at {}:".format(sw_name))
                    # print("ipv4_lpm set_nhop " + str(host_ip) + " => " + str(host_mac) + " " + str(sw_port))
                    self.controller.table_add("ipv4_lpm", "set_nhop", [str(host_ip)], [str(host_mac), str(sw_port)])

            # Check if there are directly connected hosts
            else:
                if self.topo.get_hosts_connected_to(sw_dst):
                    # Calculate the shortest paths to the dest switch (if reachable)
                    try:
                        paths = self.topo.get_shortest_paths_between_nodes(sw_name, sw_dst)
                    except:
                        continue
                    # print("paths hosts from {} to {} with len {} : {}".format(sw_name, sw_dst, len(paths), paths))
                    for host in self.topo.get_hosts_connected_to(sw_dst):

                        if len(paths) == 1:
                            next_hop = paths[0][1]

                            host_ip = self.topo.get_host_ip(host) + "/24"
                            sw_port = self.topo.node_to_node_port_num(sw_name, next_hop)
                            dst_sw_mac = self.topo.node_to_node_mac(next_hop, sw_name)

                            # Add rule
                            print("table_add at {}:".format(sw_name))
                            # Encapsulate the packet if the next hop is a lw router
                            if self.topo.get_nodes()[next_hop].get('device') == 'router_lw':
                                i = 2
                                while self.topo.get_nodes()[paths[0][i] ].get('device') == 'router_lw':
                                    i += 1
                                checkpoint = paths[0][i]
                                print("encap_lw segRoute_encap" + str(host_ip) + " => " + str(checkpoint[1:]))
                                self.controller.table_add("encap_lw", "segRoute_encap", [str(host_ip)], [checkpoint[1:]])

                            # print("ipv4_lpm set_nhop " + str(host_ip) + " => " + str(dst_sw_mac) + " " + str(sw_port))
                            self.controller.table_add("ipv4_lpm", "set_nhop", [str(host_ip)], [str(dst_sw_mac), str(sw_port)])

                        elif len(paths) > 1:
                            next_hops = [x[1] for x in paths]
                            dst_macs_ports = [(self.topo.node_to_node_mac(next_hop, sw_name),
                                                self.topo.node_to_node_port_num(sw_name, next_hop))
                                                for next_hop in next_hops]
                            host_ip = self.topo.get_host_ip(host) + "/24"

                            # Check if the ecmp group already exists. The ecmp group is defined by the number of next
                            # ports used, thus we can use dst_macs_ports as key
                            if switch_ecmp_groups[sw_name].get(tuple(dst_macs_ports), None):
                                ecmp_group_id = switch_ecmp_groups[sw_name].get(tuple(dst_macs_ports), None)
                                print("table_add at {}:".format(sw_name))
                                # print("ipv4_lpm ecmp_group " + str(host_ip) + " => " + str(ecmp_group_id) + " " + str(len(dst_macs_ports)))
                                self.controller.table_add("ipv4_lpm", "ecmp_group", [str(host_ip)], [str(ecmp_group_id), str(len(dst_macs_ports))])

                            # New ecmp group for this switch
                            else:
                                new_ecmp_group_id = len(switch_ecmp_groups[sw_name]) + 1
                                switch_ecmp_groups[sw_name][tuple(dst_macs_ports)] = new_ecmp_group_id

                                #A dd group
                                for i, (mac, port) in enumerate(dst_macs_ports):
                                    print("table_add at {}:".format(sw_name))
                                    self.controller.table_add("ecmp_group_to_nhop", "set_nhop", [str(new_ecmp_group_id), str(i)], [str(mac), str(port)])

                                # Add forwarding rule
                                print("table_add at {}:".format(sw_name))
                                # print("ipv4_lpm ecmp_group " + str(host_ip) + " => " + str(new_ecmp_group_id) + " " + str(len(dst_macs_ports)))
                                self.controller.table_add("ipv4_lpm", "ecmp_group", [str(host_ip)], [str(new_ecmp_group_id), str(len(dst_macs_ports))])


    def see_load(self):
        print("Total counter: ")
        self.controller.counter_read('count_in', 0)
        print("\u200B")

    def see_tunnelled(self):
        print("Tunnelled packets counter: ")
        self.controller.counter_read('count_tunnelled', 0)
        print("\u200B")

    def add_encap_node(self, flow, sw_dst):
        """ Add an user defined encapsulation rule to the encap_rules table"""
        self.controller.table_add("encap_rules", "segRoute_encap", flow, sw_dst[1:])
        print("Rule : segRoute_encap " + str(flow) + " to " + sw_dst + " added")
        print("\u200B")
    
    # cmd2 methods
    def do_see(self, args):
        if args == 'load':
            self.see_load()
        elif args == 'tunnelled':
            self.see_tunnelled()
    
    def do_add_encap_node(self, args):
        flow = [f for f in args.split(" ")]
        sw_dst = flow.pop()
        self.add_encap_node(flow, sw_dst)

    def do_routes_reload(self, args):
        self.controller.table_clear("ipv4_lpm")
        self.controller.table_clear("ecmp_group_to_nhop")
        self.controller.table_clear("encap_routing")
        self.controller.table_clear("encap_rules")
        self.controller.table_clear("encap_lw")
        self.controller.table_set_default("ipv4_lpm", "drop", [])
        self.controller.table_set_default("ecmp_group_to_nhop", "drop", [])
        self.controller.table_set_default("encap_routing", "drop", [])
        self.topo = load_topo('logical_topology.json')
        self.route(self.sw_name)

def matches_regex(string, regex):
    return re.match(regex, string) is not None

if __name__ == '__main__':
    if matches_regex(sys.argv[1], r's[0-9]+$'):
        app = RouterController(sys.argv[1])
        app.cmdloop()
