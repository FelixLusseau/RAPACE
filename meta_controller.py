import subprocess
from time import sleep
import cmd2

def send_command_to_controller(controller, command):
    """Send a command to the controller and print the response"""
    controller.stdin.write(command + '\n')
    controller.stdin.flush()

    # Lire la réponse
    while True:
        response = controller.stdout.readline()
        if response == '\u200B\n':
            break
        print(response, end='')

def swap(node_id, equipment, *args):
    pass

def see_topology():
    print("coucou")
    pass

def change_weight(link, weight):
    pass

def remove_link(link):
    pass

def add_link(link):
    pass

def see_filters(firewall):
    send_command_to_controller(firewall, 'see filters')

def see_load(controller):
    send_command_to_controller(controller, 'see load')

def see_tunnelled():
    pass

def add_fw_rule(firewall, flow):
    send_command_to_controller(firewall, 'add_fw_rule ' + flow)

class RAPACE_CLI(cmd2.Cmd):
    prompt = 'RAPACE_CLI> '

    def __init__(self):
        print("Starting network...")
        self.firewall = subprocess.Popen(['python3', 'firewall/firewall_controller.py', 's1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)      
        sleep(3)
        super().__init__()

    # cmd2 methods    
    def do_exit(self, args):
        self.firewall.stdin.close()
        self.firewall.terminate()
        self.firewall.wait(timeout=0.2)
        return True

    def do_swap(self, args):
        args = args.split()
        swap(*args)

    def do_see(self, args):
        if args == 'topology':
            see_topology()
        elif args == 'filters':
            see_filters(self.firewall)
        elif args == 'load':
            see_load(self.firewall)
        elif args == 'tunnelled':
            see_tunnelled()

    def do_change_weight(self, args):
        args = args.split()
        change_weight(*args)

    def do_remove_link(self, args):
        remove_link(args)

    def do_add_link(self, args):
        add_link(args)

    def do_add_fw_rule(self, args):
        add_fw_rule(self.firewall, args)

if __name__ == '__main__':
    app = RAPACE_CLI()
    app.cmdloop()
