# Network Master

A Python/Tkinter desktop tool for local network information, public IP lookup, DNS queries, speed tests, device discovery, geolocation, and basic local port checks. The blue glass-style interface uses a sidebar, NM icon, live metric cards, traffic chart, traffic distribution, and recent activity panels. The public IP card fetches the IP country's flag when the flag service is available.

## Requirements

- Python 3.10 or newer with Tkinter
- Windows or Linux with `ping` and `arp` available in `PATH`
- An internet connection for public IP, geolocation, and speed tests

## Install and run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python NetworkMaster.py
```

Tkinter is included with the standard Python installer on Windows. On Linux, install your distribution's `python3-tk` package if needed.

## Scope of the checks

## New tools

- **Live dashboard:** Shows current download and upload rates in Mbps. Choose an interface or combine all interfaces. The graph shows the last 60 samples, taken every two seconds. These are local traffic rates, not internet speed-test results.
- **Device scan:** Choose an active IPv4 interface and a CIDR range containing its address. Scans are limited to 256 addresses. Results include only observed ARP neighbors; devices that do not respond or appear in the ARP table may be missed. MAC vendor names are not inferred.
- **Monitor:** Checks TCP connectivity to the chosen host on port 443 every 15 seconds. Set a latency threshold and optionally watch for new devices about once a minute. Events appear in the Monitor tab; start and stop monitoring there.
- **History and export:** Save a snapshot of the latest results and export recorded events to JSON or CSV. History is held in memory until exported.
- **DNS tools:** Compare A-record answers and response times from the system resolver, Cloudflare, and Google DNS. The reverse lookup button queries PTR records for an IP entered in the Domain field.

The DNS resolver check shows locally configured resolvers and confirms a DNS query. It cannot prove whether DNS traffic leaks through a VPN; that requires an external controlled DNS endpoint.

The security tab tests whether selected TCP ports are reachable on `127.0.0.1`. It is a limited local check, not a vulnerability assessment.

## License

MIT. See [LICENSE](LICENSE).
