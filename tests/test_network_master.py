import ipaddress
import json
import socket
import tempfile
import unittest
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import NetworkMaster as nm


class ValueLabel:
    def __init__(self):
        self.value = None

    def config(self, **kwargs):
        self.value = kwargs.get('text')


class NetworkMasterTests(unittest.TestCase):
    def setUp(self):
        self.app = object.__new__(nm.NetworkMasterPro)
        self.app.ui = lambda callback: callback()
        self.app.update_status = lambda message: None
        self.app.closed = False

    def test_public_ip_failure_has_final_state(self):
        self.app.api_services = ['https://example.invalid']
        with patch.object(nm.requests, 'get', side_effect=nm.requests.Timeout):
            self.assertEqual(self.app.get_public_ip_info(), {'error': 'Public IP unavailable'})
        self.app.results = {'ip_info': {'error': 'Public IP unavailable'}}
        self.app.dashboard_ip_label = ValueLabel()
        self.app.quick_ip_label = ValueLabel()
        self.app.update_dashboard_ip()
        self.assertEqual(self.app.dashboard_ip_label.value, 'Unavailable')
        self.assertEqual(self.app.quick_ip_label.value, 'Unavailable')

    def test_scan_range_must_be_local_and_bounded(self):
        self.app.get_scan_interfaces = lambda: {'Ethernet': '192.168.1.10'}
        self.assertEqual(self.app.validate_scan_network('Ethernet', '192.168.1.0/24'),
                         ipaddress.ip_network('192.168.1.0/24'))
        with self.assertRaises(ValueError):
            self.app.validate_scan_network('Ethernet', '10.0.0.0/24')
        with self.assertRaises(ValueError):
            self.app.validate_scan_network('Ethernet', '192.168.0.0/16')

    def test_device_scan_only_returns_observed_neighbors(self):
        self.app.get_scan_interfaces = lambda: {'Ethernet': '192.168.1.10'}
        arp = SimpleNamespace(returncode=0, stdout=(
            '  192.168.1.1    aa-bb-cc-dd-ee-ff    dynamic\n'
            '  192.168.2.1    11-22-33-44-55-66    dynamic\n'))

        def fake_run(args, **_):
            return arp if args[:2] == ['arp', '-a'] else SimpleNamespace(returncode=0)

        with patch.object(nm.subprocess, 'run', side_effect=fake_run):
            devices = self.app.scan_network_devices('Ethernet', '192.168.1.0/24')
        self.assertEqual([device['ip'] for device in devices], ['192.168.1.1'])

    def test_security_report_does_not_claim_unmeasured_safety(self):
        class Sink:
            value = ''

            def insert(self, _, text):
                self.value += text

        self.app.security_result = Sink()
        self.app.get_network_info = lambda: {'local_ip': '192.168.1.10'}
        self.app.get_dns_info = lambda: {'DNS Servers': ['1.1.1.1']}
        with patch.object(socket, 'create_connection', side_effect=ConnectionRefusedError):
            self.app._security_scan_thread()
        self.assertIn('Port 80: not reachable', self.app.security_result.value)
        self.assertNotIn('No critical vulnerabilities', self.app.security_result.value)

    def test_json_export_includes_history(self):
        self.app.history = [{'time': '2026-10-19T12:00:00+03:30', 'event': 'snapshot',
                             'details': {'ip': '192.168.1.10'}}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.json'
            with patch.object(nm.filedialog, 'asksaveasfilename', return_value=str(path)):
                self.app.export_history('json')
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), self.app.history)

    def test_live_rates_use_counter_differences(self):
        self.app.traffic_interface = SimpleNamespace(get=lambda: 'All interfaces')
        self.app.root = SimpleNamespace(after=lambda *_: None)
        self.app.last_counters = None
        self.app.last_sample_time = None
        self.app.traffic_samples = deque(maxlen=60)
        self.app.dashboard_download_label = ValueLabel()
        self.app.dashboard_upload_label = ValueLabel()
        self.app.update_network_graph = lambda: None
        samples = [
            {'Ethernet': SimpleNamespace(bytes_sent=0, bytes_recv=0)},
            {'Ethernet': SimpleNamespace(bytes_sent=500_000, bytes_recv=1_000_000)},
        ]
        with patch.object(nm.psutil, 'net_io_counters', side_effect=samples), \
             patch.object(nm.time, 'monotonic', side_effect=[1.0, 2.0]):
            self.app.sample_traffic()
            self.app.sample_traffic()
        self.assertEqual(self.app.dashboard_download_label.value, '8.00 Mbps')
        self.assertEqual(self.app.dashboard_upload_label.value, '4.00 Mbps')


if __name__ == '__main__':
    unittest.main()
