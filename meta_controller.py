import subprocess
from time import sleep
import cmd2
from generate_network import generate_network

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
    pass

def see_topology():
    topo = network['RAPACE'].copy()
    if 'Controllers' in topo:
        del topo['Controllers']
    print(topo)

def change_weight(link, weight):
    pass

def remove_link(link):
    pass

def add_link(link):
    pass

def see_filters():
    for switch, controller in network['RAPACE']['Switches'].items():
        if switch + 'Controller' in network['RAPACE']['Controllers'] and controller == 'firewall':
            print("Filters for switch " + switch + " :")
            send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'see filters')
            print("\n")

def see_load():
    for switch in network['RAPACE']['Switches']:
        if switch + 'Controller' in network['RAPACE']['Controllers']:
            print("Load for switch " + switch + " :")
            send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'see load')
            print("\n")

def see_tunnelled():
    pass

def add_fw_rule(flow):
    for switch, controller in network['RAPACE']['Switches'].items():
            if controller == 'firewall':
                send_command_to_controller(network['RAPACE']['Controllers'][switch + 'Controller'], 'add_fw_rule ' + flow)

class RAPACE_CLI(cmd2.Cmd):
    prompt = '\033[32mRAPACE_CLI> \033[0m'

    def __init__(self):
        print("Generating network...")
        global network
        network = generate_network()
        print("Starting mininet...")
        # self.mininet = subprocess.Popen(['sudo', 'python3', 'network.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # sleep(5)
        print("Starting network...")
        network['RAPACE']['Controllers'] = {} 
        for switch, controller in network['RAPACE']['Switches'].items():
            path = controller + '/' + controller + '_controller.py'
            network['RAPACE']['Controllers'][switch + 'Controller'] = subprocess.Popen(['python3', path, switch], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)      
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

    # cmd2 methods -> delete the commands we don't want (when possible)
    delattr(cmd2.Cmd, 'do_shell')
    # delattr(cmd2.Cmd, 'do_alias')
    delattr(cmd2.Cmd, 'do_edit')
    # delattr(cmd2.Cmd, 'do_macro')
    delattr(cmd2.Cmd, 'do_run_pyscript')
    delattr(cmd2.Cmd, 'do_run_script')
    delattr(cmd2.Cmd, 'do_shortcuts')

    # cmd2 methods -> create the commands we want
    swap_argparser = cmd2.Cmd2ArgumentParser()
    swap_argparser.add_argument('node_id', help="The name of the node")
    swap_argparser.add_argument('equipment', choices=['firewall', 'router', 'loadbalancer'], help="The new equipment of the node")
    swap_argparser.add_argument('args', nargs='*')
    @cmd2.with_argparser(swap_argparser)
    def do_swap(self, args):
        """<node_id> <equipment> [args] - Swap the equipment of a node or add one"""
        args = args.split()
        swap(*args)


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
        args = args.split()
        change_weight(*args)


    remove_link_argparser = cmd2.Cmd2ArgumentParser()
    remove_link_argparser.add_argument('link', help="A link is a string of the form ['src', 'dst', [port_on_src, port_on_dst]]")
    @cmd2.with_argparser(remove_link_argparser)
    def do_remove_link(self, args):
        """<link> - Remove a link"""
        remove_link(args)


    add_link_argparser = cmd2.Cmd2ArgumentParser()
    add_link_argparser.add_argument('link', help="A link is a string of the form ['src', 'dst', [port_on_src, port_on_dst]]")
    @cmd2.with_argparser(add_link_argparser)
    def do_add_link(self, args):
        """<link> - Add a link"""
        add_link(args)


    add_fw_rule_argparser = cmd2.Cmd2ArgumentParser()
    add_fw_rule_argparser.add_argument('flow', nargs=4, help="A flow is a string of the form 'src_ip dst_ip dst_port protocol'")
    @cmd2.with_argparser(add_fw_rule_argparser)
    def do_add_fw_rule(self, args):
        """<flow> - Add a firewall rule. A flow is a string of the form 'src_ip dst_ip dst_port protocol'"""
        flow = ' '.join(args.flow)
        print(flow)
        add_fw_rule(flow)


if __name__ == '__main__':
    app = RAPACE_CLI()
    app.cmdloop()
