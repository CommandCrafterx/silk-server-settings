#!/usr/bin/env python3

import gi
import os
import subprocess
import psutil
import time
import platform
import hashlib
import sys

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Relaunch with pkexec if not running as root
if os.geteuid() != 0:
    try:
        os.execvp("pkexec", ["pkexec", sys.executable] + sys.argv)
    except Exception as e:
        dialog = Gtk.MessageDialog(
            text="Root privileges are required to run Silk Server Settings.\n\nError: " + str(e),
            buttons=Gtk.ButtonsType.OK
        )
        dialog.set_title("Permission Required")
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.show()
        Gtk.main()
        sys.exit(1)

# Files for integrity check
INTEGRITY_FILES = {
    "/etc/passwd": None,
    "/etc/ssh/sshd_config": None,
}

HASH_FILE = "/etc/silk_integrity_hashes"

def load_hashes():
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            for line in f:
                path, hash_val = line.strip().split(" ", 1)
                if path in INTEGRITY_FILES:
                    INTEGRITY_FILES[path] = hash_val
    else:
        update_hashes()  # initialize if not present

def update_hashes():
    with open(HASH_FILE, "w") as f:
        for path in INTEGRITY_FILES:
            try:
                with open(path, "rb") as file_data:
                    file_hash = hashlib.sha256(file_data.read()).hexdigest()
                    INTEGRITY_FILES[path] = file_hash
                    f.write(f"{path} {file_hash}\n")
            except:
                continue

class SilkServerSettings(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.silkos.ServerSettings")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.window = Adw.ApplicationWindow(application=app)
        self.window.set_title("Silk Server Settings")
        self.window.set_default_size(720, 520)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin_top=20, margin_bottom=20, margin_start=20, margin_end=20)

        # Scrollable content
        scroll = Gtk.ScrolledWindow()
        scroll.set_child(main_box)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        info_label = Gtk.Label(label=self.get_system_info())
        info_label.set_xalign(0)
        main_box.append(info_label)

        # Root login toggle
        self.root_button = Gtk.Button()
        self.update_root_button_label()
        self.root_button.connect("clicked", self.toggle_root_login)
        main_box.append(self.root_button)

        # SSH service toggle
        self.ssh_button = Gtk.Button()
        self.update_ssh_button_label()
        self.ssh_button.connect("clicked", self.toggle_sshd)
        main_box.append(self.ssh_button)

        # SSH root login toggle
        self.ssh_root_button = Gtk.Button()
        self.update_ssh_root_button_label()
        self.ssh_root_button.connect("clicked", self.toggle_ssh_root_login)
        main_box.append(self.ssh_root_button)

        # Firewall toggle
        self.firewall_button = Gtk.Button()
        self.update_firewall_button_label()
        self.firewall_button.connect("clicked", self.toggle_firewalld)
        main_box.append(self.firewall_button)

        # System update
        update_button = Gtk.Button(label="Update system now")
        update_button.connect("clicked", self.run_updates)
        main_box.append(update_button)

        # Integrity check
        integrity_button = Gtk.Button(label="Run integrity check")
        integrity_button.connect("clicked", self.run_integrity_check)
        main_box.append(integrity_button)

        # Update hashes manually
        update_hashes_button = Gtk.Button(label="Update integrity hashes")
        update_hashes_button.connect("clicked", self.update_integrity_hashes)
        main_box.append(update_hashes_button)

        # Reboot & shutdown
        reboot_button = Gtk.Button(label="Reboot system")
        reboot_button.connect("clicked", self.reboot_system)
        main_box.append(reboot_button)

        shutdown_button = Gtk.Button(label="Shut down system")
        shutdown_button.connect("clicked", self.shutdown_system)
        main_box.append(shutdown_button)

        self.window.set_content(scroll)
        self.window.present()

    def get_system_info(self):
        kernel = platform.release()
        uptime = time.time() - psutil.boot_time()
        uptime_str = time.strftime('%H:%M:%S', time.gmtime(uptime))
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return f"""
🖥️  Kernel: {kernel}
🧠 RAM: {ram.used // (1024 ** 2)} MB / {ram.total // (1024 ** 2)} MB
💽 Disk: {disk.used // (1024 ** 3)} GB / {disk.total // (1024 ** 3)} GB
⏱️  Uptime: {uptime_str}
        """.strip()

    def is_root_login_disabled(self):
        return os.path.exists("/var/lib/AccountsService/users/root")

    def update_root_button_label(self):
        label = "Allow root login in GDM" if self.is_root_login_disabled() else "Disable root login in GDM"
        self.root_button.set_label(label)

    def toggle_root_login(self, button):
        conf_path = "/var/lib/AccountsService/users/root"
        try:
            if self.is_root_login_disabled():
                os.remove(conf_path)
                msg = "Root login enabled in GDM."
            else:
                os.makedirs(os.path.dirname(conf_path), exist_ok=True)
                with open(conf_path, "w") as f:
                    f.write("[User]\nSystemAccount=true\n")
                os.chmod(conf_path, 0o600)
                msg = "Root login disabled in GDM."
            self.show_info(msg)
        except Exception as e:
            self.show_info(f"Error: {e}")
        self.update_root_button_label()

    def get_firewalld_status(self):
        return subprocess.run(["systemctl", "is-active", "firewalld"], capture_output=True, text=True).stdout.strip() == "active"

    def update_firewall_button_label(self):
        label = "Disable firewall" if self.get_firewalld_status() else "Enable firewall"
        self.firewall_button.set_label(label)

    def toggle_firewalld(self, button):
        try:
            if self.get_firewalld_status():
                subprocess.run(["systemctl", "disable", "--now", "firewalld"], check=True)
                msg = "Firewall disabled."
            else:
                subprocess.run(["systemctl", "enable", "--now", "firewalld"], check=True)
                msg = "Firewall enabled."
            self.show_info(msg)
        except Exception as e:
            self.show_info(f"Error: {e}")
        self.update_firewall_button_label()

    def get_sshd_status(self):
        return subprocess.run(["systemctl", "is-active", "sshd"], capture_output=True, text=True).stdout.strip() == "active"

    def update_ssh_button_label(self):
        label = "Disable SSH" if self.get_sshd_status() else "Enable SSH"
        self.ssh_button.set_label(label)

    def toggle_sshd(self, button):
        try:
            if self.get_sshd_status():
                subprocess.run(["systemctl", "disable", "--now", "sshd"], check=True)
                msg = "SSH service disabled."
            else:
                subprocess.run(["systemctl", "enable", "--now", "sshd"], check=True)
                msg = "SSH service enabled."
            self.show_info(msg)
        except Exception as e:
            self.show_info(f"Error: {e}")
        self.update_ssh_button_label()

    def is_ssh_root_allowed(self):
        try:
            with open("/etc/ssh/sshd_config", "r") as f:
                for line in f:
                    if "PermitRootLogin" in line and not line.strip().startswith("#"):
                        return "yes" in line
        except:
            return False

    def update_ssh_root_button_label(self):
        label = "Disable SSH root login" if self.is_ssh_root_allowed() else "Enable SSH root login"
        self.ssh_root_button.set_label(label)

    def toggle_ssh_root_login(self, button):
        try:
            path = "/etc/ssh/sshd_config"
            with open(path, "r") as f:
                lines = f.readlines()

            modified = False
            new_lines = []
            for line in lines:
                if "PermitRootLogin" in line and not line.strip().startswith("#"):
                    new_val = "no" if self.is_ssh_root_allowed() else "yes"
                    new_lines.append(f"PermitRootLogin {new_val}\n")
                    modified = True
                else:
                    new_lines.append(line)

            if not modified:
                new_val = "no" if self.is_ssh_root_allowed() else "yes"
                new_lines.append(f"PermitRootLogin {new_val}\n")

            with open(path, "w") as f:
                f.writelines(new_lines)

            subprocess.run(["systemctl", "restart", "sshd"], check=True)
            self.show_info("SSH configuration updated.")
        except Exception as e:
            self.show_info(f"Error: {e}")
        self.update_ssh_root_button_label()

    def run_updates(self, button):
        try:
            subprocess.run(["pkexec", "dnf", "upgrade", "-y"])
            self.show_info("System updated.")
        except Exception as e:
            self.show_info(f"Error: {e}")

    def reboot_system(self, button):
        subprocess.run(["systemctl", "reboot"])

    def shutdown_system(self, button):
        subprocess.run(["systemctl", "poweroff"])

    def run_integrity_check(self, button):
        issues = []
        for path, known_hash in INTEGRITY_FILES.items():
            try:
                with open(path, "rb") as f:
                    data = f.read()
                current_hash = hashlib.sha256(data).hexdigest()
                if current_hash != known_hash:
                    issues.append(f"⚠️  {path} has been modified!")
            except Exception as e:
                issues.append(f"❌ Cannot read {path}: {e}")

        if not issues:
            self.show_info("✅ All monitored files are intact.")
        else:
            self.show_info("\n".join(issues))

    def update_integrity_hashes(self, button):
        update_hashes()
        self.show_info("Integrity hashes updated.")

    def show_info(self, message):
        dialog = Gtk.MessageDialog(
            text=message,
            buttons=Gtk.ButtonsType.OK,
            transient_for=self.window,
            modal=True
        )
        dialog.set_title("Silk Server Settings")
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.show()

if __name__ == "__main__":
    load_hashes()
    app = SilkServerSettings()
    app.run()
