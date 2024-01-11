import yaml

def generate_network():
    with open('network.yaml', 'r') as file:
        topology = yaml.safe_load(file)

    print("Initial topology : ")
    print(topology)

    with open('network.py', 'w') as file:
        file.write('from p4utils.mininetlib.network_API import NetworkAPI\n\n')
        file.write('net = NetworkAPI()\n\n')
        file.write('# Network general options\n')
        file.write('net.setLogLevel("info")\n')
        file.write('net.enableCli()\n\n')
        file.write('# Network definition\n')
        for switch, value in topology['RAPACE']['Switches'].items():
            file.write('net.addP4Switch(\'' + switch + '\')\n')
        file.write('\n')
        for host, value in topology['RAPACE']['Hosts'].items():
            file.write('net.addHost(\'' + host + '\')\n')
        file.write('\n')
        for link, value in topology['RAPACE']['Links'].items():
            args = ', '.join('\'' + v + '\'' if isinstance(v, str) else str(v) for v in value)
            file.write('net.addLink(' + args + ')\n')
        file.write('\n')
        file.write('# Assignment strategy\n')
        file.write('net.mixed()\n\n')
        file.write('# Nodes general options\n')
        file.write('net.enablePcapDumpAll()\n')
        file.write('net.enableLogAll()\n\n')
        file.write('# Start network\n')
        file.write('net.startNetwork()\n')

    print("Network file generated.")
    return topology

# generate_network()
