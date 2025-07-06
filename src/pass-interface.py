#!/usr/bin/env python3
"""
Pass Interface - Extended functionality for auto-typing passwords

This module provides auto-typing functionality using xdotool for the KDE Pass Runner.
"""

import subprocess
import sys
import time
from typing import Optional

class AutoTyper:
    """Handles auto-typing of passwords using xdotool."""
    
    def __init__(self):
        self.xdotool_available = self._check_xdotool()
    
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
    
    def test_xdotool(self) -> bool:
        """Test if xdotool can actually type (safe test)."""
        if not self.xdotool_available:
            return False
        
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
        Type password using xdotool.
        
        Args:
            password: The password to type
            delay: Delay before typing (to allow window focus)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.xdotool_available:
            print("xdotool is not available for auto-typing", file=sys.stderr)
            return False
        
        if not password:
            print("No password provided for auto-typing", file=sys.stderr)
            return False
        
        try:
            # Small delay to allow user to focus the target window
            print(f"Waiting {delay}s for window focus...", file=sys.stderr)
            time.sleep(delay)
            
            # Get active window for debugging
            window_info = self.get_window_info()
            print(f"Typing into window: {window_info}", file=sys.stderr)
            
            # Use xdotool to type the password
            result = subprocess.run([
                "xdotool", "type", "--delay", "50", "--clearmodifiers", password
            ], check=True, timeout=10, capture_output=True, text=True)
            
            print("Auto-typing completed successfully", file=sys.stderr)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"xdotool command failed: {e}", file=sys.stderr)
            if e.stderr:
                print(f"xdotool stderr: {e.stderr}", file=sys.stderr)
            return False
        except subprocess.TimeoutExpired as e:
            print(f"xdotool command timed out: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Unexpected error during auto-typing: {e}", file=sys.stderr)
            return False
    
    def get_window_info(self) -> Optional[str]:
        """Get current window information for debugging."""
        if not self.xdotool_available:
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
        # Test xdotool before attempting to get password
        if not self.auto_typer.test_xdotool():
            print("xdotool test failed, cannot auto-type", file=sys.stderr)
            return False
        
        password = self.get_password(pass_name)
        if not password:
            print(f"Could not retrieve password for '{pass_name}'", file=sys.stderr)
            return False
        
        window_name = self.auto_typer.get_window_info()
        print(f"Auto-typing password for '{pass_name}' in window: {window_name}", file=sys.stderr)
        
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