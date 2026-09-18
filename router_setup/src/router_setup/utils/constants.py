from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RouterType(Enum):
    """Supported router types."""

    EDGEX = "edgex"


@dataclass
class DHCPLease:
    """DCHPLease class.

    attributes:
        dymamic_ip (str): IP address given when client detected on router (ex. 192.168.222.63)
        hardware_address (str): client's mac-address (ex. 02:00:2b:44:ee:8a)
        lease_expiration (datetime): expiration date and time of dymnamic ip (ex. 2026/08/12 08:36:13)
        pool (str): pool (subnet) of client's dymanic IP (ex. LAN-222)
        client_name (str): client's name (ex. orangepizero2)

    Example for full DHCP-lease on router (EdgeX):
        192.168.222.63  02:00:2b:44:ee:8a  2026/08/12 08:36:13  LAN-222    orangepizero2

    """

    dynamic_ip: str = ""
    hardware_address: str = ""
    lease_expiration: datetime = field(default_factory=datetime.now)
    pool: str = ""
    client_name: str = ""

    @property
    def ip_suffix(self) -> str:
        """Return unique IP-suffix (ex. "222_63")."""
        if not self.dynamic_ip:
            return ""
        parts = self.dynamic_ip.split(".")
        if len(parts) == 4:
            return f"{parts[2]}_{parts[3]}"
        return ""

    @property
    def host_octet(self) -> str:
        """Returns last octet from IP (ex.'192.168.222.63' -> '63')."""
        return self.dynamic_ip.split(".")[-1] if self.dynamic_ip else ""

    @property
    def host_octet_padded(self) -> str:
        """Returns last octet from IP with 0 if length of a last octet equals
        or less than 2 ('63' -> '063' або '9' -> '009').
        """

        return self.host_octet.zfill(3)
