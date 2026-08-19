<!-- markdownlint-disable MD018 MD036 MD012 MD047 MD010 MD033 -->
**Windows Version**

`Microsoft Windows [Version 10.0.26200.9168]` (Windows 11 Pro).

**WSL Version**

`2.7.8.0` (Microsoft Store). The same failure reproduces on `2.9.4.0` (Preview channel, 2026-08-19; wsldevicehost.dll v1.2.48.0, built 2026-07-09).

Version note: the guest-side port-tracking fixes #41051 (non-main-thread bind tracking, PIDFD_THREAD) and #41125 (listen() implicit autobind) both first ship in `2.9.5` (tag `b4e4ed9e`, 2026-08-11). The latest stable `2.7.12` (2026-08-18) does not contain them, and `2.9.4.0` does not either. Verified against the official tags (git merge-base --is-ancestor on a local mirror): merge commits `55d45784` (#41051) and `96b220c7` (#41125) are ancestors of `2.9.5`/`2.9.6`/`2.9.7` only, and the fix code (PIDFD_THREAD, listen() ParseListen) is present in the 2.9.5 tree. A third port-range fix, #41085 (mirrored-mode ephemeral-range cap, merge `86b51fc`), also first ships in 2.9.5; it is mirrored-specific, while this report is Consomme mode and reproduces on 2.9.4.0, which already contains that path's precursor #40597 - so the observed failures point at the guest-side tracker fixes (#41051/#41125) rather than the mirrored host-side path. As of 2026-08-19 no installable artifacts exist for 2.9.5+ (GitHub releases ship source archives only), so runtime verification on the fixed range is pending its Store release.

**Are you using WSL 1 or WSL 2?**

WSL 2 (Consomme networking). This machine never runs `wslrelay.exe`; Windows-side loopback listeners are held by `wsldevicehost.dll` inside `dllhost.exe`.

**Kernel Version**

`6.18.33.1-1` (default kernel).

**Distro Version**

Ubuntu 26.04.

**Other Software**

- Docker Desktop 29.7.2 - excluded by a three-round ON/OFF control (see Actual Behavior).
- The repro is a single-file Go program (Go 1.26, stdlib only; source below). No other software participates.

**Repro Steps**

1. Save the following as `main.go` and run it inside the WSL guest:

```go
package main

import (
	"fmt"
	"net"
	"time"
)

func main() {
	for round := 1; round <= 8; round++ {
		ln, err := net.Listen("tcp4", "127.0.0.1:0")
		if err != nil {
			panic(err)
		}
		port := ln.Addr().(*net.TCPAddr).Port

		start := time.Now()
		dialed := false
		for time.Since(start) < 30*time.Second {
			c, err := net.DialTimeout("tcp4", fmt.Sprintf("127.0.0.1:%d", port), 200*time.Millisecond)
			if err == nil {
				c.Close()
				dialed = true
				break
			}
			time.Sleep(10 * time.Millisecond)
		}
		fmt.Printf("round %d: port %d ok=%v (%v)\n", round, port, dialed, time.Since(start).Round(time.Millisecond))
		ln.Close()
	}
}
```

2. Observe: round 1 connects in ~50 ms; from round 2 the port is unreachable for the full per-round deadline in most runs. On 2026-08-18 this hit 5/5 runs from a healthy baseline (30 s deadlines); with a 90 s deadline the worst run showed rounds 2 and 4-8 never becoming reachable while rounds 1 and 3 succeeded at ~52 ms.

3. The same loop with `-rounds 200 -timeout 30s` was used for the 200-round run reported in Actual Behavior; the full probe (with Windows-side verification and fixed-port mode) is available on request.

**Expected Behavior**

Every fresh ephemeral loopback listener registers and connects within ~50-100 ms, every round, with no degradation within a run. Explicit ports and ephemeral ports behave identically.

**Actual Behavior**

- Ephemeral (127.0.0.1:0) registrations fail frequently even from a healthy state, and the failure self-amplifies within a run. After a full host reboot: **183/200 (91.5 %) fresh ephemeral binds never became reachable within 30 s**; the stall rate worsened monotonically across the run (82 % / 92 % / 94 % / 98 % per quarter), and the longest continuous stall was 49 rounds (>= 24.5 min). The failure is binary: either 11-26 ms success or >30 s unreachable.
- Fixed ports are immune: 29/29 rounds <1.1 ms; 128 concurrent fixed-port binds all reachable.
- Each intercepted bind costs a fixed ~10.4 ms round trip through the synchronous registration chain (guest seccomp -> localhost handler -> GNS channel -> Windows-side bind); latency under concurrent churn tracks concurrency linearly (128-way p50 1.32 s, 99.27 % >1 s) while throughput stays constant at ~96 binds/s. A cache-warm control locates the serialization in the guest-side notification-processing chain.
- Windows-side residue: device-host-owned loopback connections stay in TIME_WAIT for 81-187 s depending on close direction; same-four-tuple reuse fails fast with WSAEADDRINUSE (no SYN transmitted). Source anchor: the installed wsldevicehost.dll v1.2.14.0 matches openvmm commit 0bb5cf75 by trace-line fingerprint (tcp 27/27, udp 7/7, dns_tcp 2/2), where the TimeWait transition has no expiry timer (// TODO: start timer), SYN retransmission is disabled (SIO_TCP_INITIAL_RTO), and the Windows-side socket has no SO_REUSEADDR. Full measurement tables are in my follow-up on #41286.
- Docker Desktop is not a factor: three rounds after a fresh reboot (ON / OFF / ON) produced identical behavior.

**Impact**

Local development services that bind ephemeral loopback ports inside WSL (language servers, dev proxies, port-forwarders, test harnesses opening many short-lived connections) become intermittently unreachable from Windows for 30 s+, and the path degrades within a single run. No error appears in the guest or Windows event logs.

**Workaround**

Use fixed ports: explicit (127.0.0.1:<port>) binds register synchronously and never stalled in 29/29 rounds on this machine.

**Diagnostic Logs**

- Full WPR networking trace captured with the official `collect-wsl-logs.ps1 -LogProfile networking` (2026-08-18, ~102 MB, includes a repro run inside the capture window: rounds 1-3 half-blackhole, rounds 4-8 full registration stall).
- A new capture (2026-08-19, WSL core + TCPIP/Winsock providers, 36 s window) is attached in a comment on this issue; it includes a fresh 3-round probe run with a >30 s registration stall in round 3, plus `logs.etl`, the WSL service traces (`service.0-2.etl`), appx/optional-component state, the guest network configuration before/after, and the repro program + capture log.
- The ~102 MB bundle remains available via email per CONTRIBUTING.md.
- The complete evidence chain, measurement tables, and a step-by-step repro manual are in my comment on #41286 (linked above).

**Questions**

1. Is a TimeWait state without an expiry timer, on a socket without SO_REUSEADDR, intended for loopback connections owned by the device host?
2. Is disabling SYN retransmission (SIO_TCP_INITIAL_RTO) on Consomme sockets intended, given a dropped SYN then has no backstop?
3. The registration failures are consistent with running in the range missing #41051/#41125 (first shipped in 2.9.5), but the self-amplifying degradation (91.5 % stall rate, monotonically worsening) is not obviously explained by those two fixes - is this worth a separate look? I can re-run the full battery on 2.9.5 once it reaches the Store.

**Related issues checked before filing**

#40109 (bind(0) -> EADDRINUSE), #40187 (port-0 inline resolution), #41039/#41051 (non-main-thread tracking), #41117/#41125 (listen autobind), #40803 (IPv6 port-retention leak), #41162 (mirrored UDP retention), #40597/#41085 (mirrored-mode host ephemeral-range deny/cap - same 2.9.5 boundary, different (mirrored) path), openvmm issue #2313 (TCP retry/timeout acknowledged backlog). None covers this combination (Consomme + TCP loopback + ephemeral churn + registration chain).

<!-- markdownlint-enable -->