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
	net.addP4Switch('s4')
	net.addP4Switch('s5')

	for i in range(0, 6):
		for j in range(i, 6):
			if i != j:
				net.addLink(f's{i}', f's{j}')

	net.addHost('h1')
	net.addHost('h2')

	net.addLink('h1', 's0')
	net.addLink('s3', 'h2')

	# Assignment strategy
	net.l3()

	# Nodes general options
	net.enablePcapDumpAll()
	net.enableLogAll()

	# Start network
	net.startNetwork()

	return net
