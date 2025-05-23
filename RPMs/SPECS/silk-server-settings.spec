Name:           silk-server-settings
Version:        0.0.1
Release:        1%{?dist}
Summary:        SilkOS server configuration tool

License:        MIT
URL:            https://example.com/silk-server-settings
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3
Requires:       python3, gtk4, libadwaita

%description
A lightweight GTK4+Libadwaita application to configure basic server settings for SilkOS,
including SSH access, root login, system updates, and integrity checking.

%prep
%autosetup

%build
# Nothing to build for this Python/GTK app

%install
# Install the Python script
install -Dm755 silk-server-settings.py %{buildroot}%{_bindir}/silk-server-settings

# Install the .desktop launcher
install -Dm644 silk-server-settings.desktop %{buildroot}%{_datadir}/applications/silk-server-settings.desktop

%files
%license LICENSE
%doc README.md
%{_bindir}/silk-server-settings
%{_datadir}/applications/silk-server-settings.desktop

%changelog
* Fri May 23 2025 CommandCrafterx - 0.0.1
- Initial release

