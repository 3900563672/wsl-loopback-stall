Logs attached: a fresh WPR capture taken today (2026-08-19, 36 s window, WSL core + TCPIP/Winsock providers) with a 3-round probe run inside the capture window.

- Round 1 (port 43047): healthy, connected in ~14 ms guest-side / ~53 ms Windows-side check.
- Round 2 (port 37825): healthy, ~12 ms / ~53 ms.
- Round 3 (port 45117): stalled for the full 30 s per-round deadline - the failure reproduced while the trace was running.

The archive contains `logs.etl`, the WSL service traces (`service.0-2.etl`), `appxpackage.txt`, `optional-components.txt`, the guest network configuration before/after, the repro program, and the capture-window repro log.

The full ~102 MB networking trace from the official `collect-wsl-logs.ps1 -LogProfile networking` (2026-08-18, with the 8-round repro inside it) remains available via email per CONTRIBUTING.md if the wider provider set is needed.
