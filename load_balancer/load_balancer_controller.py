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

    def __init__(self, sw_name):
        super().__init__()
        self.topo = load_topo('logical_topology.json')
        self.sw_name = sw_name
        self.port_in = 0
        self.packet_rate = 1
        self.host_connected = [] #mac_adress, port source
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)
        self.controller = swap(self.sw_name, 'load_balancer')
        self.reset_state()
        self.set_table_defaults()
        self.update_packet_rate(1)
        print(f"\033[32mLoad_balancer {sw_name} ready\033[0m", flush=True)
        print("\u200B")

    def reset_state(self):
        self.controller.reset_state()
        self.controller.table_clear("port_to_nhop")
        self.controller.table_clear("ecmp_nhop")

    def set_table_defaults(self):
        self.controller.table_set_default("port_to_nhop", "drop", [])
        self.controller.table_set_default("ecmp_nhop","drop",[])

    def set_packet_rate(self, rate):
        self.packet_rate = rate

    #get the mac address of the interface of the switch facing port in
    def get_mac_address_port_in(self):
        for sw in self.topo.get_switches_connected_to(self.sw_name):
            if self.port_in == self.topo.node_to_node_port_num(self.sw_name, sw):
                return self.topo.node_to_node_mac(sw, self.sw_name)
        for host in self.topo.get_hosts_connected_to(self.sw_name):
            if self.port_in == self.topo.node_to_node_port_num(self.sw_name, host):
                return self.topo.node_to_node_mac(host, self.sw_name)

    #return the list of all the "out" port of a load_balancer
    def get_list_port_out_connected(self):
        port_list = []

        for sw in self.topo.get_switches_connected_to(self.sw_name):
            sw_port = self.topo.node_to_node_port_num(self.sw_name, sw)
            if(sw_port != self.port_in):
                port_list.append(sw_port)

        for host in self.topo.get_hosts_connected_to(self.sw_name):
            host_port = self.topo.node_to_node_port_num(self.sw_name, sw)
            if(host_port != self.port_in):
                port_list.append(host_port)

        return port_list
    
    def port_out_possibilities(self):
        #get the number of port out possibilites
        num_nhop = len(self.topo.get_switches_connected_to(self.sw_name)) - 1
        if num_nhop < 0:
            num_nhop = 0 #just in case to avoid crash if non sense topology happens
        return num_nhop


    #create_tables and fill it if they don't exist
    def set_tables(self):
        
        mac_address_port_in = self.get_mac_address_port_in()

        #check if we have a port_in existing
        if mac_address_port_in is None:
            print(f"\033[31mNo switches facing port_in: {self.port_in}\033[0m")
            return 0

        #get the number of port out possibilites
        num_nhop = self.port_out_possibilities()

        #index_out to give each table_match an unique port output
        port_out = self.get_list_port_out_connected()
        index_out = 0

        #we scan neighbor to create our tables
        #table: port_to_nhop : if port_out, then set next_hop to port_in
        #                      else hash function to get a random port out
        #table: ecmp_nhop : from the hash result return a valid port_out
            
        for sw in self.topo.get_switches_connected_to(self.sw_name):
            sw_port = self.topo.node_to_node_port_num(self.sw_name, sw)
            sw_mac = self.topo.node_to_node_mac(self.sw_name, sw)

            #If it comes from port_in return 0 for port_out
            if sw_port == self.port_in:
                self.controller.table_add("port_to_nhop", "ecmp_hash", [str(sw_port)], [str(num_nhop)])
                print(f"Table: port_to_nhop. Line added: {sw_port} ecmp_hash {num_nhop}\n")
            #Else send it to port_in
            else:
                self.controller.table_add("port_to_nhop", "set_nhop", [str(sw_port)], [str(mac_address_port_in), str(self.port_in)])
                print(f"Table: port_to_nhop. Line added: {sw_port} set_nhop {mac_address_port_in} {self.port_in}\n")
                self.controller.table_add("ecmp_nhop", "set_nhop", [str(index_out)], [str(sw_mac), str(port_out[index_out])])
                print(f"Table: ecmp_nhop. Line added: {index_out} ecmp_hash {sw_mac} {port_out[index_out]}\n")
                index_out = index_out + 1

        for host in self.topo.get_hosts_connected_to(self.sw_name):
            host_port = self.topo.node_to_node_port_num(self.sw_name, host)
            host_mac = self.topo.node_to_node_mac(self.sw_name, host)

            #If it comes from port_in return 0 for port_out
            if host_port == self.port_in:
                self.controller.table_add("port_to_nhop", "ecmp_hash", [str(host_port)], [str(num_nhop)])
                print(f"Table: port_to_nhop. Line added: {host_port} ecmp_hash {num_nhop}\n")
            #Else send it to port_in
            else:
                self.controller.table_add("port_to_nhop", "set_nhop", [str(host_port)], [str(mac_address_port_in), str(self.port_in)])
                print(f"Table: port_to_nhop. Line added: {host_port} set_nhop {mac_address_port_in} {self.port_in}\n")
                self.controller.table_add("ecmp_nhop", "set_nhop", [str(index_out)], [str(sw_mac), str(port_out[index_out])])
                print(f"Table: ecmp_nhop. Line added: {index_out} ecmp_hash {host_mac} {port_out[index_out]}\n")
                index_out = index_out + 1

    #same code as set_tables, but it modifies entries not creating new.
    def update_tables(self):
        mac_address_port_in = self.get_mac_address_port_in()

        #check if we have a port_in existing
        if mac_address_port_in is None:
            print(f"\033[31mNo switches facing port_in: {self.port_in}\033[0m")
            return 0

        #get the number of port out possibilites
        num_nhop = self.port_out_possibilities()

        #index_out to give each table_match an unique port output
        port_out = self.get_list_port_out_connected()
        index_out = 0

        for sw in self.topo.get_switches_connected_to(self.sw_name):
            sw_port = self.topo.node_to_node_port_num(self.sw_name, sw)
            sw_mac = self.topo.node_to_node_mac(self.sw_name, sw)

            #If it comes from port_in return 0 for port_out
            if sw_port == self.port_in:
                self.controller.table_modify_match("port_to_nhop", "ecmp_hash", [str(sw_port)], [str(num_nhop)])
                print(f"Table: port_to_nhop. Line modfied: {sw_port} ecmp_hash {num_nhop}\n")
            #Else send it to port_in
            else:
                self.controller.table_modify_match("port_to_nhop", "set_nhop", [str(sw_port)], [str(mac_address_port_in), str(self.port_in)])
                print(f"Table: port_to_nhop. Line modified: {sw_port} set_nhop {mac_address_port_in} {self.port_in}\n")
                self.controller.table_modify_match("ecmp_nhop", "set_nhop", [str(index_out)], [str(sw_mac), str(port_out[index_out])])
                print(f"Table: ecmp_nhop. Line modified: {index_out} ecmp_hash {sw_mac} {port_out[index_out]}\n")
                index_out = index_out + 1

        for host in self.topo.get_hosts_connected_to(self.sw_name):
            host_port = self.topo.node_to_node_port_num(self.sw_name, host)
            host_mac = self.topo.node_to_node_mac(self.sw_name, host)

            #If it comes from port_in return 0 for port_out
            if host_port == self.port_in:
                self.controller.table_modify_match("port_to_nhop", "ecmp_hash", [str(host_port)], [str(num_nhop)])
                print(f"Table: port_to_nhop. Line modfied: {host_port} ecmp_hash {num_nhop}\n")
            #Else send it to port_in
            else:
                self.controller.table_modify_match("port_to_nhop", "set_nhop", [str(host_port)], [str(mac_address_port_in), str(self.port_in)])
                print(f"Table: port_to_nhop. Line modified: {host_port} set_nhop {mac_address_port_in} {self.port_in}\n")
                self.controller.table_modify_match("ecmp_nhop", "set_nhop", [str(index_out)], [str(host_mac), str(port_out[index_out])])
                print(f"Table: ecmp_nhop. Line modified: {index_out} ecmp_hash {host_mac} {port_out[index_out]}\n")
                index_out = index_out + 1


    def update_packet_rate(self, rate):
        self.packet_rate = float(rate)/1000000
        self.controller.meter_array_set_rates("my_meter", [(self.packet_rate,1),(self.packet_rate,1)])
        print(f"Packet rate updated ! Now is : {self.packet_rate}") 

    def see_load(self):
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

    def see_rate(self):
        print(f"Packet rate is {self.packet_rate}")     
        print("\u200B")     

    def do_see(self, args):
        if args == 'table':
            self.see_table()
        elif args == 'load':
            self.see_load()
        elif args == 'rate':
            self.see_rate()

    def do_set_pck_rate(self, rate):
        self.update_packet_rate(rate)
        print("\u200B")

    def do_set_port_in(self, args):
        #if first time
        target = args.split()
        if self.port_in == 0:
            self.port_in = int(self.topo.node_to_node_port_num(self.sw_name, target[0]))
            print(f"port_in is {self.port_in}")
            if(self.port_in is not None):
                self.set_tables()
                print("Port_in changed")
            else:
                print("\033[31mError, bad switch or host given\033[0m")
        else:
            self.port_in = int(self.topo.node_to_node_port_num(self.sw_name, target[0]))
            if(self.port_in is not None):
                self.update_tables()
                print("Port_in changed")
            else:
                print("\033[31mError, bad switch or host given\033[0m")
        print("\u200B")

    def do_routes_reload(self):
        self.reset_state()
        self.topo = load_topo('logical_topology.json')
        if(self.set_tables() == 1):
            print(f"Error: no port_in defined for loab_balancer {self.sw_name}, please define a port with set_port_in")
            self.port_in = 0
        print("\u200B")



def matches_regex(string, regex):
    return re.match(regex, string) is not None

if __name__ == '__main__':
    if matches_regex(sys.argv[1], r's[0-9]+$'):
        app = LoadBalancerController(sys.argv[1])
        app.cmdloop()