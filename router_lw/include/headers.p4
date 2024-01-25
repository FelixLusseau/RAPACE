/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

const bit<16> TYPE_IPV4 = 0x800;
const bit<16> TYPE_SEGROUTE = 0x1234;

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;

header segRoute_t {
    bit<8>    checkpoint;
}

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<6>    dscp;
    bit<2>    ecn;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

struct headers {
    ethernet_t   ethernet;
    segRoute_t   segRoute;
    ipv4_t       ipv4;
}
