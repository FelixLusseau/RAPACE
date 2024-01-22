from p4utils.mininetlib.network_API import NetworkAPI

def runMininet():
	net = NetworkAPI()

	# Network general options
	net.setLogLevel("debug")
	net.disableCli()

	# Network definition
	net.addP4Switch('s1')
	net.addP4Switch('s2')
	net.addP4Switch('s3')

	net.addHost('h1')
	net.addHost('h2')

	net.addLink('s1', 's2')
	net.addLink('s1', 'h1')
	net.addLink('s2', 'h2')

	# Assignment strategy
	net.l2()

	# Nodes general options
	net.enablePcapDumpAll()
	net.enableLogAll()

	# Start network
	net.startNetwork()

	return net
