#!/bin/bash
set -e

# KDE Pass Runner Installation Script
# This script installs the KDE Pass Runner plugin for KRunner integration with pass

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_PREFIX="${INSTALL_PREFIX:-$HOME/.local}"

echo "🔑 KDE Pass Runner Installation"
echo "==============================="

# Check dependencies
echo "Checking dependencies..."

# Check if pass is installed
if ! command -v pass &> /dev/null; then
    echo "❌ Error: 'pass' (password-store) is not installed"
    echo "   Please install it using your package manager:"
    echo "   - Debian/Ubuntu: sudo apt install pass"
    echo "   - Fedora: sudo dnf install pass"
    echo "   - Arch: sudo pacman -S pass"
    exit 1
fi

# Check if pass is initialized
if [ ! -d "$HOME/.password-store" ]; then
    echo "❌ Error: Pass is not initialized"
    echo "   Please initialize pass first:"
    echo "   pass init your-gpg-key-id"
    exit 1
fi

# Check Python dependencies
echo "Checking Python dependencies..."
if ! python3 -c "import dbus" 2>/dev/null; then
    echo "❌ Error: python3-dbus is not installed"
    echo "   Please install it using your package manager:"
    echo "   - Debian/Ubuntu: sudo apt install python3-dbus"
    echo "   - Fedora: sudo dnf install python3-dbus"
    echo "   - Arch: sudo pacman -S python-dbus"
    exit 1
fi

if ! python3 -c "from gi.repository import GLib" 2>/dev/null; then
    echo "❌ Error: python3-gi is not installed"
    echo "   Please install it using your package manager:"
    echo "   - Debian/Ubuntu: sudo apt install python3-gi"
    echo "   - Fedora: sudo dnf install python3-gobject"
    echo "   - Arch: sudo pacman -S python-gobject"
    exit 1
fi

# Check optional dependencies
if ! command -v xdotool &> /dev/null; then
    echo "⚠️  Warning: 'xdotool' is not installed (auto-typing will not work)"
    echo "   Install it for auto-typing functionality:"
    echo "   - Debian/Ubuntu: sudo apt install xdotool"
    echo "   - Fedora: sudo dnf install xdotool"
    echo "   - Arch: sudo pacman -S xdotool"
fi

if ! command -v notify-send &> /dev/null; then
    echo "⚠️  Warning: 'notify-send' is not installed (notifications will not work)"
    echo "   Install libnotify for notifications:"
    echo "   - Debian/Ubuntu: sudo apt install libnotify-bin"
    echo "   - Fedora: sudo dnf install libnotify"
    echo "   - Arch: sudo pacman -S libnotify"
fi

echo "✅ Dependencies check completed"

# Create directories
echo "Creating installation directories..."
mkdir -p "$INSTALL_PREFIX/bin"
mkdir -p "$INSTALL_PREFIX/share/dbus-1/services"
mkdir -p "$INSTALL_PREFIX/share/krunner/dbusplugins"

# Install Python scripts
echo "Installing KDE Pass Runner scripts..."
cp "$SCRIPT_DIR/src/kde-pass-runner.py" "$INSTALL_PREFIX/bin/"
cp "$SCRIPT_DIR/src/pass-interface.py" "$INSTALL_PREFIX/bin/"
chmod +x "$INSTALL_PREFIX/bin/kde-pass-runner.py"
chmod +x "$INSTALL_PREFIX/bin/pass-interface.py"

# Update service file with correct path
echo "Installing service files..."
sed "s|/usr/bin/kde-pass-runner.py|$INSTALL_PREFIX/bin/kde-pass-runner.py|" \
    "$SCRIPT_DIR/services/org.kde.krunner.pass.service" > \
    "$INSTALL_PREFIX/share/dbus-1/services/org.kde.krunner.pass.service"

cp "$SCRIPT_DIR/services/plasma-runner-pass.desktop" \
   "$INSTALL_PREFIX/share/krunner/dbusplugins/"

# Reload services
echo "Reloading services..."
if command -v kbuildsycoca5 &> /dev/null; then
    kbuildsycoca5
elif command -v kbuildsycoca6 &> /dev/null; then
    kbuildsycoca6
fi

# Restart krunner
echo "Restarting KRunner..."
if pgrep -x krunner > /dev/null; then
    kquitapp5 krunner 2>/dev/null || kquitapp6 krunner 2>/dev/null || true
    sleep 2
fi

# Start krunner
if command -v krunner &> /dev/null; then
    krunner &
    disown
fi

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "Usage:"
echo "  1. Press Alt+F2 or Alt+Space to open KRunner"
echo "  2. Type 'pass' to see all passwords"
echo "  3. Type 'pass search-term' to filter passwords"
echo "  4. Press Enter to copy password to clipboard"
echo "  5. Press Ctrl+Enter to auto-type password (requires xdotool)"
echo ""
echo "To uninstall:"
echo "  rm '$INSTALL_PREFIX/bin/kde-pass-runner.py'"
echo "  rm '$INSTALL_PREFIX/bin/pass-interface.py'"
echo "  rm '$INSTALL_PREFIX/share/dbus-1/services/org.kde.krunner.pass.service'"
echo "  rm '$INSTALL_PREFIX/share/krunner/dbusplugins/plasma-runner-pass.desktop'"
echo ""

# Test the installation
echo "Testing installation..."
if python3 "$INSTALL_PREFIX/bin/kde-pass-runner.py" --help 2>/dev/null; then
    echo "✅ Installation test successful"
else
    echo "❌ Installation test failed - check error messages above"
fi 