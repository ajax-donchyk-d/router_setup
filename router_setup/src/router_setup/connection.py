import time
from pathlib import Path

import paramiko


class Connection:
    def __init__(self, config) -> None:
        """
        Class for managing SSH connections to network equipment.

        Args:
            config (EdgeXConfig | BaseModel): Configuration object containing router parameters
            (router_ip_address, router_username, router_password).

        """
        self.ip: str = config.router_ip_address
        self.username: str = config.router_username
        self.password: str | None = config.router_password

        # Using pathlib.Path for cross-platform and reliable path handling
        self.key_filename: Path = Path.home() / ".ssh" / "id_rsa"
        self.port: int = 22

        self.client: paramiko.SSHClient | None = None

    def connect(self, timeout: int = 10) -> None:
        """Establishes an SSH connection with the device."""
        self.client = paramiko.SSHClient()
        # Automatically add unknown SSH host keys (useful for local routers)
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.client.connect(
                hostname=self.ip,
                port=self.port,
                username=self.username,
                password=self.password,
                key_filename=str(self.key_filename),  # Convert Path to str for paramiko
                timeout=timeout,
            )
            print(f"[+] Successfully connected to {self.username}@{self.ip}")
        except Exception as e:
            print(f"[-] Connection error to {self.ip}: {e}")
            raise

    def execute(self, commands: list[str]) -> str:
        """
        Executes a list of CLI commands sequentially within an interactive shell session.

        Args:
            commands: List of commands to be sent to the device.

        Returns:
             Accumulated shell output string.

        """
        if not self.client:
            raise RuntimeError("Connection is not established.")

            # Open an interactive shell channel for sequential command execution
        shell = self.client.invoke_shell()
        time.sleep(0.5)

        # Discard initial banner/welcome message from buffer
        if shell.recv_ready():
            shell.recv(4096)

        output = ""
        for cmd in commands:
            shell.send(cmd + "\n")

            # Read output continuously until the command finishes responding
            time.sleep(1)  # Initial delay for the command to start executing

            no_data_counter = 0
            while True:
                if shell.recv_ready():
                    chunk = shell.recv(4096).decode("utf-8", errors="ignore")
                    output += chunk
                    no_data_counter = 0  # Reset counter when data arrives
                else:
                    time.sleep(0.2)
                    no_data_counter += 1
                    # If no new data arrives within 1 second, assume command finished
                    if no_data_counter > 5:
                        break

        shell.close()
        return output

    def disconnect(self) -> None:
        """Closes the active SSH connection."""
        if self.client:
            self.client.close()
            print(f"[*] Connection to {self.ip} closed.")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
