import cmd2

def swap(node_id, equipment, *args):
    pass  # Implement your logic here

def see_topology():
    print("coucou")
    pass  # Implement your logic here

def change_weight(link, weight):
    pass  # Implement your logic here

def remove_link(link):
    pass  # Implement your logic here

def add_link(link):
    pass  # Implement your logic here

def see_filters():
    pass  # Implement your logic here

def see_load():
    pass  # Implement your logic here

def see_tunnelled():
    pass  # Implement your logic here

def add_fw_rule(flow):
    pass  # Implement your logic here

class RAPACE_CLI(cmd2.Cmd):
    prompt = 'RAPACE_CLI> '

    def do_swap(self, args):
        args = args.split()
        swap(*args)

    def do_see_topology(self, args):
        see_topology()

    def do_change_weight(self, args):
        args = args.split()
        change_weight(*args)

    def do_remove_link(self, args):
        remove_link(args)

    def do_add_link(self, args):
        add_link(args)

    def do_see_filters(self, args):
        see_filters()

    def do_see_load(self, args):
        see_load()

    def do_see_tunnelled(self, args):
        see_tunnelled()

    def do_add_fw_rule(self, args):
        add_fw_rule(args)

if __name__ == '__main__':
    app = RAPACE_CLI()
    app.cmdloop()
