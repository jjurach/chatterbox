#!/usr/bin/env python3
"""
OTA Deployment Tool for Chatterbox Devices

Deploys firmware binaries to ESP32 devices over Wi-Fi using the ESPHome OTA protocol.
Supports single device and batch deployments with progress indication and error handling.
Can auto-generate firmware and read credentials from secrets.yaml.

Usage:
    # Auto-generate firmware and deploy (reads IP & password from secrets.yaml)
    python ota_deploy.py

    # Deploy to single device with specific binary
    python ota_deploy.py --device 192.168.1.100 --binary firmware.bin

    # Deploy to multiple devices with password
    python ota_deploy.py --binary firmware.bin --batch devices.json --password mypassword

    # Deploy with custom port and retry logic
    python ota_deploy.py --device esp32.local --binary firmware.bin --port 8266 --retries 3

    # Auto-generate and deploy to specific device
    python ota_deploy.py --device esp32.local
"""

import argparse
import json
import hashlib
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import socket

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("Error: pyyaml library not found. Install with: pip install pyyaml")
    sys.exit(1)


class OTADeployError(Exception):
    """Base exception for OTA deployment errors."""
    pass


def read_secrets_yaml(key: str, secrets_path: Optional[str] = None) -> Optional[str]:
    """
    Read a value from secrets.yaml file.

    Args:
        key: The key to read (e.g., 'ota_password')
        secrets_path: Optional path to secrets file (default: firmware/secrets.yaml)

    Returns:
        The value if found, None otherwise
    """
    if secrets_path is None:
        secrets_path = Path(__file__).parent.parent / "firmware" / "secrets.yaml"
    else:
        secrets_path = Path(secrets_path)

    if not secrets_path.exists():
        return None

    try:
        with open(secrets_path, 'r') as f:
            secrets = yaml.safe_load(f) or {}
            return secrets.get(key)
    except Exception as e:
        print(f"Warning: Failed to read secrets file: {e}")
        return None


def generate_firmware(config_path: Optional[str] = None) -> Optional[str]:
    """
    Generate firmware binary using ESPHome.

    Args:
        config_path: Path to YAML config (default: firmware/voice-assistant.yaml)

    Returns:
        Path to generated firmware binary, None if generation fails
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "firmware" / "voice-assistant.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise OTADeployError(f"Config file not found: {config_path}")

    print(f"\n🔨 Generating firmware from {config_path}")
    print("   ⏳ Compiling... (this may take a few minutes)")

    try:
        result = subprocess.run(
            ["esphome", "compile", str(config_path)],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        # Filter output to hide verbose compilation lines but show important ones
        if result.stdout:
            for line in result.stdout.split('\n'):
                # Skip common verbose lines
                if any(skip in line for skip in [
                    'Compiling',
                    'Linking',
                    'ar ',
                    'cc1plus',
                    'Scanning',
                    'Building',
                    'Generating',
                    'HARDWARE_SPI',
                    'esphome.common',
                ]):
                    continue
                # Show important lines
                if any(keyword in line for keyword in [
                    'INFO',
                    'SUCCESS',
                    'ERROR',
                    'WARNING',
                    'Running',
                    'Done',
                ]):
                    print(f"   {line.strip()}")

        if result.returncode != 0:
            # Show error details
            error_output = result.stderr if result.stderr else result.stdout
            raise OTADeployError(
                f"ESPHome compilation failed. Check firmware/voice-assistant.yaml for errors.\n"
                f"Last output:\n{error_output[-500:]}"  # Last 500 chars
            )

        # Find the generated binary
        # ESPHome builds to .esphome/build/<device_name>/.pioenvs/<device_name>/firmware.bin
        # Or sometimes: .esphome/build/esp32-s3-box-3/.pioenvs/esp32-s3-box-3/firmware.bin
        config_stem = config_path.stem  # e.g., "voice-assistant"

        # Search in multiple possible locations
        search_paths = [
            Path(__file__).parent.parent / ".esphome" / "build" / "*" / ".pioenvs" / "*" / "firmware.bin",
            Path(__file__).parent.parent / ".esphome" / "build" / "**" / "firmware.bin",
        ]

        firmware_files = []
        for pattern in search_paths:
            firmware_files.extend(Path(pattern.parts[0]).glob(str(Path(*pattern.parts[1:]))))
            if firmware_files:
                break

        if not firmware_files:
            build_dir = Path(__file__).parent.parent / ".esphome" / "build"
            if build_dir.exists():
                # List what's actually in the build directory for debugging
                contents = list(build_dir.glob("*"))
                contents_str = "\n   ".join([str(c.relative_to(build_dir)) for c in contents])
                raise OTADeployError(
                    f"No firmware.bin found in build directory.\n"
                    f"Build directory contents:\n   {contents_str}\n"
                    f"Ensure firmware/voice-assistant.yaml is valid and ESPHome can compile it."
                )
            else:
                raise OTADeployError(
                    f"Build directory not found: {build_dir}\n"
                    f"ESPHome may not have completed successfully."
                )

        # Use the most recently modified one
        firmware_path = max(firmware_files, key=lambda p: p.stat().st_mtime)

        print(f"   ✅ Firmware generated successfully")
        print(f"   📦 Size: {firmware_path.stat().st_size / 1024 / 1024:.1f} MB")
        print(f"   📁 Path: {firmware_path}")
        return str(firmware_path)

    except subprocess.TimeoutExpired:
        raise OTADeployError("Firmware compilation timed out (>10 minutes)")
    except FileNotFoundError:
        raise OTADeployError(
            "ESPHome not found. Install with: pip install esphome"
        )
    except OTADeployError:
        raise
    except Exception as e:
        raise OTADeployError(f"Firmware generation failed: {e}")


class OTADeployer:
    """Handles OTA firmware deployment to ESP32 devices."""

    DEFAULT_PORT = 8266
    CHUNK_SIZE = 1024  # 1KB chunks for progress indication
    DEFAULT_RETRIES = 3
    DEFAULT_TIMEOUT = 60  # seconds

    def __init__(self, binary_path: str, password: Optional[str] = None,
                 port: int = DEFAULT_PORT, retries: int = DEFAULT_RETRIES,
                 timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize OTA deployer.

        Args:
            binary_path: Path to firmware binary file
            password: Optional OTA password for authentication
            port: OTA port on device (default: 8266)
            retries: Number of retry attempts (default: 3)
            timeout: Connection timeout in seconds (default: 60)

        Raises:
            OTADeployError: If binary file not found or not readable
        """
        self.binary_path = Path(binary_path)
        if not self.binary_path.exists():
            raise OTADeployError(f"Binary file not found: {binary_path}")
        if not self.binary_path.is_file():
            raise OTADeployError(f"Binary path is not a file: {binary_path}")

        self.password = password
        self.port = port
        self.retries = retries
        self.timeout = timeout
        self.binary_size = self.binary_path.stat().st_size
        self.binary_hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calculate MD5 hash of firmware binary."""
        md5 = hashlib.md5()
        with open(self.binary_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()

    def _get_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.retries,
            backoff_factor=1,  # Exponential backoff: 1, 2, 4 seconds
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _resolve_hostname(self, host: str) -> str:
        """Resolve hostname to IP address if needed."""
        try:
            # If it's already an IP address, return as-is
            socket.inet_aton(host)
            return host
        except socket.error:
            # It's a hostname, resolve it
            try:
                ip = socket.gethostbyname(host)
                print(f"  ℹ️  Resolved {host} → {ip}")
                return ip
            except socket.error as e:
                raise OTADeployError(f"Failed to resolve hostname '{host}': {e}")

    def deploy(self, device_host: str) -> bool:
        """
        Deploy firmware to a single device.

        Args:
            device_host: Device IP address or hostname

        Returns:
            True if deployment successful, False otherwise

        Raises:
            OTADeployError: If deployment fails after all retries
        """
        device_ip = self._resolve_hostname(device_host)
        ota_url = f"http://{device_ip}:{self.port}/update"

        print(f"\n📦 Deploying to {device_host} ({device_ip}:{self.port})")
        print(f"   Binary size: {self._format_size(self.binary_size)}")
        print(f"   Binary hash: {self.binary_hash}")

        session = self._get_session()

        try:
            # Prepare request
            files = {'file': open(self.binary_path, 'rb')}
            data = {}

            if self.password:
                data['pwd'] = self.password

            # Send update request with progress
            print(f"   ⏳ Uploading...", end='', flush=True)

            response = session.post(
                ota_url,
                files=files,
                data=data,
                timeout=self.timeout
            )

            files['file'].close()

            if response.status_code == 200:
                print("\r   ✅ Deployment successful!")
                if response.text:
                    print(f"   Response: {response.text.strip()}")
                return True
            elif response.status_code == 403:
                raise OTADeployError("Authentication failed (invalid password)")
            elif response.status_code == 400:
                raise OTADeployError(f"Bad request: {response.text}")
            else:
                raise OTADeployError(
                    f"Server returned status {response.status_code}: {response.text}"
                )

        except requests.exceptions.Timeout:
            raise OTADeployError("Connection timeout - device not responding")
        except requests.exceptions.ConnectionError as e:
            raise OTADeployError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            raise OTADeployError(f"Request failed: {e}")
        except Exception as e:
            raise OTADeployError(f"Unexpected error: {e}")
        finally:
            session.close()

    def deploy_batch(self, devices: List[Dict[str, str]]) -> Dict[str, bool]:
        """
        Deploy firmware to multiple devices.

        Args:
            devices: List of device configs with 'host' and optional 'password'

        Returns:
            Dictionary mapping device hosts to deployment success status
        """
        results = {}
        total = len(devices)

        print(f"\n🚀 Starting batch deployment to {total} device(s)")
        print(f"   Binary: {self.binary_path.name} ({self._format_size(self.binary_size)})")
        print("=" * 60)

        for idx, device_config in enumerate(devices, 1):
            host = device_config.get('host')
            if not host:
                print(f"[{idx}/{total}] ⚠️  Skipping device with missing 'host' field")
                results[f"unknown_{idx}"] = False
                continue

            device_password = device_config.get('password', self.password)

            try:
                # Temporarily set password for this device
                original_password = self.password
                self.password = device_password

                success = self.deploy(host)
                results[host] = success

                # Restore original password
                self.password = original_password

            except OTADeployError as e:
                print(f"   ❌ Deployment failed: {e}")
                results[host] = False
                self.password = original_password

            # Add delay between deployments to avoid overwhelming network
            if idx < total:
                time.sleep(1)

        print("\n" + "=" * 60)
        self._print_batch_summary(results)

        return results

    @staticmethod
    def _format_size(bytes_size: int) -> str:
        """Format bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"

    @staticmethod
    def _print_batch_summary(results: Dict[str, bool]) -> None:
        """Print summary of batch deployment results."""
        successful = sum(1 for v in results.values() if v)
        total = len(results)

        print(f"\n📊 Deployment Summary:")
        print(f"   Total devices: {total}")
        print(f"   Successful:   {successful} ✅")
        print(f"   Failed:       {total - successful} ❌")

        if total > 0:
            success_rate = (successful / total) * 100
            print(f"   Success rate: {success_rate:.1f}%")

        # Show failed devices
        failed = [host for host, success in results.items() if not success]
        if failed:
            print(f"\n   Failed devices:")
            for host in failed:
                print(f"   - {host}")


def load_batch_file(batch_file: str) -> List[Dict[str, str]]:
    """
    Load device list from JSON or CSV file.

    JSON format:
    [
        {"host": "192.168.1.100", "password": "optional_password"},
        {"host": "esp32.local"}
    ]

    CSV format (header required):
    host,password
    192.168.1.100,optional_password
    esp32.local,

    Args:
        batch_file: Path to batch file

    Returns:
        List of device configurations

    Raises:
        OTADeployError: If file cannot be read or parsed
    """
    path = Path(batch_file)

    if not path.exists():
        raise OTADeployError(f"Batch file not found: {batch_file}")

    try:
        if path.suffix.lower() == '.json':
            with open(path, 'r') as f:
                devices = json.load(f)
                if not isinstance(devices, list):
                    raise OTADeployError("JSON file must contain a list of devices")
                return devices

        elif path.suffix.lower() == '.csv':
            import csv
            devices = []
            with open(path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    device = {'host': row.get('host', '').strip()}
                    if row.get('password'):
                        device['password'] = row['password'].strip()
                    if device['host']:
                        devices.append(device)
            return devices

        else:
            raise OTADeployError(
                f"Unsupported file format: {path.suffix} (use .json or .csv)"
            )

    except json.JSONDecodeError as e:
        raise OTADeployError(f"Invalid JSON in batch file: {e}")
    except csv.Error as e:
        raise OTADeployError(f"Invalid CSV in batch file: {e}")
    except Exception as e:
        raise OTADeployError(f"Failed to read batch file: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Optional binary argument - will be auto-generated if not provided
    parser.add_argument('--binary',
                       help='Path to firmware binary file (auto-generated if not provided)')
    parser.add_argument('--config',
                       help='Path to ESPHome config (default: firmware/voice-assistant.yaml)')

    # Device selection (mutually exclusive, but both optional now)
    device_group = parser.add_mutually_exclusive_group()
    device_group.add_argument('--device',
                             help='Single device IP address or hostname (read from secrets.yaml if not provided)')
    device_group.add_argument('--batch',
                             help='Batch file (JSON or CSV) with device list')

    # Optional arguments
    parser.add_argument('--password',
                       help='OTA password for authentication (read from secrets.yaml if not provided)')
    parser.add_argument('--port', type=int, default=OTADeployer.DEFAULT_PORT,
                       help=f'OTA port (default: {OTADeployer.DEFAULT_PORT})')
    parser.add_argument('--retries', type=int, default=OTADeployer.DEFAULT_RETRIES,
                       help=f'Number of retry attempts (default: {OTADeployer.DEFAULT_RETRIES})')
    parser.add_argument('--timeout', type=int, default=OTADeployer.DEFAULT_TIMEOUT,
                       help=f'Connection timeout in seconds (default: {OTADeployer.DEFAULT_TIMEOUT})')
    parser.add_argument('--secrets',
                       help='Path to secrets.yaml file (default: firmware/secrets.yaml)')

    args = parser.parse_args()

    try:
        # Generate firmware if not provided
        binary_path = args.binary
        if not binary_path:
            binary_path = generate_firmware(args.config)

        # Get OTA password from secrets if not provided
        password = args.password
        if not password:
            password = read_secrets_yaml('ota_password', args.secrets)
            if password:
                print(f"✅ Read OTA password from secrets.yaml")
            else:
                print("⚠️  No OTA password provided and none found in secrets.yaml")

        # Get device from secrets if not provided and no batch file
        device = args.device
        if not device and not args.batch:
            device = read_secrets_yaml('ota_device', args.secrets)
            if device:
                print(f"✅ Read device address from secrets.yaml: {device}")
            else:
                print("ℹ️  No device specified and none found in secrets.yaml")

        # Create deployer
        deployer = OTADeployer(
            binary_path=binary_path,
            password=password,
            port=args.port,
            retries=args.retries,
            timeout=args.timeout
        )

        # Deploy based on mode
        if device:
            # Single device deployment
            success = deployer.deploy(device)
            sys.exit(0 if success else 1)

        elif args.batch:
            # Batch deployment
            devices = load_batch_file(args.batch)
            if not devices:
                print("Error: No devices found in batch file")
                sys.exit(1)

            results = deployer.deploy_batch(devices)

            # Exit with success only if all devices succeeded
            success_count = sum(1 for v in results.values() if v)
            sys.exit(0 if success_count == len(devices) else 1)

        else:
            # No device or batch specified
            parser.error("Either --device, --batch, or ota_device in secrets.yaml must be specified")

    except OTADeployError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
