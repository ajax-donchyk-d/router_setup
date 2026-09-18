from datetime import UTC, datetime

import pytest

from router_setup.router_factory import RouterEdgeX
from router_setup.utils.constants import DHCPLease


@pytest.mark.parametrize(
    "raw_input, expected_output",
    [
        (
            """IP address      Hardware Address   Lease expiration     Pool       Client Name
    ----------      ----------------   ----------------     ----       -----------
    192.168.222.63  02:00:2b:44:ee:8a  2026/08/12 08:36:13  LAN-222    orangepizero2""",
            [
                DHCPLease(
                    dynamic_ip="192.168.222.63",
                    hardware_address="02:00:2b:44:ee:8a",
                    lease_expiration=datetime(2026, 8, 12, 8, 36, 13, tzinfo=UTC),
                    pool="LAN-222",
                    client_name="orangepizero2",
                )
            ],
        ),
        (
            """IP address      Hardware Address   Lease expiration     Pool       Client Name
    ----------      ----------------   ----------------     ----       -----------
    192.168.222.56  02:00:00:01:02:12  2026/08/12 08:32:59  LAN-222    MCG3-2010212
    192.168.222.65  28:7c:11:80:51:92  2026/08/12 08:32:59  LAN-222    287C11805192""",
            [
                DHCPLease(
                    dynamic_ip="192.168.222.56",
                    hardware_address="02:00:00:01:02:12",
                    lease_expiration=datetime(2026, 8, 12, 8, 32, 59, tzinfo=UTC),
                    pool="LAN-222",
                    client_name="MCG3-2010212",
                ),
                DHCPLease(
                    dynamic_ip="192.168.222.65",
                    hardware_address="28:7c:11:80:51:92",
                    lease_expiration=datetime(2026, 8, 12, 8, 32, 59, tzinfo=UTC),
                    pool="LAN-222",
                    client_name="287C11805192",
                ),
            ],
        ),
        (
            """IP address      Hardware Address   Lease expiration     Pool       Client Name
    ----------      ----------------   ----------------     ----       -----------""",
            [],
        ),
    ],
)
def test_collect_dhcp_leases_output(raw_input, expected_output):
    result = RouterEdgeX.form_dhcp_leases_list(raw_input)
    assert result == expected_output


@pytest.mark.parametrize(
    "dhcp_lease, static_cmds",
    [
        (
            DHCPLease(
                dynamic_ip="192.168.222.56",
                hardware_address="02:00:00:01:02:12",
                lease_expiration=datetime(2026, 8, 12, 8, 32, 59, tzinfo=UTC),
                pool="LAN-222",
                client_name="MCG3-2010212",
            ),
            (
                "set service dhcp-server shared-network-name LAN-222 subnet 192.168.222.0/24 static-mapping MCG3-2010212_222_56 mac-address 02:00:00:01:02:12",
                "set service dhcp-server shared-network-name LAN-222 subnet 192.168.222.0/24 static-mapping MCG3-2010212_222_56 ip-address 192.168.222.56",
            ),
        ),
        (
            DHCPLease(
                dynamic_ip="192.168.222.63",
                hardware_address="02:00:2b:44:ee:8a",
                lease_expiration=datetime(2026, 8, 12, 8, 36, 13, tzinfo=UTC),
                pool="LAN-222",
                client_name="orangepizero2",
            ),
            (
                "set service dhcp-server shared-network-name LAN-222 subnet 192.168.222.0/24 static-mapping orangepizero2_222_63 mac-address 02:00:2b:44:ee:8a",
                "set service dhcp-server shared-network-name LAN-222 subnet 192.168.222.0/24 static-mapping orangepizero2_222_63 ip-address 192.168.222.63",
            ),
        ),
    ],
)
def test_form_static_rule_cmd(dhcp_lease, static_cmds):
    result = RouterEdgeX.form_static_rule_command(dhcp_lease)
    assert result == static_cmds


@pytest.mark.parametrize(
    "dhcp_client, start_rule, expected_cmds",
    [
        (
            DHCPLease(
                dynamic_ip="192.168.222.63",
                hardware_address="02:00:2b:44:ee:8a",
                lease_expiration=datetime(2026, 8, 12, 8, 36, 13, tzinfo=UTC),
                pool="LAN-222",
                client_name="orangepizero2",
            ),
            17,
            [
                [
                    "edit port-forward rule 17",
                    "set description orangepizero2_222_63",
                    "set forward-to address 192.168.222.63",
                    "set forward-to port 22",
                    "set original-port 20063",
                    "set protocol tcp_udp",
                ],
                [
                    "edit port-forward rule 18",
                    "set description tcp_orangepizero2_222_63",
                    "set forward-to address 192.168.222.63",
                    "set forward-to port 3240",
                    "set original-port 20163",
                    "set protocol tcp_udp",
                ],
                [
                    "edit port-forward rule 19",
                    "set description scanner_orangepizero2_222_63",
                    "set forward-to address 192.168.222.63",
                    "set forward-to port 9630",
                    "set original-port 9630",
                    "set protocol tcp_udp",
                ],
            ],
        ),
        (
            DHCPLease(
                dynamic_ip="192.168.222.63",
                hardware_address="02:00:2b:44:ee:8a",
                lease_expiration=datetime(2026, 8, 12, 8, 36, 13, tzinfo=UTC),
                pool="LAN-222",
                client_name="Ajax-002B93D9",
            ),
            5,
            [
                [
                    "edit port-forward rule 5",
                    "set description hub_Ajax-002B93D9_222_63",
                    "set forward-to address 192.168.222.63",
                    "set forward-to port 23",
                    "set original-port 52063",
                    "set protocol tcp_udp",
                ],
            ],
        ),
        (
            DHCPLease(
                dynamic_ip="192.168.222.63",
                hardware_address="02:00:2b:44:ee:8a",
                lease_expiration=datetime(2026, 8, 12, 8, 36, 13, tzinfo=UTC),
                pool="LAN-222",
                client_name="SomeUnknownStand",
            ),
            1,
            [
                [
                    "edit port-forward rule 1",
                    "set description stand_SomeUnknownStand_222_63",
                    "set forward-to address 192.168.222.63",
                    "set forward-to port 23",
                    "set original-port 21630",
                    "set protocol tcp_udp",
                ],
            ],
        ),
        (
            DHCPLease(
                dynamic_ip="192.168.222.63",
                hardware_address="02:00:2b:44:ee:8a",
                lease_expiration=datetime(2026, 8, 12, 8, 36, 13, tzinfo=UTC),
                pool="LAN-222",
                client_name="287AB361999E",
            ),
            135,
            [
                [
                    "edit port-forward rule 135",
                    "set description jammer_287AB361999E_222_63",
                    "set forward-to address 192.168.222.63",
                    "set forward-to port 4196",
                    "set original-port 21631",
                    "set protocol tcp_udp",
                ],
            ],
        ),
    ],
)
def test_form_port_forward_rule_client_block(
    dhcp_client,
    start_rule,
    expected_cmds,
):
    cmds = RouterEdgeX.form_port_forward_rule_client_block(
        dhcp_client=dhcp_client, start_rule_num=start_rule
    )
    assert cmds == expected_cmds
