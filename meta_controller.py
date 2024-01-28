import subprocess
from time import sleep
import cmd2
from generate_network import generate_network
import ast
import json
import pprint
import networkx as nx
import matplotlib.pyplot as plt

def flush_controller():
    """Flush the controller's stdout"""
    for switch, controller in network['RAPACE']['Switches'].items():
        if switch + 'Controller' in network['RAPACE']['Controllers']:
            network['RAPACE']['Controllers'][switch + 'Controller'].stdout.flush()
            while True:
                response = network['RAPACE']['Controllers'][switch + 'Controller'].stdout.readline()
                if response == "\u200B\n":
                    break
                elif response.startswith("\033[32m"):
                    print(response, end='')
                else:
                    print(response, end='', file=open("/dev/null", "w")) # Print the response in /dev/null to avoid printing it in the terminal

def send_command_to_controller(controller, command):
    """Send a command to the controller and print the response"""
    controller.stdin.write(command + '\n')
    controller.stdin.flush()

    while True:
        response = controller.stdout.readline()
        if response == '\u200B\n':
            break
        print(response, end='')

def add_lo_and_dev_type():
    """ Add loopback addresses and device type to the topology"""
    with open('topology.json', 'r') as f:
        data = json.load(f)

    network['RAPACE']['RoutersLoopback'] = {}
    for node in data['nodes']:
        if node['id'][0] == 's': 
            node['device'] = network['RAPACE']['Switches'][node['id']]
            if network['RAPACE']['Switches'][node['id']] == 'router':
                node['loopback'] = '10.100.0.' + node['id'][1:] + '/32'
                network['RAPACE']['RoutersLoopback'][node['id']] = node['loopback']

    with open('topology.json', 'w') as f:
        json.dump(data, f, indent=4)

def generate_logical_network():
    """ Generate the logical network from the physical network in a different json file"""
    print("Generating logical network...")
    with open('topology.json', 'r') as f:
        data = json.load(f)
    
    for link in data['links'][:]: 
        for link in data['links'][:]:  
            if [link['source'], link['target']] not in [l[:2] for l in network['RAPACE']['Links']] and \
            [link['target'], link['source']] not in [l[:2] for l in network['RAPACE']['Links']]:
                data['links'].remove(link) # Remove the link if it's not in the logical network
    
    for host in data['nodes'][:]:
        if host['id'][0] == 'h':
            network['RAPACE']['Hosts'][host['id']] = host['ip']
            
    with open('logical_topology.json', 'w') as f:
        json.dump(data, f, indent=4)
    
def routes_reload():
    """Reload the routes of the equipments"""
    print("Reloading routes...")
    for switch, controller in network['RAPACE']['Controllers'].items():
        controller.stdin.write('routes_reload' + '\n')
        controller.stdin.flush()

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
    sleep(5) # Wait for the P4 equipment to start
    print("The equipment of " + switch + " has been changed to " + equipment + ".")    
    routes_reload()

def add_node(name, type):
    if(type == "host"):
        mininet.addHost(name)
    else:
        mininet.addP4Switch(name)
        network['RAPACE']['Switches'][name] = type
        path = type + '/' + type + '_controller.py'
        network['RAPACE']['Controllers'][name + 'Controller'] = subprocess.Popen(['python3', path, name], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)      
        if network['RAPACE']['Controllers'][name + 'Controller'].poll() is not None and network['RAPACE']['Controllers'][name + 'Controller'].poll() != 0:
            print(f"The Controller of {name} has crashed.")
            del network['RAPACE']['Controllers'][name + 'Controller']

def see_topology():
    """Print the topology in the terminal and in the network.png file"""
    topo = network['RAPACE'].copy()
    if 'Controllers' in topo:
        del topo['Controllers']

    pprint.pprint(topo) # Print the topology in the terminal (pretty print)

    plt.figure()

    G = nx.Graph()

    device_types = network['RAPACE']['Switches'].values()

    # Create a dictionary where the keys are device types and the values are empty lists
    device_lists = {device_type: [] for device_type in device_types}

    # Now add devices to the lists based on their type
    for switch, device in network['RAPACE']['Switches'].items():  
        device_type = device  
        device_lists[device_type].append(switch)
    
    # Add switches as nodes
    for device_type, switches in device_lists.items():
        for switch in switches:
            G.add_node(switch, device_type=device_type)
    
    # Add hosts as nodes
    hosts = network['RAPACE']['Hosts']
    for host in hosts:
        G.add_node(host)

    pos = nx.spring_layout(G)
    # pos = nx.circular_layout(G)

    # Draw switches with different colors based on their type
    color_map = {'router': 'green', 'router_lw': 'magenta', 'firewall': 'red', 'load_balancer': 'blue'}
    for device_type, switches in device_lists.items():
        color = color_map[device_type]
        nx.draw_networkx_nodes(G, pos, nodelist=switches, node_color=color)

    # Draw hosts
    hosts = network['RAPACE']['Hosts']
    for host in hosts:
        G.add_node(host)
    nx.draw_networkx_nodes(G, pos, nodelist=hosts, node_color='black')

    # Add links as edges
    for link in network['RAPACE']['Links']:
        # Extract weight from link attributes
        weight = next((attr.split('=')[1].strip() for attr in link if attr.startswith('weight =')), 1)
        # Make sure the nodes exist before adding the edge
        if link[0] in G.nodes and link[1] in G.nodes:
            G.add_edge(link[0], link[1], weight=int(weight))

    elarge = [(u, v) for (u, v, d) in G.edges(data=True) if d["weight"] > 1]
    esmall = [(u, v) for (u, v, d) in G.edges(data=True) if d["weight"] <= 1]

    # Draw edges
    nx.draw_networkx_edges(G, pos, edgelist=elarge, width=6)
    nx.draw_networkx_edges(G, pos, edgelist=esmall, width=6, alpha=0.5, edge_color="b", style="dashed")

    # Create labels for switches
    switch_labels = {switch: f'{switch}\n{device_type}' for device_type, switches in device_lists.items() for switch in switches}

    # Create labels for hosts
    host_labels = {host: f'{host}\nHost' for host in network['RAPACE']['Hosts']}

    # Combine switch and host labels
    labels = {**switch_labels, **host_labels}

    # Draw labels
    label_pos = {node: (pos[node][0], pos[node][1] + 0.25) for node in G.nodes}  # Adjust y position of labels
    nx.draw_networkx_labels(G, label_pos, labels=labels)
    edge_labels = nx.get_edge_attributes(G, "weight")
    nx.draw_networkx_edge_labels(G, pos, edge_labels)

    # Adjust plot limits
    x_values, y_values = zip(*pos.values())
    x_max = max(x_values)
    x_min = min(x_values)
    y_max = max(y_values)
    y_min = min(y_values)

    plt.xlim(x_min - 0.4, x_max + 0.4)
    plt.ylim(y_min - 0.4, y_max + 0.4)

    # Save the graph to a file because plt.show() is hard to use through SSH and sudo
    plt.savefig('network.png')

def change_weight(link, weight):
    if isinstance(link, str):
        link = ast.literal_eval(link)
    mininet.updateLink(*link, weight=weight) # Update the weight of the link in mininet physical topology
    network['RAPACE']['Links'][network['RAPACE']['Links'].index(link)].append("weight = " + weight)
    print("Weight of " + str(link) + " changed to " + weight + ".")

    # Save the physical topology and regenerate the logical topology before reloading the routes
    mininet.save_topology()
    generate_logical_network()
    routes_reload()

def remove_link(link):
    if isinstance(link, str):
        link = ast.literal_eval(link)
    mininet.deleteLink(*link)
    network['RAPACE']['Links'].remove(link)
    print("Link " + str(link) + " removed.")
    generate_logical_network()
    routes_reload()

def add_link(link):
    if isinstance(link, str):
        link = ast.literal_eval(link)
    mininet.addLink(*link)
    network['RAPACE']['Links'].append(link)
    generate_logical_network()    
    routes_reload()
    
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

def set_rate_lb(lb_id, rate):
    for switch, controller in network['RAPACE']['Switches'].items():
            if controller == 'load_balancer' and switch == lb_id:
                send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'set_rate_lb ' + rate)

def set_port_in(lb_id, port_in):
    lb_id = lb_id if lb_id.startswith('s') else 's' + lb_id
    for switch, controller in network['RAPACE']['Switches'].items():
            if controller == 'load_balancer' and switch == lb_id:
                send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'set_port_in ' + port_in)

def see_rate():
    for switch, controller in network['RAPACE']['Switches'].items():
        if switch + 'Controller' in network['RAPACE']['Controllers'] and controller == 'load_balancer':
            print("For load_balancer " + switch + " :")
            send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'see rate')
            print("\n")

def add_encap_node(node_src, flow, node_dst):
    node_src = node_src if node_src.startswith('s') else 's' + node_src
    node_dst = node_dst if node_dst.startswith('s') else 's' + node_dst
    for switch, controller in network['RAPACE']['Switches'].items():
        if switch == node_src and controller == 'router' and network['RAPACE']['Switches'][node_dst] == 'router':
            # Add rules in the two routers to encapsulate the flow in the two directions
            send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'add_encap_node ' + flow + ' ' + node_dst)
            reversed_flow = ' '.join(reversed(flow.split()))
            send_command_to_controller(network['RAPACE']['Controllers'][node_dst + 'Controller'], 'add_encap_node ' + reversed_flow + ' ' + node_src)
        elif switch == node_src and controller != 'router':
            print("\033[31mThe source node must be a router.\033[0m")
            return
        elif network['RAPACE']['Switches'][node_dst] != 'router':
            print("\033[31mThe destination node must be a router.\033[0m")
            return

class RAPACE_CLI(cmd2.Cmd):
    prompt = '\033[32mRAPACE_CLI> \033[0m'

    def __init__(self):
        print("Generating physical network...")
        global network
        network = generate_network()
        from network import runMininet # Import when network.py is generated
        print("Starting mininet...")
        global mininet
        mininet = runMininet()
        print("\033[32mMininet started.\033[0m")

        add_lo_and_dev_type()

        generate_logical_network()

        print("\nInitial topology : ")
        see_topology()
        print("\n")

        print("Starting network...")
        network['RAPACE']['Controllers'] = {} 
        for switch, controller in network['RAPACE']['Switches'].items():
            path = controller + '/' + controller + '_controller.py'
            network['RAPACE']['Controllers'][switch + 'Controller'] = subprocess.Popen(['python3', path, switch], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)      
            sleep(1) # Wait for the P4 equipment to start
            # Check if the controller has crashed immediatly
            if network['RAPACE']['Controllers'][switch + 'Controller'].poll() is not None and network['RAPACE']['Controllers'][switch + 'Controller'].poll() != 0:
                print(f"\033[31mThe Controller of {switch} has crashed.\033[0m")
                del network['RAPACE']['Controllers'][switch + 'Controller']
        print("Please wait for the equipments to be ready...")
        super().__init__()
        # Hide undeletable builtin commands
        self.hidden_commands.append('alias')
        self.hidden_commands.append('macro')
        self.hidden_commands.append('set')
        flush_controller()
        print("\n\033[32mNetwork started !\033[0m\n")

    # cmd2 methods -> delete the commands we don't want
    delattr(cmd2.Cmd, 'do_shell')
    delattr(cmd2.Cmd, 'do_edit')
    delattr(cmd2.Cmd, 'do_run_pyscript')
    delattr(cmd2.Cmd, 'do_run_script')
    delattr(cmd2.Cmd, 'do_shortcuts')

    # cmd2 methods -> create the commands we want
    swap_argparser = cmd2.Cmd2ArgumentParser()
    swap_argparser.add_argument('node_id', help="The name of the node")
    swap_argparser.add_argument('equipment', choices=['firewall', 'router', 'router_lw', 'load_balancer'], help="The new equipment of the node")
    swap_argparser.add_argument('args', nargs='*')
    @cmd2.with_argparser(swap_argparser)
    def do_swap(self, args):
        """<node_id> <equipment> [args] - Swap the equipment of a node or add one"""
        node_id = args.node_id
        equipment = args.equipment
        extra_args = args.args
        swap(node_id, equipment, *extra_args)


    see_argparser = cmd2.Cmd2ArgumentParser()
    see_argparser.add_argument('args', choices=['topology', 'filters', 'load', 'tunnelled', 'rate'])
    @cmd2.with_argparser(see_argparser)
    def do_see(self, opts):
        """topology|filters|load|tunelled|rate - See the topology, the filters, the load, the tunnelled flows or the packet rate"""
        if opts.args == 'topology':
            see_topology()
        elif opts.args == 'filters':
            see_filters()
        elif opts.args == 'load':
            see_load()
        elif opts.args == 'tunnelled':
            see_tunnelled()
        elif opts.args == 'rate':
            see_rate()


    change_weight_argparser = cmd2.Cmd2ArgumentParser()
    change_weight_argparser.add_argument('link', help="A link is a string of the form ['src','dst']")
    change_weight_argparser.add_argument('weight', help="The new weight of the link")
    @cmd2.with_argparser(change_weight_argparser)
    def do_change_weight(self, args):
        """<link> <weight> - Change the weight of a link"""
        change_weight(args.link, args.weight)


    remove_link_argparser = cmd2.Cmd2ArgumentParser()
    remove_link_argparser.add_argument('link', help="A link is a string of the form ['src','dst']")
    @cmd2.with_argparser(remove_link_argparser)
    def do_remove_link(self, args):
        """<link> - Remove a link"""
        remove_link(args.link)


    add_link_argparser = cmd2.Cmd2ArgumentParser()
    add_link_argparser.add_argument('link', help="A link is a string of the form ['src','dst']")
    @cmd2.with_argparser(add_link_argparser)
    def do_add_link(self, args):
        """<link> - Add a link"""
        add_link(args.link)


    add_fw_rule_argparser = cmd2.Cmd2ArgumentParser()
    add_fw_rule_argparser.add_argument('flow', nargs=4, help="A flow is a string of the form 'src_ip dst_ip dst_port protocol'. The protocol can be tcp, udp or icmp")
    @cmd2.with_argparser(add_fw_rule_argparser)
    def do_add_fw_rule(self, args):
        """<flow> - Add a firewall rule. A flow is a string of the form 'src_ip dst_ip dst_port protocol'"""
        flow = ' '.join(args.flow)
        add_fw_rule(flow)

    set_rate_lb_argparser = cmd2.Cmd2ArgumentParser()
    set_rate_lb_argparser.add_argument('lb_id', help="the name of the targeted load_balancer")
    set_rate_lb_argparser.add_argument('rate', help="The new rate of the loadbalancer in packet/seconds")
    @cmd2.with_argparser(set_rate_lb_argparser)
    def do_set_rate_lb(self, args):
        """<pkts/s> - Set the rate of the loadbalancer"""
        set_rate_lb(args.lb_id, args.rate)

    set_port_in_argparser = cmd2.Cmd2ArgumentParser()
    set_port_in_argparser.add_argument('lb_id', help="The name of the targeted loadbalancer")
    set_port_in_argparser.add_argument('port_in', help="Name of the equipment or host facing the interface that you want to set as port_in")
    @cmd2.with_argparser(set_port_in_argparser)
    def do_set_port_in(self, args):
        """<lb_id> <port_in> - Set the port_in of the loadbalancer"""
        set_port_in(args.lb_id, args.port_in)

    add_encap_node_argparser = cmd2.Cmd2ArgumentParser()
    add_encap_node_argparser.add_argument('node_src', help="The name of the source node")
    add_encap_node_argparser.add_argument('flow', nargs=2, help="The flow to encapsulate of the form 'src_ip dst_ip'")
    add_encap_node_argparser.add_argument('node_dst', help="The name of the destination node")
    @cmd2.with_argparser(add_encap_node_argparser)
    def do_add_encap_node(self, args):
        """<node_src> <flow> <node_dst> - Add an encapsulation node"""
        flow = ' '.join(args.flow)
        add_encap_node(args.node_src, flow, args.node_dst)

    add_node_argparser = cmd2.Cmd2ArgumentParser()
    add_node_argparser.add_argument('name', help="The name of the equipment")
    add_node_argparser.add_argument('type',choices=['firewall', 'router', 'router_lw', 'load_balancer'], help="The type of the node")
    @cmd2.with_argparser(add_node_argparser)
    def do_add_node(self, args):
        """<node_name> <type>"""
        add_node(args.name, args.type)
        

# Main function
if __name__ == '__main__':
    app = RAPACE_CLI()
    app.cmdloop()
