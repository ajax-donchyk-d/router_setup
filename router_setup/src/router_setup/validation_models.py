import os
from typing import Any, ClassVar

from pydantic import BaseModel, model_validator

from router_setup.utils.exceptions import (
    EdgeXRouterConfigException,
)


class EdgeXConfig(BaseModel):
    # Collect validation errors instead of raising immediately
    configure_errors: ClassVar[list[Exception]] = []

    router_ip_address: str = ""
    router_username: str = ""
    router_password: str = ""

    class Config:
        """Allowing extra args."""

        extra = "allow"

    @classmethod
    def get_data(cls) -> dict[str, Any]:
        """Get data from .env file."""
        data = os.environ
        return {k.lower(): v for k, v in data.items()}

    @model_validator(mode="before")
    @classmethod
    def validate_router_config(cls, values: dict) -> dict:
        cls.configure_errors = []
        data = cls.get_data()

        router_ip_address = data.get("router_ip_address")
        router_username = data.get("router_username")
        router_password = data.get("router_password")

        if not router_ip_address:
            cls.configure_errors.append(
                EdgeXRouterConfigException(
                    "Missing 'router_ip_address' for connection, must be provided via .env file (ex. ROUTER_IP=192.168.1.1)"
                    " or --router_ip_address."
                )
            )

        if not router_username:
            cls.configure_errors.append(
                EdgeXRouterConfigException(
                    "Missing 'username' for connection, must be provided via .env file (ex. USERNAME=User)"
                    " or --router_username."
                )
            )

        if not router_password:
            cls.configure_errors.append(
                EdgeXRouterConfigException(
                    "Missing 'password' for connection, must be provided via .env file (ex. PASSWORD=Pass)"
                    " or --router_password."
                )
            )

        values.update(
            {
                "router_ip_address": router_ip_address,
                "router_username": router_username,
                "router_password": router_password,
            }
        )

        return values
