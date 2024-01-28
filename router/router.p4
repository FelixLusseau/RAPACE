/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

//My includes
#include "include/headers.p4"
#include "include/parsers.p4"

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {  }
}

/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    // Counter of incoming and tunnelled / encapsulated packets
    counter(1, CounterType.packets) count_in;
    counter(1, CounterType.packets) count_tunnelled;

    // Register to store the device id filled by the controller
    register<bit<8>>(1) device_id_register;

    bool is_tunnelled = false;

    action drop() {
        mark_to_drop(standard_metadata);
    }

    // Forward packets to the checkpoint specified in the table without IP
    action segRoute_port(macAddr_t dstAddr, egressSpec_t port) {
        // Prepare the packet for forwarding
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        standard_metadata.egress_spec = port;
    }

    // Finish the encapsulation process by invalidating the segRoute header
    action segRoute_finish() {
        hdr.ethernet.etherType = TYPE_IPV4;
        hdr.segRoute.setInvalid();
    }

    // Encapsulate the packet with the segRoute header
    action segRoute_encap(bit<8> checkpoint) {
        hdr.ethernet.etherType = TYPE_SEGROUTE;
        hdr.segRoute.setValid();
        hdr.segRoute.checkpoint = checkpoint;
        count_tunnelled.count(0);
    }

    action ecmp_group(bit<14> ecmp_group_id, bit<16> num_nhops){
        hash(meta.ecmp_hash,
	    HashAlgorithm.crc16,
	    (bit<1>)0,
	    { hdr.ipv4.srcAddr,
	      hdr.ipv4.dstAddr,
          meta.srcPort,
          meta.dstPort,
          hdr.ipv4.protocol},
	    num_nhops);

	    meta.ecmp_group_id = ecmp_group_id;
    }

    action set_nhop(macAddr_t dstAddr, egressSpec_t port) {
        // Prepare the packet for forwarding
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        standard_metadata.egress_spec = port;

        // Decrease TTL by 1
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    table ecmp_group_to_nhop {
        key = {
            meta.ecmp_group_id:    exact;
            meta.ecmp_hash: exact;
        }
        actions = {
            drop;
            set_nhop;
        }
        size = 1024;
    }

    // LPM IPv4 table to forward packets to the next hop with IPv4
    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            set_nhop;
            ecmp_group;
            drop;
        }
        size = 1024;
        default_action = drop;
    }

    // LPM IPv4 table to forward encapsulated packets to the next hop when the next hop isn't IPv4 aware
    table encap_lw {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            segRoute_encap;
        }
        size = 1024;
    }

    // Table conaining the rules to encapsulate packets flows
    table encap_rules {
        key = {
            hdr.ipv4.srcAddr: exact;
            hdr.ipv4.dstAddr: exact;
            // meta.dstPort: exact;
            // hdr.ipv4.protocol: exact;
        }
        actions = {
            segRoute_encap;
        }
        size = 1024;
    }

    // Forward packets to the next hop with their tag
    table encap_routing {
        key = {
            hdr.segRoute.checkpoint: exact;
        }
        actions = {
            segRoute_port;
            drop;
        }
        size = 1024;
        default_action = drop;
    }

    // Set the source IP of the ICMP packet
    action set_src_icmp_ip (bit<32> src_ip){
        hdr.ipv4_icmp.srcAddr = src_ip;
    }

    // Table to set the source IP of the ICMP packet for traceroute
    table icmp_ingress_port {
        key = {
            standard_metadata.ingress_port: exact;
        }

        actions = {
            set_src_icmp_ip;
            NoAction;
        }
        size=64;
        default_action=NoAction;
    }

    apply {
        // Count the entering packets
        count_in.count(0);
        
        bit<8> device_id;
        device_id_register.read(device_id, 0);

        // If the packet is encapsulated, forward it to the next hop with tag or finish the encapsulation process
        if (hdr.segRoute.isValid()){
            is_tunnelled = true;
            if (hdr.segRoute.checkpoint == device_id){ // If the packet is for this device, finish the encapsulation process
                segRoute_finish();
                is_tunnelled = false;
            }
            else
                encap_routing.apply();
        }
        // If the packet is not tunnelled
        if (hdr.ipv4.isValid() && hdr.ipv4.ttl > 1 && !is_tunnelled){

            // Small trick to avoid the use of one multiple hash functions for ECMP
            if (hdr.ipv4.protocol == TYPE_TCP){
                meta.dstPort = hdr.tcp.dstPort;
            }
            else if (hdr.ipv4.protocol == TYPE_UDP){
                meta.dstPort = hdr.udp.dstPort;
            }

            // Apply the tables to encapsulate the packets if rules are found or next hop is not IPv4 aware
            encap_lw.apply();
            encap_rules.apply();

            // Apply the LPM table to forward the packets to the next hop (in IPv4 or encapsulate beginning of the tunnel)
            switch (ipv4_lpm.apply().action_run){
                ecmp_group: {
                    ecmp_group_to_nhop.apply();
                }
            }
        }
        //Traceroute Logic (only for TCP probes)
        else if (hdr.ipv4.isValid() && !is_tunnelled && hdr.tcp.isValid() && hdr.ipv4.ttl == 1){

            // Set new headers valid
            hdr.ipv4_icmp.setValid();
            hdr.icmp.setValid();

            // Set egress port == ingress port
            standard_metadata.egress_spec = standard_metadata.ingress_port;

            //Ethernet: Swap map addresses
            bit<48> tmp_mac = hdr.ethernet.srcAddr;
            hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
            hdr.ethernet.dstAddr = tmp_mac;

            // Building new Ipv4 header for the ICMP packet
            // Copy original header (for simplicity)
            hdr.ipv4_icmp = hdr.ipv4;
            // Set destination address as traceroute origin
            hdr.ipv4_icmp.dstAddr = hdr.ipv4.srcAddr;
            // Set src IP to the IP assigned to the switch interface
            icmp_ingress_port.apply();

            // Set protocol to ICMP
            hdr.ipv4_icmp.protocol = IP_ICMP_PROTO;
            // Set default TTL
            hdr.ipv4_icmp.ttl = 64;
            // And IP Length to 56 bytes (normal IP header + ICMP + 8 bytes of data)
            hdr.ipv4_icmp.totalLen= 56;

            // Create ICMP header with
            hdr.icmp.type = ICMP_TTL_EXPIRED;
            hdr.icmp.code = 0;

            // Make sure all the packets are length 70.. so wireshark does not complain when tpc options, etc
            truncate((bit<32>)70);
        }
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply {

    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
     apply {
	update_checksum(
	    hdr.ipv4.isValid(),
            { hdr.ipv4.version,
	          hdr.ipv4.ihl,
              hdr.ipv4.dscp,
              hdr.ipv4.ecn,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
              hdr.ipv4.hdrChecksum,
              HashAlgorithm.csum16);

    update_checksum(
    hdr.ipv4_icmp.isValid(),
        { hdr.ipv4_icmp.version,
          hdr.ipv4_icmp.ihl,
          hdr.ipv4_icmp.dscp,
          hdr.ipv4_icmp.ecn,
          hdr.ipv4_icmp.totalLen,
          hdr.ipv4_icmp.identification,
          hdr.ipv4_icmp.flags,
          hdr.ipv4_icmp.fragOffset,
          hdr.ipv4_icmp.ttl,
          hdr.ipv4_icmp.protocol,
          hdr.ipv4_icmp.srcAddr,
          hdr.ipv4_icmp.dstAddr },
          hdr.ipv4_icmp.hdrChecksum,
          HashAlgorithm.csum16);

    update_checksum(
    hdr.icmp.isValid(),
        { hdr.icmp.type,
          hdr.icmp.code,
          hdr.icmp.unused,
          hdr.ipv4.version,
	      hdr.ipv4.ihl,
          hdr.ipv4.dscp,
          hdr.ipv4.ecn,
          hdr.ipv4.totalLen,
          hdr.ipv4.identification,
          hdr.ipv4.flags,
          hdr.ipv4.fragOffset,
          hdr.ipv4.ttl,
          hdr.ipv4.protocol,
          hdr.ipv4.hdrChecksum,
          hdr.ipv4.srcAddr,
          hdr.ipv4.dstAddr,
          hdr.tcp.srcPort,
          hdr.tcp.dstPort,
          hdr.tcp.seqNo
          },
          hdr.icmp.checksum,
          HashAlgorithm.csum16);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

//switch architecture
V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;