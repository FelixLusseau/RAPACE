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

    def rules_counters(self):
        nb_entries = self.controller.table_num_entries('fw')
        # print(str(self.controller.table_dump('fw')))
        for i in range(0,nb_entries):
            print("\nRule " + str(i) + " : ")
            print(str(self.controller.table_dump_entry('fw', i)))
            self.controller.counter_read('rule_counter', i)

    def total_counter(self):
        print("Total counter: ")
        self.controller.counter_read('count_in', 0)

    def add_fw_rule(self, flow):
        self.controller.table_add("fw", "drop", flow, [])
        print("Rule : drop " + str(flow) + " added")
    
    # cmd2 methods
    def do_rules_counters(self, args):
        self.rules_counters()

    def do_total_counter(self, args):
        self.total_counter()

    def do_add_fw_rule(self, args):
        self.add_fw_rule(args.split())


def matches_regex(string, regex):
    return re.match(regex, string) is not None

if __name__ == '__main__':
    if matches_regex(sys.argv[1], r's[0-9]+$'):
        app = FirewallController(sys.argv[1])
        app.cmdloop()
    # if sys.argv[1] == 'rules_counters':
    #     FirewallController('s1').rules_counters()

    # elif sys.argv[1] == 'total_counter':
    #     FirewallController('s1').total_counter()
    
    # elif sys.argv[1] == 'add_fw_rule':
    #     FirewallController('s1').add_fw_rule(sys.argv[2:])
    
    # else:
    #     print("Unknown command")
    #     print("Usage: python firewall_controller.py [rules_counters|total_counter|add_fw_rule <flow>]")
