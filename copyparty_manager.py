# copyparty_manager.py - Copyparty Server Management
import os
import subprocess
import time
import signal
import sys
import socket
from pathlib import Path


class CopypartyManager:
    """Manages the Copyparty server lifecycle."""

    def __init__(self):
        self.process = None
        self.config = self._get_config()
        self._ensure_upload_directory()

    def _get_config(self):
        """Get Copyparty configuration from environment variables."""
        # Get the backend directory (where this file is located)
        backend_dir = Path(__file__).parent
        instance_dir = backend_dir / 'instance'
        copyparty_files_dir = instance_dir / 'copyparty-files'

        return {
            'base_url': os.getenv('COPYPARTY_BASE_URL', 'http://localhost:3923'),
            'port': os.getenv('COPYPARTY_PORT', '3923'),
            'host': os.getenv('COPYPARTY_HOST', '127.0.0.1'),
            'upload_password': os.getenv('COPYPARTY_UPLOAD_PASSWORD', ''),
            'api_token': os.getenv('COPYPARTY_API_TOKEN', ''),
            'folder_prefix': os.getenv('COPYPARTY_FOLDER_PREFIX', 'bookings'),
            'files_directory': str(copyparty_files_dir),
            'instance_dir': str(instance_dir)
        }

    def _ensure_upload_directory(self):
        """Ensure the upload directory exists."""
        files_dir = Path(self.config['files_directory'])
        files_dir.mkdir(parents=True, exist_ok=True)
        print(f"Copyparty files directory: {files_dir}")

    def is_running(self):
        """Check if Copyparty is already running on the configured port."""
        port = int(self.config['port'])
        host = self.config['host']

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0

    def start(self):
        """Start Copyparty server."""
        if self.is_running():
            print(f"Copyparty is already running on {self.config['host']}:{self.config['port']}")
            return True

        try:
            # Build copyparty command with correct arguments
            cmd = [
                'copyparty',
                '-i', self.config['host'],  # IP to bind to
                '-p', self.config['port'],  # Port to listen on
                '--chdir', self.config['files_directory'],  # Change working directory
                '--name', 'Booking Documents Server',
            ]

            # Add volume mapping (SRC:DST:FLAG format)
            if self.config['upload_password']:
                # Create account with write permissions
                cmd.extend(['-a', f"upload:{self.config['upload_password']}"])
                # Create volume with read/write for authenticated user
                cmd.extend(['-v', '.::rw=upload'])
            else:
                # Create anonymous volume with read/write permissions
                cmd.extend(['-v', '.::rw'])

            # Start copyparty process
            print(f"Starting Copyparty server...")
            print(f"  Host: {self.config['host']}")
            print(f"  Port: {self.config['port']}")
            print(f"  Files Directory: {self.config['files_directory']}")
            print(f"  Upload Password: {'Set' if self.config['upload_password'] else 'None (anonymous)'}")

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.config['files_directory'],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )

            # Wait a moment and check if it started successfully
            time.sleep(3)
            if self.process.poll() is None and self.is_running():
                print(f"[OK] Copyparty started successfully on http://{self.config['host']}:{self.config['port']}")
                return True
            else:
                stdout, stderr = self.process.communicate()
                print(f"[ERROR] Failed to start Copyparty:")
                if stdout:
                    print(f"STDOUT: {stdout.decode()}")
                if stderr:
                    print(f"STDERR: {stderr.decode()}")
                return False

        except FileNotFoundError:
            print("[ERROR] Copyparty not found! Please install it with: pip install copyparty")
            return False
        except Exception as e:
            print(f"[ERROR] Error starting Copyparty: {e}")
            return False

    def stop(self):
        """Stop Copyparty server."""
        if not self.process or self.process.poll() is not None:
            return

        try:
            print("Stopping Copyparty server...")
            if sys.platform == 'win32':
                # On Windows, use CTRL_BREAK_EVENT
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                # On Unix-like systems, use SIGTERM
                self.process.terminate()

            # Wait for process to terminate
            self.process.wait(timeout=5)
            print("[OK] Copyparty stopped successfully")
        except subprocess.TimeoutExpired:
            print("[WARN] Copyparty didn't stop gracefully, forcing termination...")
            self.process.kill()
            self.process.wait()
            print("[OK] Copyparty forcefully terminated")
        except Exception as e:
            print(f"[ERROR] Error stopping Copyparty: {e}")
        finally:
            self.process = None

    def restart(self):
        """Restart Copyparty server."""
        print("Restarting Copyparty server...")
        self.stop()
        time.sleep(1)
        return self.start()

    def get_status(self):
        """Get Copyparty server status."""
        return {
            'running': self.is_running(),
            'process_alive': self.process is not None and self.process.poll() is None,
            'config': self.config,
            'pid': self.process.pid if self.process else None
        }

    def get_upload_url(self):
        """Get the upload URL for the server."""
        return f"http://{self.config['host']}:{self.config['port']}"

    def get_files_directory(self):
        """Get the files storage directory."""
        return self.config['files_directory']


# Global instance for easy access
copyparty_manager = CopypartyManager()


# Convenience functions
def start_copyparty():
    """Start the global Copyparty instance."""
    return copyparty_manager.start()


def stop_copyparty():
    """Stop the global Copyparty instance."""
    return copyparty_manager.stop()


def is_copyparty_running():
    """Check if the global Copyparty instance is running."""
    return copyparty_manager.is_running()


def get_copyparty_status():
    """Get status of the global Copyparty instance."""
    return copyparty_manager.get_status()


if __name__ == '__main__':
    # Test the copyparty manager
    print("Testing Copyparty Manager...")

    manager = CopypartyManager()
    print("Configuration:", manager.config)

    print("\nStarting Copyparty...")
    if manager.start():
        print("Copyparty started successfully!")

        print(f"Upload URL: {manager.get_upload_url()}")
        print(f"Files Directory: {manager.get_files_directory()}")
        print("Status:", manager.get_status())

        input("Press Enter to stop Copyparty...")
        manager.stop()
    else:
        print("Failed to start Copyparty!")