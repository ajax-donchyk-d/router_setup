import argparse
import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv

from router_setup.router_factory import RouterFactory

logger = logging.getLogger("Router")
logger.setLevel(logging.INFO)

load_dotenv()


def parse_command_line_args() -> dict[str, Any]:
    parser = argparse.ArgumentParser(
        description="Router setup service, connecting via ssh"
    )

    # Base args
    parser.add_argument(
        "-i",
        "--router_ip_address",
        type=str,
        help="Router IP address",
        required=True,
    )
    parser.add_argument(
        "-u",
        "--router_username",
        type=str,
        help="Enable detailed data logging",
        default="User's username for connection to router",
        required=True,
    )
    parser.add_argument(
        "-p",
        "--router_password",
        type=str,
        help="User's password for connection to router",
        default="password",
        required=True,
    )
    parser.add_argument(
        "--router_type",
        type=str,
        help="Router type (ex. edgex)",
        required=True,
    )
    parser.add_argument(
        "--save-backup",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Save config backup to local directory",
    )


def load_environment_config() -> dict[str, Any]:
    return {
        "router_ip_address": str(os.environ.get("ROUTER_IP_ADDRESS", "")),
        "router_username": str(os.environ.get("ROUTER_USERNAME", "")),
        "router_password": str(os.environ.get("ROUTER_PASSWORD", "")),
        "router_type": str(os.environ.get("ROUTER_TYPE", "")),
        "save_backup": os.environ.get("SAVE_BACKUP", "1").lower() in ("1", "true"),
    }


def main():
    config = (
        parse_command_line_args() if len(sys.argv) > 1 else load_environment_config()
    )
    router = RouterFactory.create(config)
    config.get("save_backup") and router.save_text_config_backup(
        destination_dir="backups"
    )
    dhcp_leases = router.collect_dhcp_leases()
    router.set_static_ip_addresses_for_leases(dhcp_leases)
    for dhcp_client in dhcp_leases:
        rules_list = router.form_port_forward_rule_client_block(
            dhcp_client=dhcp_client,
            start_rule_num=router.get_next_port_forward_rule_number(),
        )
        formatted_log_rules = "\n".join(
            f"  Block #{idx + 1}:\n" + "\n".join(f"    {cmd}" for cmd in block)
            for idx, block in enumerate(rules_list)
        )

        router.logger.info(
            "Formed rules for '%s':\n%s\nApplying rules to router...",
            dhcp_client.client_name,
            formatted_log_rules,
        )

        router.set_forward_port_rules(rules_list)


if __name__ == "__main__":
    main()
