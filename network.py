from p4utils.mininetlib.network_API import NetworkAPI

def runMininet():
	net = NetworkAPI()

	# Network general options
	net.disableCli()

	# Network definition
	net.addP4Switch('s0')
	net.addP4Switch('s1')
	net.addP4Switch('s2')
	net.addP4Switch('s3')

	for i in range(0, 4):
		for j in range(i, 4):
			if i != j:
				net.addLink(f's{i}', f's{j}')

	net.addHost('h1')
	net.addHost('h2')

	net.addLink('h1', 's0')
	net.addLink('s1', 'h2')

	# Assignment strategy
	net.l3()

	# Nodes general options
	net.enablePcapDumpAll()
	net.enableLogAll()

	# Start network
	net.startNetwork()

	return net
