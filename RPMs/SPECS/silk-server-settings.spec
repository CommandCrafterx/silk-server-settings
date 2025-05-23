Name:           silk-server-settings
Version:        0.0.1
Release:        1%{?dist}
Summary:        Simple GTK4/Adw app for Silk Server management

License:        MIT
URL:            https://github.com/CommandCrafterx/silk-server-settings
Source0:        silk-server-settings
Source1:        silk-server-settings.desktop
BuildArch:      noarch
Requires:       python3, python3-gi, adwaita-gtk3-theme, polkit (optional)

%description
A GTK4 and libadwaita based app to manage Silk Server settings like root login, sshd, firewall etc.

%prep
# no preparation needed

%build
# no build step

%install
rm -rf %{buildroot}

# Install the script as executable
install -d %{buildroot}/usr/bin
install -m 755 %{SOURCE0} %{buildroot}/usr/bin/silk-server-settings

# Install the .desktop file
install -d %{buildroot}/usr/share/applications
install -m 644 %{SOURCE1} %{buildroot}/usr/share/applications/silk-server-settings.desktop

%files
/usr/bin/silk-server-settings
/usr/share/applications/silk-server-settings.desktop

%changelog
* Thu May 23 2025 CommandCrafterx - 1.0-1
- Initial package
