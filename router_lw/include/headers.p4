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

struct headers {
    ethernet_t   ethernet;
    segRoute_t   segRoute;
}

struct metadata {
    
}
