# KDE Pass Runner

🔑 **A KRunner plugin for seamless integration with [pass](https://www.passwordstore.org/) - the standard Unix password manager**

![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-blue.svg)
![KDE](https://img.shields.io/badge/KDE-Plasma%206-blue.svg)

## Features

- 🔍 **Quick Search**: Search your passwords directly from KRunner
- 📋 **Clipboard Copy**: Copy passwords to clipboard with a single keystroke
- ⌨️ **Auto-Type**: Automatically type passwords into active windows (X11 and Wayland support)
- 🏷️ **Fuzzy Matching**: Intelligent search with fuzzy matching algorithm
- 🔒 **Secure**: Uses your existing GPG setup and pass configuration
- 🌐 **Multi-language**: Supports multiple languages in the UI
- 📢 **Notifications**: Visual feedback for all actions

## Demo

Type `pass` in KRunner to see all your passwords, or `pass github` to filter by search term:

```
🔑 github.com/username          (Press Enter to copy, Ctrl+Enter to type)
🔑 work/github-enterprise       (Press Enter to copy, Ctrl+Enter to type)  
🔑 personal/github-backup       (Press Enter to copy, Ctrl+Enter to type)
```

## Installation

### Prerequisites

**Required:**
- [pass](https://www.passwordstore.org/) (password-store) installed and initialized
- Python 3.6+
- python3-dbus
- python3-gi (python3-gobject)
- KDE Plasma 6

**Optional:**
- `xdotool` for auto-typing functionality on X11
- `wtype` for auto-typing functionality on Wayland
- `libnotify-bin` for desktop notifications

### Install Dependencies

**Debian/Ubuntu:**
```bash
sudo apt install pass python3-dbus python3-gi xdotool libnotify-bin
# For Wayland support:
sudo apt install wtype  # If available in your distro
# Or build from source: https://github.com/atx/wtype
```

**Fedora:**
```bash
sudo dnf install pass python3-dbus python3-gobject xdotool libnotify wtype
```

**Arch Linux:**
```bash
sudo pacman -S pass python3-dbus python-gobject xdotool libnotify wtype
```

### Wayland Configuration

If you're using Wayland, you need to enable the virtual keyboard protocol for auto-typing to work:

1. Edit or create `~/.config/kwinrc`:
   ```bash
   mkdir -p ~/.config
   nano ~/.config/kwinrc
   ```

2. Add or modify the following section:
   ```ini
   [Wayland]
   VirtualKeyboardEnabled=true
   ```

3. Save the file and restart your Wayland session (log out and log back in)

### Install KDE Pass Runner

1. **Clone and install in development mode:**
   ```bash
   git clone https://github.com/rakanalh/kde-krunner-pass.git
   cd kde-krunner-pass
   ./install.sh
   ```

### Manual Installation

If you prefer to install manually:

```bash
# Install to user directory
mkdir -p ~/.local/bin ~/.local/share/dbus-1/services ~/.local/share/krunner/dbusplugins

# Copy files
cp src/kde-pass-runner.py ~/.local/bin/
cp src/pass-interface.py ~/.local/bin/
chmod +x ~/.local/bin/kde-pass-runner.py ~/.local/bin/pass-interface.py

# Install service files
cp services/plasma-runner-pass.desktop ~/.local/share/krunner/dbusplugins/
sed "s|/usr/bin/kde-pass-runner.py|$HOME/.local/bin/kde-pass-runner.py|" \
    services/org.kde.krunner.pass.service > \
    ~/.local/share/dbus-1/services/org.kde.krunner.pass.service

# Reload services
kbuildsycoca6

# Restart KRunner
kquitapp6 krunner
krunner &
```

## Usage

### Basic Usage

1. **Open KRunner**: Press `Alt+F2` or `Alt+Space`

2. **List all passwords**: Type `pass`
   ```
   pass
   ```

3. **Search passwords**: Type `pass` followed by a search term
   ```
   pass github
   pass work/
   pass email
   ```

### Actions

- **Copy to Clipboard** (default): Press `Enter` on any password entry
- **Auto-Type Password**: Press `Ctrl+Enter` (requires xdotool on X11 or wtype on Wayland)

### Advanced Usage

The plugin supports fuzzy matching, so these searches will all work:

- `pass gh` → matches `github.com`
- `pass wrk` → matches `work/email`
- `pass gmai` → matches `personal/gmail`

## Configuration

### Pass Configuration

The plugin respects your existing pass configuration:

- **Password Store Location**: `~/.password-store` (or `$PASSWORD_STORE_DIR`)
- **GPG Key**: Uses your configured pass GPG key
- **Directory Structure**: Maintains your existing organization

### Plugin Configuration

The plugin uses your existing pass configuration and doesn't require additional setup. However, you can customize:

- **Cache Behavior**: Password list is cached until KRunner session ends
- **Search Algorithm**: Uses built-in fuzzy matching
- **Timeout Settings**: Inherits from your pass/GPG configuration

## Troubleshooting

### Plugin Not Appearing

1. **Check if the service is registered:**
   ```bash
   ls ~/.local/share/krunner/dbusplugins/plasma-runner-pass.desktop
   ls ~/.local/share/dbus-1/services/org.kde.krunner.pass.service
   ```

2. **Rebuild KDE cache:**
   ```bash
   kbuildsycoca6
   ```

3. **Restart KRunner:**
   ```bash
   kquitapp6 krunner
   krunner &
   ```

### Auto-Type Not Working

1. **Check your display server:**
   ```bash
   echo $XDG_SESSION_TYPE
   ```
   This will show whether you're running X11 or Wayland.

2. **For X11 sessions:**
   - Check if xdotool is installed:
     ```bash
     which xdotool
     ```
   - Test xdotool manually:
     ```bash
     echo "test" | xdotool type --file -
     ```

3. **For Wayland sessions:**
   - Check if wtype is installed:
     ```bash
     which wtype
     ```
   - Test wtype manually:
     ```bash
     echo "test" | wtype -
     ```
   - Check if virtual keyboard is enabled:
     ```bash
     grep -i virtualkeyboard ~/.config/kwinrc
     ```

4. **Check window focus:** Auto-type requires the target window to be active

### Pass Integration Issues

1. **Verify pass is working:**
   ```bash
   pass ls
   ```

2. **Check GPG key setup:**
   ```bash
   pass init your-gpg-key-id
   ```

3. **Test password retrieval:**
   ```bash
   pass show some-password
   ```

### Debug Mode

Run the service manually to see debug output:

```bash
# Stop the automatic service
pkill -f kde-pass-runner.py

# Run manually with debug output
~/.local/bin/kde-pass-runner.py
```

## Architecture

This plugin uses the **DBus service approach** introduced in KDE Plasma 6, which offers several advantages:

- **No Compilation**: Pure Python implementation
- **Easy Debugging**: Run standalone for testing
- **External Integration**: Perfect for tools like pass
- **Cross-Platform**: Works on any system with DBus
- **Display Server Support**: Works on both X11 and Wayland

### Project Structure

```
KDE-Pass/
├── src/
│   ├── kde-pass-runner.py      # Main DBus service
│   └── pass-interface.py       # Auto-typing functionality (X11/Wayland)
├── services/
│   ├── org.kde.krunner.pass.service     # DBus service registration
│   └── plasma-runner-pass.desktop       # KRunner plugin registration
├── install.sh                  # Installation script
└── README.md                   # This file
```

### DBus Interface

The plugin implements the standard KRunner DBus interface:

- **Service Name**: `org.kde.krunner.pass`
- **Object Path**: `/runner`
- **Interface**: `org.kde.krunner1`

Methods:
- `Match(query)` → Returns password matches
- `Run(match_id, action_id)` → Executes copy/type action
- `Actions(match_id)` → Returns available actions

## Development

### Setting Up Development Environment

1. **Clone and install in development mode:**
   ```bash
   git clone https://github.com/rakanalh/kde-krunner-pass.git
   cd kde-krunner-pass
   ./install.sh
   ```

2. **Make changes to the source files**

3. **Test your changes:**
   ```bash
   # Kill running service
   pkill -f kde-pass-runner.py
   
   # Run manually for testing
   ~/.local/bin/kde-pass-runner.py
   ```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Related Projects

- [pass](https://www.passwordstore.org/) - The standard Unix password manager
- [QtPass](https://qtpass.org/) - Cross-platform GUI for pass
- [browserpass](https://github.com/browserpass/browserpass-native) - Browser integration
- [passff](https://github.com/passff/passff) - Firefox extension

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/rakanalh/kde-krunner-pass/issues)
- **KDE Community**: [KDE Forums](https://forum.kde.org/)

## Acknowledgments

- The [pass](https://www.passwordstore.org/) project for creating an excellent password manager
- The KDE community for the excellent KRunner framework
- All contributors who help improve this project 
