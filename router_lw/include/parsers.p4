/*************************************************************************
*********************** P A R S E R  *******************************
*************************************************************************/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType){
            TYPE_SEGROUTE: parse_segrouting;
            TYPE_IPV4: reject;
            default: reject;
        }
    }

    state parse_segrouting {
        packet.extract(hdr.segRoute);
        transition accept;
    }
}

/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {

        // Parsed headers have to be added again into the packet
        packet.emit(hdr.ethernet);
        packet.emit(hdr.segRoute);
    }
}