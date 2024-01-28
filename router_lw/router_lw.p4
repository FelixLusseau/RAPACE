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

    // Counter of incoming packets
    counter(1, CounterType.packets) count_in;

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

    // Forward packets to the next hop with their tag
    table encap_routing {
        key = {
            hdr.segRoute.checkpoint: exact;
        }
        actions = {
            segRoute_port;
        }
        size = 1024;
    }

    apply {
        // Count the entering packets
        count_in.count(0);
        
        // Forward the packet to the next checkpoint only if tunnelled
        if (hdr.segRoute.isValid()){
            encap_routing.apply();
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
     apply {  }
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