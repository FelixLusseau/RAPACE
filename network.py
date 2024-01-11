from p4utils.mininetlib.network_API import NetworkAPI

net = NetworkAPI()

# Network general options
net.setLogLevel("info")
net.enableCli()

# Network definition
net.addP4Switch('s1')
net.addP4Switch('s2')
net.addP4Switch('s3')

net.addHost('h1')
net.addHost('h2')

net.addLink('s2', 's3')
net.addLink('s1', 'h1')
net.addLink('s1', 'h2')

# Assignment strategy
net.mixed()

# Nodes general options
net.enablePcapDumpAll()
net.enableLogAll()

# Start network
net.startNetwork()
