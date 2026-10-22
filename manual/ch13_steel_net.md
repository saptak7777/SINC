# Chapter 13: The `steel_net` Engine

Network packet headers can be read directly in SINC without copying buffers:

```sinc
// offsets for network packet headers
const IP_DST = 4;
const TCP_PORT = 8;

fn route_packet!(packet) [
    // Verify packet destination using constant lenses
    dst_ip = packet.IP_DST;
    dest_port = packet.TCP_PORT;
    
    // forward or discard...
    ret packet;
]
```

Network protocols often incur copy overhead when decoding into data structures. In SINC, packets are passed directly as linear pointers `packet~`, querying headers at fixed offsets with zero memory copying.

The standard library `steel_net` engine implements packet layouts and protocol fields using **Constant Lenses**.

---

## Zero-Copy Packet Parsing

When a packet is read from a hardware network interface card (NIC), `steel_sys` delivers a linear buffer pointer `packet~`. 

Instead of copying it into a struct, we use constant offsets:

```sinc
const TCP_DPORT = 9;

fn get_dport(packet) [
    // Read 64-bit value at offset (TCP_DPORT * 8)
    ret packet.TCP_DPORT;
]
```

Because `TCP_DPORT` is a constant, `packet.TCP_DPORT` is compiled directly into a single hardware load instruction:

```assembly
mov rax, [rax + 72]
```

Note that SINC constant lenses step in 8-byte words ($9 \times 8 = 72$ bytes), not individual byte offsets or 16-bit network fields, allowing direct single-cycle QWORD memory access.

This compiles straight to native machine instructions. You get the ergonomics of object-like property syntax (`packet.TCP_DPORT`) with the performance of direct hardware offset assembly.
