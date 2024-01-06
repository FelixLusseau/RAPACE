from p4utils.mininetlib.network_API import NetworkAPI

net = NetworkAPI()

# Network general options
net.setLogLevel("info")
net.enableCli()

# Network definition
net.addP4Switch('s1')
net.setP4Source("s1", "firewall.p4")
net.addHost("h1")
net.addHost("h2")

net.addLink("h1", "s1")
net.addLink("h2", "s1")

# Assignment strategy
net.mixed()

# Nodes general options
net.enablePcapDumpAll()
net.enableLogAll()

# Start network
net.startNetwork()
