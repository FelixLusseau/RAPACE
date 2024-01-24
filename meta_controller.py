import subprocess
from time import sleep
import cmd2
from generate_network import generate_network
import ast
# import networkx as nx
# import matplotlib.pyplot as plt

def send_command_to_controller(controller, command):
    """Send a command to the controller and print the response"""
    controller.stdin.write(command + '\n')
    controller.stdin.flush()

    # Read the response
    while True:
        response = controller.stdout.readline()
        if response == '\u200B\n':
            break
        print(response, end='')

def swap(node_id, equipment, *args):
    """Swap the equipment of a node or add one"""
    switch = node_id if node_id.startswith('s') else 's' + node_id
    if switch not in network['RAPACE']['Switches']:
        print("This node doesn't exist.")
        # TODO: add the node ?
        return
    else:
        controller = network['RAPACE']['Controllers'][switch + 'Controller']
        controller.stdin.close()
        controller.stdout.read()
        controller.stderr.read()
        controller.terminate()
        del network['RAPACE']['Controllers'][switch + 'Controller']

    network['RAPACE']['Switches'][switch] = equipment
    path = equipment + '/' + equipment + '_controller.py'
    network['RAPACE']['Controllers'][switch + 'Controller'] = subprocess.Popen(['python3', path, switch], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)  
    print("The equipment of " + switch + " has been changed to " + equipment + ".")    
            

def see_topology():
    topo = network['RAPACE'].copy()
    if 'Controllers' in topo:
        del topo['Controllers']
    print(topo)

    # G = nx.Graph()

    # # Ajoutez les switches et les hôtes comme nœuds
    # for node in network['RAPACE']['Switches']:
    #     G.add_node(node)
    # for node in network['RAPACE']['Hosts']:
    #     G.add_node(node)

    # # Ajoutez les liens comme arêtes
    # for link in network['RAPACE']['Links']:
    #     # Supprimez les poids des liens pour la visualisation
    #     link = [node for node in link if not node.startswith('weight=')]
    #     G.add_edge(*link)
    
    # nx.draw(G, with_labels=True)
    # plt.show()

def change_weight(link, weight):
    if isinstance(link, str):
        link = ast.literal_eval(link)
    mininet.updateLink(*link, weight=weight)
    network['RAPACE']['Links'][network['RAPACE']['Links'].index(link)].append("weight = " + weight)
    print("Weight of " + str(link) + " changed to " + weight + ".")
    # TODO: update the shortest paths

def remove_link(link):
    if isinstance(link, str):
        link = ast.literal_eval(link)
    mininet.deleteLink(*link)
    network['RAPACE']['Links'].remove(link)
    print("Link " + str(link) + " removed.")    

def add_link(link):
    if isinstance(link, str):
        link = ast.literal_eval(link)
    mininet.addLink(*link)
    network['RAPACE']['Links'].append(link)
    print("Link " + str(link) + " added.")

def see_filters():
    for switch, controller in network['RAPACE']['Switches'].items():
        if switch + 'Controller' in network['RAPACE']['Controllers'] and controller == 'firewall':
            print("Filtered packets of firewall " + switch + " :")
            send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'see filters')
            print("\n")

def see_load():
    for switch in network['RAPACE']['Switches']:
        if switch + 'Controller' in network['RAPACE']['Controllers']:
            print("Load for " + network['RAPACE']['Switches'][switch] + " " + switch + " :")
            send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'see load')
            print("\n")

def see_tunnelled():
    for switch, controller in network['RAPACE']['Switches'].items():
        if switch + 'Controller' in network['RAPACE']['Controllers'] and controller == 'router':
            print("Tunnelled packets of router " + switch + " :")
            send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'see tunnelled')
            print("\n")

def add_fw_rule(flow):
    for switch, controller in network['RAPACE']['Switches'].items():
            if controller == 'firewall':
                send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'add_fw_rule ' + flow)

def set_rate_lb(rate):
    for switch, controller in network['RAPACE']['Switches'].items():
            if controller == 'load_balancer':
                send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'set_rate_lb ' + rate)

def add_encap_node(flow, node_id):
    switch = node_id if node_id.startswith('s') else 's' + node_id
    for switch, controller in network['RAPACE']['Switches'].items():
        if controller == 'router':
            send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'add_encap_node ' + flow + ' ' + node_id)

class RAPACE_CLI(cmd2.Cmd):
    prompt = '\033[32mRAPACE_CLI> \033[0m'

    def __init__(self):
        print("Generating network...")
        global network
        network = generate_network()
        from network import runMininet # import when network.py is generated
        print("Starting mininet...")
        global mininet
        mininet = runMininet()
        print("Starting network...")
        network['RAPACE']['Controllers'] = {} 
        for switch, controller in network['RAPACE']['Switches'].items():
            path = controller + '/' + controller + '_controller.py'
            network['RAPACE']['Controllers'][switch + 'Controller'] = subprocess.Popen(['python3', path, switch], stdin=subprocess.PIPE, text=True)      
            sleep(1)
            if network['RAPACE']['Controllers'][switch + 'Controller'].poll() is not None and network['RAPACE']['Controllers'][switch + 'Controller'].poll() != 0:
                print(f"The Controller of {switch} has crashed.")
                del network['RAPACE']['Controllers'][switch + 'Controller']
        sleep(3)
        super().__init__()
        # Hide undeletable builtin commands
        self.hidden_commands.append('alias')
        self.hidden_commands.append('macro')
        self.hidden_commands.append('set')

    # cmd2 methods -> delete the commands we don't want
    delattr(cmd2.Cmd, 'do_shell')
    delattr(cmd2.Cmd, 'do_edit')
    delattr(cmd2.Cmd, 'do_run_pyscript')
    delattr(cmd2.Cmd, 'do_run_script')
    delattr(cmd2.Cmd, 'do_shortcuts')

    # cmd2 methods -> create the commands we want
    swap_argparser = cmd2.Cmd2ArgumentParser()
    swap_argparser.add_argument('node_id', help="The name of the node")
    swap_argparser.add_argument('equipment', choices=['firewall', 'router', 'load_balancer'], help="The new equipment of the node")
    swap_argparser.add_argument('args', nargs='*')
    @cmd2.with_argparser(swap_argparser)
    def do_swap(self, args):
        """<node_id> <equipment> [args] - Swap the equipment of a node or add one"""
        node_id = args.node_id
        equipment = args.equipment
        extra_args = args.args
        swap(node_id, equipment, *extra_args)


    see_argparser = cmd2.Cmd2ArgumentParser()
    see_argparser.add_argument('args', choices=['topology', 'filters', 'load', 'tunnelled'])
    @cmd2.with_argparser(see_argparser)
    def do_see(self, opts):
        """topology|filters|load - See the topology, the filters, the load or the tunnelled flows"""
        if opts.args == 'topology':
            see_topology()
        elif opts.args == 'filters':
            see_filters()
        elif opts.args == 'load':
            see_load()
        elif opts.args == 'tunnelled':
            see_tunnelled()


    change_weight_argparser = cmd2.Cmd2ArgumentParser()
    change_weight_argparser.add_argument('link', help="A link is a string of the form ['src', 'dst', [port_on_src, port_on_dst]]")
    change_weight_argparser.add_argument('weight', help="The new weight of the link")
    @cmd2.with_argparser(change_weight_argparser)
    def do_change_weight(self, args):
        """<link> <weight> - Change the weight of a link"""
        change_weight(args.link, args.weight)


    remove_link_argparser = cmd2.Cmd2ArgumentParser()
    remove_link_argparser.add_argument('link', help="A link is a string of the form ['src', 'dst', [port_on_src, port_on_dst]]")
    @cmd2.with_argparser(remove_link_argparser)
    def do_remove_link(self, args):
        """<link> - Remove a link"""
        remove_link(args.link)


    add_link_argparser = cmd2.Cmd2ArgumentParser()
    add_link_argparser.add_argument('link', help="A link is a string of the form ['src', 'dst', [port_on_src, port_on_dst]]")
    @cmd2.with_argparser(add_link_argparser)
    def do_add_link(self, args):
        """<link> - Add a link"""
        add_link(args.link)


    add_fw_rule_argparser = cmd2.Cmd2ArgumentParser()
    add_fw_rule_argparser.add_argument('flow', nargs=4, help="A flow is a string of the form 'src_ip dst_ip dst_port protocol'")
    @cmd2.with_argparser(add_fw_rule_argparser)
    def do_add_fw_rule(self, args):
        """<flow> - Add a firewall rule. A flow is a string of the form 'src_ip dst_ip dst_port protocol'"""
        flow = ' '.join(args.flow)
        add_fw_rule(flow)

    set_rate_lb_argparser = cmd2.Cmd2ArgumentParser()
    set_rate_lb_argparser.add_argument('pkts/s', help="The new rate of the loadbalancer")
    @cmd2.with_argparser(set_rate_lb_argparser)
    def do_set_rate_lb(self, args):
        """<pkts/s> - Set the rate of the loadbalancer"""
        set_rate_lb(args.pkts_s)

    add_encap_node_argparser = cmd2.Cmd2ArgumentParser()
    add_encap_node_argparser.add_argument('flow', nargs=4, help="The flow to encapsulate")
    add_encap_node_argparser.add_argument('node_id', help="The name of the node")
    @cmd2.with_argparser(add_encap_node_argparser)
    def do_add_encap_node(self, args):
        """<flow> <node_id> - Add an encapsulation node"""
        flow = ' '.join(args.flow)
        add_encap_node(flow, args.node_id)
        

# Main function
if __name__ == '__main__':
    app = RAPACE_CLI()
    app.cmdloop()
