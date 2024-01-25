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

    // Counter of incoming packets that contain the counter
    counter(1, CounterType.packets) count_in;
    direct_counter(CounterType.packets) rule_counter;

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action forward_packet(macAddr_t dstAddr)
    {
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;

        // Simply forward the packet from one port to the other
        // If input port is 1 => output port 2
        if (standard_metadata.ingress_port == 1){
            standard_metadata.egress_spec = 2;
        }
        // If input port is 2 => output port 1
        else if (standard_metadata.ingress_port == 2){
            standard_metadata.egress_spec = 1;
        }
    }

    table forward {
        key = {
            standard_metadata.ingress_port: exact;
        }
        actions = {
            forward_packet;
        }
        size = 2;
    }

    table fw {
        key = {
            hdr.ipv4.srcAddr: exact;
            hdr.ipv4.dstAddr: exact;
            // meta.srcPort: exact;
            meta.dstPort: exact;
            hdr.ipv4.protocol: exact;
        }

        actions = {
            drop;
            NoAction;
        }
        
        size = 1024;
        default_action = NoAction;
        counters = rule_counter;
    }

    apply {
        // Only if IPV4 the rule is applied. Therefore other packets will not be forwarded.
        if (hdr.ipv4.isValid() && hdr.ipv4.ttl > 1){
            
            // Count the entering packets
            count_in.count(0);

            forward.apply();
           
            if (hdr.ipv4.protocol == TYPE_TCP){
                meta.dstPort = hdr.tcp.dstPort;
            }
            else if (hdr.ipv4.protocol == TYPE_UDP){
                meta.dstPort = hdr.udp.dstPort;
            }
            else {
                // drop();
            }

            fw.apply(); // Apply the firewall rules
        }
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply {  }
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
              hdr.ipv4.diffserv,
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