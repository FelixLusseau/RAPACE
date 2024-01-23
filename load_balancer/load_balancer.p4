/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

//My includes
#include "include/headers.p4"
#include "include/parsers.p4"

#define REGISTER_SIZE 1024
#define REGISTER_WIDTH 32

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

    register <bit<REGISTER_WIDTH>>(REGISTER_SIZE) loadbalance_seed;

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action update_flow_seed(){
        bit<12> register_index;

        hash(register_index,
	    HashAlgorithm.crc16,
	    (bit<1>)0,
	    { hdr.ipv4.dstAddr,
	      hdr.ipv4.srcAddr,
              hdr.tcp.srcPort,
              hdr.tcp.dstPort,
              hdr.ipv4.protocol},
	      (bit<12>)REGISTER_SIZE);
    }

    action set_nhop(macAddr_t dstAddr, egressSpec_t port) {

        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;

       //set the destination mac address that we got from the match in the table
        hdr.ethernet.dstAddr = dstAddr;

        //set the output port that we also get from the table
        standard_metadata.egress_spec = port;

        //decrease ttl by 1
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    table port_to_nhop {
        key = {
            standard_metadata.ingress_port: exact;
        }
        actions = {
            //send_to_out;
            set_nhop;
            drop;
        }   
        size = 1024;
        //default_action = send_to_out;
    }

    apply {
        //Only forward packets if they are IP and TTL > 1
        if (hdr.ipv4.isValid() && hdr.ipv4.ttl > 1){
            port_to_nhop.apply();
        }
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply{}
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
              hdr.ipv4.tos,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr},
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