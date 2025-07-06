#!/usr/bin/env python3
"""
Pass Interface - Extended functionality for auto-typing passwords

This module provides auto-typing functionality using xdotool for X11 and wtype for Wayland.
"""

import subprocess
import sys
import time
import os
from typing import Optional, Tuple

class AutoTyper:
    """Handles auto-typing of passwords using xdotool (X11) or wtype (Wayland)."""
    
    def __init__(self):
        self.session_type, self.display_server = self._detect_display_server()
        self.xdotool_available = self._check_xdotool() if self.display_server == "x11" else False
        self.wtype_available, self.wtype_error = self._check_wtype() if self.display_server == "wayland" else (False, None)
        
        print(f"Display server: {self.display_server}", file=sys.stderr)
        print(f"Session type: {self.session_type}", file=sys.stderr)
        print(f"xdotool available: {self.xdotool_available}", file=sys.stderr)
        print(f"wtype available: {self.wtype_available}", file=sys.stderr)
        if self.wtype_error:
            print(f"wtype error: {self.wtype_error}", file=sys.stderr)
    
    def _detect_display_server(self) -> Tuple[str, str]:
        """
        Detect the current display server and session type.
        
        Returns:
            Tuple of (session_type, display_server)
            session_type: 'x11', 'wayland', or 'unknown'
            display_server: 'x11', 'wayland', or 'unknown'
        """
        # Check XDG_SESSION_TYPE first
        session_type = os.environ.get("XDG_SESSION_TYPE", "unknown").lower()
        
        # Check WAYLAND_DISPLAY
        if "WAYLAND_DISPLAY" in os.environ:
            display_server = "wayland"
        # Check DISPLAY for X11
        elif "DISPLAY" in os.environ:
            display_server = "x11"
        else:
            display_server = "unknown"
        
        return session_type, display_server
    
    def _check_xdotool(self) -> bool:
        """Check if xdotool is available."""
        try:
            result = subprocess.run(["xdotool", "--version"], 
                                  capture_output=True, check=True, timeout=5, text=True)
            print(f"xdotool version: {result.stdout.strip()}", file=sys.stderr)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"xdotool check failed: {e}", file=sys.stderr)
            return False
    
    def _check_wtype(self) -> Tuple[bool, Optional[str]]:
        """
        Check if wtype is available and working.
        
        Returns:
            Tuple of (is_available, error_message)
            is_available: True if wtype is available and working
            error_message: Error message if wtype is not working, None if working
        """
        try:
            # First check if wtype is installed
            if not os.path.exists("/usr/bin/wtype"):
                return False, "wtype is not installed"
            
            # Test wtype with a simple command
            result = subprocess.run(
                ["wtype", "-"],
                input="test",
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Check for virtual keyboard protocol error
            if "virtual keyboard protocol" in result.stderr.lower():
                return False, """Wayland virtual keyboard protocol not supported.
To enable it in KDE Plasma:
1. Edit/create ~/.config/kwinrc
2. Add under [Wayland]:
   VirtualKeyboardEnabled=true
3. Restart your Wayland session"""
            
            # wtype returns non-zero when run without args, which is fine
            print("wtype is available and working", file=sys.stderr)
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "wtype command timed out"
        except FileNotFoundError:
            return False, "wtype is not installed"
        except Exception as e:
            return False, str(e)
    
    def test_typing(self) -> bool:
        """Test if typing is available with current setup."""
        if self.display_server == "x11" and self.xdotool_available:
            return self._test_xdotool()
        elif self.display_server == "wayland":
            if not self.wtype_available:
                print(f"wtype is not available: {self.wtype_error}", file=sys.stderr)
            return self.wtype_available
        return False
    
    def _test_xdotool(self) -> bool:
        """Test if xdotool can actually type (safe test)."""
        try:
            # Test with a harmless command
            subprocess.run([
                "xdotool", "getactivewindow"
            ], check=True, timeout=5, capture_output=True)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"xdotool test failed: {e}", file=sys.stderr)
            return False
    
    def type_password(self, password: str, delay: float = 0.1) -> bool:
        """
        Type password using appropriate tool for the current display server.
        
        Args:
            password: The password to type
            delay: Delay before typing (to allow window focus)
            
        Returns:
            True if successful, False otherwise
        """
        if not password:
            print("No password provided for auto-typing", file=sys.stderr)
            return False
        
        # Check if we have a supported typing method
        if self.display_server == "x11" and not self.xdotool_available:
            print("xdotool is not available for auto-typing on X11", file=sys.stderr)
            return False
        elif self.display_server == "wayland":
            if not self.wtype_available:
                print(f"Auto-typing not available on Wayland: {self.wtype_error}", file=sys.stderr)
                return False
        elif self.display_server == "unknown":
            print("Unknown display server, cannot auto-type", file=sys.stderr)
            return False
        
        try:
            # Small delay to allow user to focus the target window
            print(f"Waiting {delay}s for window focus...", file=sys.stderr)
            time.sleep(delay)
            
            if self.display_server == "x11":
                return self._type_with_xdotool(password)
            elif self.display_server == "wayland":
                return self._type_with_wtype(password)
            
            return False
            
        except Exception as e:
            print(f"Unexpected error during auto-typing: {e}", file=sys.stderr)
            return False
    
    def _type_with_xdotool(self, password: str) -> bool:
        """Type password using xdotool (X11)."""
        try:
            # Get active window for debugging
            window_info = self.get_window_info()
            print(f"Typing into window: {window_info}", file=sys.stderr)
            
            # Use xdotool to type the password
            result = subprocess.run([
                "xdotool", "type", "--delay", "50", "--clearmodifiers", password
            ], check=True, timeout=10, capture_output=True, text=True)
            
            print("Auto-typing completed successfully with xdotool", file=sys.stderr)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"xdotool command failed: {e}", file=sys.stderr)
            if e.stderr:
                print(f"xdotool stderr: {e.stderr}", file=sys.stderr)
            return False
        except subprocess.TimeoutExpired as e:
            print(f"xdotool command timed out: {e}", file=sys.stderr)
            return False
    
    def _type_with_wtype(self, password: str) -> bool:
        """Type password using wtype (Wayland)."""
        try:
            # wtype is simpler than xdotool, just pipe the password to it
            process = subprocess.Popen(
                ["wtype", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send password to wtype's stdin
            stdout, stderr = process.communicate(input=password, timeout=10)
            
            if process.returncode == 0:
                print("Auto-typing completed successfully with wtype", file=sys.stderr)
                return True
            else:
                print(f"wtype failed with return code {process.returncode}", file=sys.stderr)
                if stderr:
                    print(f"wtype stderr: {stderr}", file=sys.stderr)
                if "virtual keyboard protocol" in stderr.lower():
                    print("""
To enable virtual keyboard support in KDE Plasma:
1. Edit/create ~/.config/kwinrc
2. Add under [Wayland]:
   VirtualKeyboardEnabled=true
3. Restart your Wayland session""", file=sys.stderr)
                return False
            
        except subprocess.TimeoutExpired as e:
            print(f"wtype command timed out: {e}", file=sys.stderr)
            return False
    
    def get_window_info(self) -> Optional[str]:
        """Get current window information for debugging (X11 only)."""
        if self.display_server != "x11" or not self.xdotool_available:
            return None
        
        try:
            result = subprocess.run([
                "xdotool", "getactivewindow", "getwindowname"
            ], capture_output=True, check=True, timeout=5, text=True)
            
            return result.stdout.strip()
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

class ExtendedPassInterface:
    """Extended pass interface with auto-typing capabilities."""
    
    def __init__(self):
        self.auto_typer = AutoTyper()
    
    def get_password(self, pass_name: str) -> Optional[str]:
        """Get password content (first line only)."""
        try:
            result = subprocess.run(["pass", "show", pass_name], 
                                  capture_output=True, check=True, 
                                  timeout=10, text=True)
            # Return only the first line (the password)
            return result.stdout.split('\n')[0]
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"Error getting password: {e}", file=sys.stderr)
            return None
    
    def type_password(self, pass_name: str) -> bool:
        """
        Auto-type password for the given pass entry.
        
        Args:
            pass_name: Name of the pass entry
            
        Returns:
            True if successful, False otherwise
        """
        # Test typing before attempting to get password
        if not self.auto_typer.test_typing():
            print("Typing test failed, cannot auto-type", file=sys.stderr)
            return False
        
        password = self.get_password(pass_name)
        if not password:
            print(f"Could not retrieve password for '{pass_name}'", file=sys.stderr)
            return False
        
        if self.auto_typer.display_server == "x11":
            window_name = self.auto_typer.get_window_info()
            print(f"Auto-typing password for '{pass_name}' in window: {window_name}", file=sys.stderr)
        else:
            print(f"Auto-typing password for '{pass_name}'", file=sys.stderr)
        
        return self.auto_typer.type_password(password)

def main():
    """Test the auto-typing functionality."""
    if len(sys.argv) != 2:
        print("Usage: pass-interface.py <pass-entry-name>", file=sys.stderr)
        sys.exit(1)
    
    pass_name = sys.argv[1]
    interface = ExtendedPassInterface()
    
    if interface.type_password(pass_name):
        print(f"Successfully typed password for '{pass_name}'")
    else:
        print(f"Failed to type password for '{pass_name}'")
        sys.exit(1)

if __name__ == "__main__":
    main() 