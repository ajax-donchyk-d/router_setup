import ipaddress
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, Protocol

import colorlog

from router_setup.connection import Connection
from router_setup.utils.constants import DHCPLease, RouterType
from router_setup.validation_models import EdgeXConfig


class Router(Protocol):
    router_ip_address: str | None
    router_username: str | None
    router_password: str | None
    connection: Connection

    def connect(self): ...


class RouterEdgeX:
    router_ip_address: str | None
    router_username: str | None
    router_password: str | None
    connection: Connection

    def __init__(
        self,
        router_ip_address: str,
        router_username: str,
        router_password: str,
        connection: Connection,
    ):
        self.connection = connection
        self.router_ip_address = router_ip_address
        self.router_username = router_username
        self.router_password = router_password
        self.logger = logging.getLogger(f"Router_{self.router_ip_address}")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = colorlog.StreamHandler()
            handler.setFormatter(
                colorlog.ColoredFormatter(
                    fmt="%(asctime)s [%(log_color)s%(levelname)s%(reset)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "bold_red",
                    },
                )
            )

            self.logger.handlers.clear()
            self.logger.addHandler(handler)

    def connect(self):
        with self.connection as conn:
            conn.connect()

    def show_dhcp_leases(self) -> str:
        with self.connection as conn:
            self.logger.info(f"DHCP leases on {self.router_ip_address} router:")
            return conn.execute(["show dhcp leases"])

    def show_port_forward(self) -> str:
        with self.connection as conn:
            self.logger.info(f"Port forward rules on {self.router_ip_address} router:")
            return conn.execute(["configure", "show port-forward | cat"])

    @classmethod
    def form_port_forward_rule_client_block(
        cls, dhcp_client: DHCPLease, start_rule_num: int
    ) -> list[list[str]]:
        """Form port forward rule client's block.

        Args:
            dhcp_client (DHCPLease): DHCP client, making rule for
            start_rule_num (int): start number for rule(s) block

        Returns:
            List: list of rule-blocks for DHCP client

        """

        name = dhcp_client.client_name.lower()
        ip = dhcp_client.dynamic_ip
        suffix = dhcp_client.ip_suffix
        host_id = dhcp_client.host_octet

        rule_blocks: list[list[str]] = []
        current_rule = start_rule_num

        def _build_edit_block(
            rule_num: int, desc: str, fwd_port: int | str, orig_port: int | str
        ) -> list[str]:
            return [
                f"edit port-forward rule {rule_num}",
                f"set description {desc}",
                f"set forward-to address {ip}",
                f"set forward-to port {fwd_port}",
                f"set original-port {orig_port}",
                "set protocol tcp_udp",
            ]

        if "orangepi" in name or "raspberry" in name:
            rule_blocks.append(
                _build_edit_block(
                    current_rule,
                    f"{dhcp_client.client_name}_{suffix}",
                    22,
                    f"200{host_id}",
                )
            )
            current_rule += 1

            rule_blocks.append(
                _build_edit_block(
                    current_rule,
                    f"tcp_{dhcp_client.client_name}_{suffix}",
                    3240,
                    f"201{host_id}",
                )
            )
            current_rule += 1

            scanner_port = f"9{host_id}0"
            rule_blocks.append(
                _build_edit_block(
                    current_rule,
                    f"scanner_{dhcp_client.client_name}_{suffix}",
                    scanner_port,
                    scanner_port,
                )
            )

        elif "jammer" in name or (len(name) == 12 and name.isalnum()):
            rule_blocks.append(
                _build_edit_block(
                    current_rule,
                    f"jammer_{dhcp_client.client_name}_{suffix}",
                    4196,
                    f"21{host_id}1",
                )
            )

        elif "hub" in name or "ajax" in name:
            octets = suffix.split("_")  # ex, ['222', '63']
            third_octet_last_char = octets[0][-1]  # '2'
            fourth_octet_padded = octets[1].zfill(3)  # '63' -> '063'

            orig_port = f"5{third_octet_last_char}{fourth_octet_padded}"  # '5' + '2' + '063' = '52063'

            rule_blocks.append(
                _build_edit_block(
                    current_rule,
                    f"hub_{dhcp_client.client_name}_{suffix}",
                    23,
                    orig_port,
                )
            )

        else:
            rule_blocks.append(
                _build_edit_block(
                    current_rule,
                    f"stand_{dhcp_client.client_name}_{suffix}",
                    23,
                    f"21{host_id}0",
                )
            )

        return rule_blocks

    @staticmethod
    def form_dhcp_leases_list(raw_output: str) -> list[DHCPLease]:
        """Form DHCP leases list from raw output."""
        leases: list[DHCPLease] = []

        for line in raw_output.splitlines():
            clean_line = line.strip()

            if (
                not clean_line
                or clean_line.startswith(("IP address", "----"))
                or "show dhcp leases" in clean_line
            ):
                continue

            parts = clean_line.split()

            if len(parts) >= 6:
                ip, mac, date_str, time_str, subnet, device_name = parts[:6]
                if ip.count(".") != 3:
                    continue

                try:
                    dt = datetime.strptime(
                        f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S"
                    ).replace(tzinfo=UTC)
                except ValueError:
                    dt = datetime.now(tz=UTC)

                leases.append(
                    DHCPLease(
                        dynamic_ip=ip,
                        hardware_address=mac,
                        lease_expiration=dt,
                        pool=subnet,
                        client_name=device_name,
                    )
                )

        return leases

    @staticmethod
    def form_static_rule_command(dhcp_client: DHCPLease) -> tuple[str, str]:
        static_hardware_cmd = (
            f"set service dhcp-server shared-network-name "
            f"{dhcp_client.pool} subnet {ipaddress.ip_interface(f'{dhcp_client.dynamic_ip}/24').network} static-mapping "
            f"{dhcp_client.client_name}_{dhcp_client.ip_suffix} mac-address {dhcp_client.hardware_address}"
        )
        static_ip_cmd = (
            f"set service dhcp-server shared-network-name "
            f"{dhcp_client.pool} subnet {ipaddress.ip_interface(f'{dhcp_client.dynamic_ip}/24').network} static-mapping "
            f"{dhcp_client.client_name}_{dhcp_client.ip_suffix} ip-address {dhcp_client.dynamic_ip}"
        )
        return static_hardware_cmd, static_ip_cmd

    def collect_dhcp_leases(self) -> list[DHCPLease,]:
        with self.connection as conn:
            raw_output = conn.execute(["show dhcp leases"])
            return self.form_dhcp_leases_list(raw_output=raw_output)

    def set_static_ip_addresses_for_leases(self, dhcp_leases: list[DHCPLease,]) -> None:
        for dhcp_client in dhcp_leases:
            hardware_cmd, ip_cmd = self.form_static_rule_command(dhcp_client)
            self.logger.info(
                f"Formed static rules for {dhcp_client.client_name}:\n"
                f"Hardware: {hardware_cmd}\n"
                f"IP: {ip_cmd}\n"
                f"Applying static rules to router.."
            )
            with self.connection as conn:
                conn.execute(
                    [
                        "configure",
                        hardware_cmd,
                        "commit",
                        "save",
                        ip_cmd,
                        "commit",
                        "save",
                    ]
                )
                self.logger.info(
                    "Verifying applied static for %s(%s) on %s...",
                    dhcp_client.client_name,
                    dhcp_client.hardware_address,
                    self.router_ip_address,
                )
                raw_output = conn.execute(
                    [f"show service dhcp-server | grep {dhcp_client.hardware_address}"]
                )
                has_static = any(
                    f"{dhcp_client.hardware_address}" in line
                    for line in raw_output.splitlines()
                )

                if has_static:
                    self.logger.info(
                        "Static for %s(%s) applied successfully!",
                        dhcp_client.client_name,
                        dhcp_client.hardware_address,
                    )
                else:
                    self.logger.error(
                        "Failed to apply static for %s(%s)!",
                        dhcp_client.client_name,
                        dhcp_client.hardware_address,
                    )

    def get_next_port_forward_rule_number(self) -> int:
        """Returns the next port forward rule number (last + 1)."""
        matches = re.findall(r"rule\s+(\d+)\s*\{", self.show_port_forward())
        return 1 if not matches else max([int(num) for num in matches]) + 1

    def set_forward_port_rules(self, rules_list: list[list[str]]) -> None:
        """Set forward port rules to router's configuration."""
        if not rules_list:
            self.logger.info("No port-forward rules to apply.")
            return

        with self.connection as conn:
            for rule_block in rules_list:
                conn.execute(["configure", *rule_block, "commit", "save"])

                rule_num = rule_block[0].split()[-1]
                self.logger.info(
                    "Verifying applied rule %s on %s...",
                    rule_num,
                    self.router_ip_address,
                )
                check_variable = f"rule {rule_num} {{"
                raw_output = conn.execute(
                    [f"show port-forward | grep {check_variable}"]
                )
                has_rule = any(
                    check_variable in line for line in raw_output.splitlines()
                )

                if has_rule:
                    self.logger.info(
                        "Rule %s for %s on %s port applied successfully!\n",
                        rule_num,
                        rule_block[1].split()[-1],
                        rule_block[4].split()[-1],
                    )
                else:
                    self.logger.error("Failed to apply rule %s!", rule_num)

    def get_text_config(self) -> str:
        """Retrieves full human-readable CLI configuration from the router."""
        with self.connection as conn:
            self.logger.info(
                "Reading /config/config.boot directly from %s...",
                self.router_ip_address,
            )
            raw_output = conn.execute(["cat /config/config.boot"])

        clean_lines = [
            line
            for line in raw_output.splitlines()
            if "cat /config/config.boot" not in line
            and not line.rstrip().endswith(":$")
            and not line.rstrip().endswith(":#")
        ]

        return "\n".join(clean_lines).strip()

    def save_text_config_backup(self, destination_dir: Path | str = "backups") -> Path:
        """Fetches and saves the human-readable CLI configuration to a text file."""
        dest_path = Path(destination_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        file_path = dest_path / f"config_{self.router_ip_address.replace('.', '_')}.txt"
        config_text = self.get_text_config()

        file_path.write_text(config_text, encoding="utf-8")

        self.logger.info(
            "Text configuration successfully saved to %s (bytes: %d)",
            file_path,
            file_path.stat().st_size,
        )
        return file_path


class RouterFactory:
    """Factory for creating router instances."""

    _registry: ClassVar[
        dict[
            RouterType,
            tuple[type[RouterEdgeX], type[EdgeXConfig]],
        ]
    ] = {RouterType.EDGEX: (RouterEdgeX, EdgeXConfig)}

    @classmethod
    def create(cls, config: dict[str, Any]) -> RouterEdgeX | Router:
        """Create router instance, based on provided config.

        Configuration priority:
            1. config['router_type'] (from argparse)
            2. Environment variable ROUTER_TYPE

        Returns:
            Router instance

        Raises:
            ExceptionGroup: If router configuration validation fails
            ValueError: If router type is not registered

        """

        router_type = RouterType(config.get("router_type", "").lower())
        router_class, router_validation_model = cls._registry[router_type]
        router_config = router_validation_model(**config)
        connection = Connection(router_config)

        # Check for validation errors
        if router_config.configure_errors:
            raise ExceptionGroup(
                "Invalid router configuration:", router_config.configure_errors
            )

        return router_class(
            router_ip_address=router_config.router_ip_address,
            router_username=router_config.router_username,
            router_password=router_config.router_password,
            connection=connection,
        )
