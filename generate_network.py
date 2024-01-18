import yaml

def generate_network():
    with open('network.yaml', 'r') as file:
        topology = yaml.safe_load(file)

    print("Initial topology : ")
    print(topology)

    with open('network.py', 'w') as file:
        file.write('from p4utils.mininetlib.network_API import NetworkAPI\n\n')
        file.write('def runMininet():\n')
        file.write('\tnet = NetworkAPI()\n\n')
        file.write('\t# Network general options\n')
        # file.write('\tnet.setLogLevel("info")\n')
        file.write('\tnet.disableCli()\n\n')
        file.write('\t# Network definition\n')
        for switch, value in topology['RAPACE']['Switches'].items():
            file.write('\tnet.addP4Switch(\'' + switch + '\')\n')
        file.write('\n')
        for host, value in topology['RAPACE']['Hosts'].items():
            file.write('\tnet.addHost(\'' + host + '\')\n')
        file.write('\n')
        for link in topology['RAPACE']['Links']:
            args = ', '.join('\'' + v + '\'' if isinstance(v, str) else str(v) for v in link)
            file.write('\tnet.addLink(' + args + ')\n')
        file.write('\n')
        file.write('\t# Assignment strategy\n')
        file.write('\tnet.mixed()\n\n')
        file.write('\t# Nodes general options\n')
        file.write('\tnet.enablePcapDumpAll()\n')
        file.write('\tnet.enableLogAll()\n\n')
        file.write('\t# Start network\n')
        file.write('\tnet.startNetwork()\n')
        file.write('\n')
        file.write('\treturn net\n')

    print("Network file generated.")
    return topology

generate_network()
