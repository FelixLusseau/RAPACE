import sys
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI


class FirewallController(object):

    def __init__(self, sw_name):
        self.topo = load_topo('topology.json')
        self.sw_name = sw_name
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)

    def rules_counters(self):
        nb_entries = self.controller.table_num_entries('fw')
        # print(str(self.controller.table_dump('fw')))
        for i in range(0,nb_entries):
            print("\nRule " + str(i) + " : ")
            print(str(self.controller.table_dump_entry('fw', i)))
            self.controller.counter_read('rule_counter', i)

    def total_counter(self):
        self.controller.counter_read('count_in', 0)

    def add_fw_rule(self, flow):
        self.controller.table_add("fw", "drop", flow, [])
        print("Rule added")


if __name__ == '__main__':
    if sys.argv[1] == 'rules_counters':
        FirewallController('s1').rules_counters()

    elif sys.argv[1] == 'total_counter':
        FirewallController('s1').total_counter()
    
    elif sys.argv[1] == 'add_fw_rule':
        FirewallController('s1').add_fw_rule(sys.argv[2:])
    
    else:
        print("Unknown command")
        print("Usage: python firewall_controller.py [rules_counters|total_counter|add_fw_rule <flow>]")
