#!/usr/bin/env python3

import gi
import os
import subprocess
import psutil
import time
import platform
import hashlib
import json

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

HASH_FILE = "/etc/silk_integrity_hashes.json"
INTEGRITY_FILES = [
    "/etc/passwd",
    "/etc/ssh/sshd_config",
]

class SilkServerSettings(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.silkos.ServerSettings")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.window = Adw.ApplicationWindow(application=app)
        self.window.set_title("Silk Server Settings")
        self.window.set_default_size(720, 520)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin_top=20, margin_bottom=20, margin_start=20, margin_end=20)

        info_label = Gtk.Label(label=self.get_system_info())
        info_label.set_xalign(0)
        main_box.append(info_label)

        self.root_button = Gtk.Button()
        self.update_root_button_label()
        self.root_button.connect("clicked", self.toggle_root_login)
        main_box.append(self.root_button)

        self.ssh_button = Gtk.Button()
        self.update_ssh_button_label()
        self.ssh_button.connect("clicked", self.toggle_sshd)
        main_box.append(self.ssh_button)

        self.ssh_root_button = Gtk.Button()
        self.update_ssh_root_button_label()
        self.ssh_root_button.connect("clicked", self.toggle_ssh_root_login)
        main_box.append(self.ssh_root_button)

        self.firewall_button = Gtk.Button()
        self.update_firewall_button_label()
        self.firewall_button.connect("clicked", self.toggle_firewalld)
        main_box.append(self.firewall_button)

        update_button = Gtk.Button(label="Update system now")
        update_button.connect("clicked", self.run_updates)
        main_box.append(update_button)

        integrity_button = Gtk.Button(label="Run integrity check")
        integrity_button.connect("clicked", self.run_integrity_check)
        main_box.append(integrity_button)

        update_hashes_button = Gtk.Button(label="Update integrity hashes")
        update_hashes_button.connect("clicked", self.update_hashes)
        main_box.append(update_hashes_button)

        reboot_button = Gtk.Button(label="Reboot system")
        reboot_button.connect("clicked", self.reboot_system)
        main_box.append(reboot_button)

        shutdown_button = Gtk.Button(label="Shut down system")
        shutdown_button.connect("clicked", self.shutdown_system)
        main_box.append(shutdown_button)

        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", self.close_app)
        main_box.append(close_button)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(main_box)

        self.window.set_content(scrolled)
        self.window.present()

        self.initialize_hashes()

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
        label = "Allow root login again" if self.is_root_login_disabled() else "Disable root login in GDM"
        self.root_button.set_label(label)

    def toggle_root_login(self, button):
        conf_path = "/var/lib/AccountsService/users/root"
        try:
            if self.is_root_login_disabled():
                os.remove(conf_path)
                msg = "Root login has been re-enabled."
            else:
                os.makedirs(os.path.dirname(conf_path), exist_ok=True)
                with open(conf_path, "w") as f:
                    f.write("[User]\nSystemAccount=true\n")
                os.chmod(conf_path, 0o600)
                msg = "Root login has been disabled."
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
                msg = "SSH disabled."
            else:
                subprocess.run(["systemctl", "enable", "--now", "sshd"], check=True)
                msg = "SSH enabled."
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

    def close_app(self, button):
        self.quit()

    def initialize_hashes(self):
        if not os.path.exists(HASH_FILE):
            hashes = {}
            for path in INTEGRITY_FILES:
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                        hashes[path] = hashlib.sha256(data).hexdigest()
                except:
                    pass
            try:
                with open(HASH_FILE, "w") as f:
                    json.dump(hashes, f, indent=4)
            except Exception as e:
                self.show_info(f"Error writing hash file: {e}")

    def run_integrity_check(self, button):
        issues = []
        try:
            with open(HASH_FILE, "r") as f:
                stored_hashes = json.load(f)
        except Exception as e:
            self.show_info(f"Error loading hashes: {e}")
            return

        for path in INTEGRITY_FILES:
            try:
                with open(path, "rb") as f:
                    data = f.read()
                current_hash = hashlib.sha256(data).hexdigest()
                if stored_hashes.get(path) != current_hash:
                    issues.append(f"⚠️  {path} has been modified!")
            except Exception as e:
                issues.append(f"❌ {path} unreadable: {e}")

        if not issues:
            self.show_info("✅ All monitored files are intact.")
        else:
            self.show_info("\n".join(issues))

    def update_hashes(self, button):
        hashes = {}
        for path in INTEGRITY_FILES:
            try:
                with open(path, "rb") as f:
                    data = f.read()
                    hashes[path] = hashlib.sha256(data).hexdigest()
            except Exception as e:
                self.show_info(f"Error hashing {path}: {e}")
                return
        try:
            with open(HASH_FILE, "w") as f:
                json.dump(hashes, f, indent=4)
            self.show_info("Hashes updated successfully.")
        except Exception as e:
            self.show_info(f"Error writing updated hashes: {e}")

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
    app = SilkServerSettings()
    app.run()
