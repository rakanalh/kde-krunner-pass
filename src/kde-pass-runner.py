#!/usr/bin/env python3
"""
KDE Pass Runner - DBus service for KRunner integration with pass (passwordstore.org)

This service provides KRunner integration for the standard Unix password manager 'pass'.
It allows users to search and access their passwords directly from KRunner.
"""

import sys
import os
import subprocess
import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

# Import auto-typing functionality
def import_extended_interface():
    """Safely import the extended pass interface."""
    try:
        import importlib.util
        # Try to find the pass-interface.py file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        interface_path = os.path.join(script_dir, "pass-interface.py")
        
        print(f"Looking for pass-interface.py at: {interface_path}", file=sys.stderr)
        
        if not os.path.exists(interface_path):
            print(f"pass-interface.py not found at {interface_path}", file=sys.stderr)
            return None
            
        spec = importlib.util.spec_from_file_location("pass_interface", interface_path)
        if spec and spec.loader:
            pass_interface_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pass_interface_module)
            print("Successfully imported pass_interface module", file=sys.stderr)
            
            # Test the extended interface
            try:
                test_interface = pass_interface_module.ExtendedPassInterface()
                print(f"ExtendedPassInterface test - xdotool available: {test_interface.auto_typer.xdotool_available}", file=sys.stderr)
                return pass_interface_module.ExtendedPassInterface
            except Exception as e:
                print(f"Failed to create ExtendedPassInterface instance: {e}", file=sys.stderr)
                return None
        else:
            print("Failed to create module spec", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Failed to import extended interface: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None

ExtendedPassInterface = import_extended_interface()

# DBus interface for KRunner
KRUNNER_IFACE = "org.kde.krunner1"
SERVICE_NAME = "org.kde.krunner.pass"
OBJECT_PATH = "/runner"

class PasswordMatch:
    """Represents a password match result."""
    
    def __init__(self, path: str, name: str, category: str = "Passwords"):
        self.path = path
        self.name = name
        self.category = category
        self.relevance = 1.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to KRunner match format."""
        return {
            "id": self.path,
            "text": self.name,
            "icon": "dialog-password",
            "category": self.category,
            "relevance": self.relevance,
            "properties": {
                "multiline": False
            }
        }

class PassInterface:
    """Interface to the pass password manager."""
    
    def __init__(self):
        self.store_dir = Path.home() / ".password-store"
        
    def is_available(self) -> bool:
        """Check if pass is available and password store exists."""
        try:
            # Check if pass command exists
            subprocess.run(["pass", "--version"], 
                         capture_output=True, check=True, timeout=5)
            # Check if password store directory exists
            return self.store_dir.exists()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_password_list(self) -> List[str]:
        """Get list of all password entries."""
        if not self.is_available():
            return []
            
        passwords = []
        try:
            # Recursively find all .gpg files in password store
            for gpg_file in self.store_dir.rglob("*.gpg"):
                # Convert path to pass entry name
                rel_path = gpg_file.relative_to(self.store_dir)
                # Remove .gpg extension
                pass_name = str(rel_path)[:-4]
                passwords.append(pass_name)
        except Exception as e:
            print(f"Error reading password store: {e}", file=sys.stderr)
            
        return sorted(passwords)
    
    def copy_password(self, pass_name: str) -> bool:
        """Copy password to clipboard using pass -c."""
        try:
            subprocess.run(["pass", "-c", pass_name], 
                         check=True, timeout=10,
                         capture_output=True)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"Error copying password: {e}", file=sys.stderr)
            return False
    
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

class KDEPassRunner(dbus.service.Object):
    """KRunner DBus service for pass integration."""
    
    def __init__(self):
        self.bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(SERVICE_NAME, self.bus)
        super().__init__(bus_name, OBJECT_PATH)
        
        self.pass_interface = PassInterface()
        
        # Initialize extended functionality with detailed logging
        print(f"ExtendedPassInterface class available: {ExtendedPassInterface is not None}", file=sys.stderr)
        
        if ExtendedPassInterface:
            try:
                print("Creating ExtendedPassInterface instance...", file=sys.stderr)
                self.extended_interface = ExtendedPassInterface()
                print("Extended interface initialized successfully", file=sys.stderr)
                print(f"Extended interface xdotool available: {self.extended_interface.auto_typer.xdotool_available}", file=sys.stderr)
            except Exception as e:
                print(f"Failed to initialize extended interface: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                self.extended_interface = None
        else:
            print("ExtendedPassInterface class not available", file=sys.stderr)
            self.extended_interface = None
        
        self.password_cache = []
        self.cache_valid = False
        
        print("KDE Pass Runner service started", file=sys.stderr)
    
    def _refresh_cache(self):
        """Refresh the password cache."""
        if not self.cache_valid:
            self.password_cache = self.pass_interface.get_password_list()
            self.cache_valid = True
            print(f"Loaded {len(self.password_cache)} passwords", file=sys.stderr)
    
    def _fuzzy_match(self, query: str, password_name: str) -> float:
        """Calculate fuzzy match score."""
        query = query.lower()
        password_name = password_name.lower()
        
        # Exact match
        if query == password_name:
            return 1.0
        
        # Starts with query (highest priority)
        if password_name.startswith(query):
            return 0.95
        
        # Contains query as whole word
        if query in password_name:
            return 0.8
        
        # Check if query matches any part after slash (directory structure)
        password_parts = password_name.split('/')
        for part in password_parts:
            if part.startswith(query):
                return 0.75
            if query in part:
                return 0.7
        
        # Fuzzy matching - check if all characters of query appear in order
        query_chars = list(query)
        name_chars = list(password_name)
        
        query_idx = 0
        for char in name_chars:
            if query_idx < len(query_chars) and char == query_chars[query_idx]:
                query_idx += 1
        
        if query_idx == len(query_chars):
            # Score based on how compact the match is
            return 0.5 + (0.2 * (len(query) / len(password_name)))
        
        return 0.0
    
    @dbus.service.method(KRUNNER_IFACE, in_signature='s', out_signature='a(sssida{sv})')
    def Match(self, query: str):
        """Handle match requests from KRunner."""
        print(f"Match request: '{query}'", file=sys.stderr)
        
        # Check if pass is available
        if not self.pass_interface.is_available():
            print("Pass is not available", file=sys.stderr)
            return []
        
        query = query.strip()
        
        # Check if query starts with "pass" (case insensitive)
        query_lower = query.lower()
        if not query_lower.startswith("pass"):
            return []
        
        # Extract search term after "pass"
        if query_lower == "pass":
            search_term = ""
        elif query_lower.startswith("pass "):
            search_term = query[5:].strip()  # Remove "pass " prefix
        else:
            # Handle partial typing like "pass" being typed
            if len(query) == 4 and query_lower == "pass":
                search_term = ""
            elif len(query) > 4 and not query_lower.startswith("pass "):
                return []  # Don't match incomplete words
            else:
                search_term = ""
        
        self._refresh_cache()
        
        matches = []
        for password_name in self.password_cache:
            if search_term:
                relevance = self._fuzzy_match(search_term, password_name)
                if relevance == 0.0:
                    continue
            else:
                relevance = 1.0
            
            # Create match entry
            match_id = f"pass:{password_name}"
            text = f"🔑 {password_name}"
            icon = "dialog-password"
            category = "Passwords"
            properties = dbus.Dictionary({
                "subtext": dbus.String("Press Enter to copy, Ctrl+Enter to type"),
                "urls": dbus.Array([], signature="s")
            }, signature="sv")
            
            matches.append((
                dbus.String(match_id),
                dbus.String(text),
                dbus.String(icon),
                dbus.Int32(int(relevance * 100)),
                dbus.Double(relevance),
                properties
            ))
        
        # Sort by relevance (higher relevance first)
        matches.sort(key=lambda x: x[4], reverse=True)
        
        # Limit results to avoid overwhelming KRunner
        max_results = 15 if not search_term else 10
        matches = matches[:max_results]
        
        print(f"Returning {len(matches)} matches for search term: '{search_term}'", file=sys.stderr)
        return matches
    
    @dbus.service.method(KRUNNER_IFACE, in_signature='ss', out_signature='')
    def Run(self, match_id: str, action_id: str):
        """Handle run requests from KRunner."""
        print(f"Run request: '{match_id}', action: '{action_id}'", file=sys.stderr)
        
        if not match_id.startswith("pass:"):
            return
        
        password_name = match_id[5:]  # Remove "pass:" prefix
        
        if action_id == "type":
            # Auto-type password
            if not self.extended_interface:
                print("Auto-typing not available (extended interface not loaded)", file=sys.stderr)
                try:
                    subprocess.run([
                        "notify-send", 
                        "KDE Pass Runner", 
                        "Auto-typing not available. Check installation.",
                        "--icon=dialog-error",
                        "--expire-time=5000"
                    ], timeout=5)
                except:
                    pass
                return
                
            try:
                print(f"Attempting to auto-type password for '{password_name}'", file=sys.stderr)
                success = self.extended_interface.type_password(password_name)
                
                if success:
                    print(f"Auto-typed password for '{password_name}'", file=sys.stderr)
                    try:
                        subprocess.run([
                            "notify-send", 
                            "KDE Pass Runner", 
                            f"Password for '{password_name}' typed",
                            "--icon=input-keyboard",
                            "--expire-time=2000"
                        ], timeout=5)
                    except:
                        pass
                else:
                    print(f"Failed to auto-type password for '{password_name}'", file=sys.stderr)
                    try:
                        subprocess.run([
                            "notify-send", 
                            "KDE Pass Runner", 
                            f"Failed to type password for '{password_name}'. Check if xdotool is working.",
                            "--icon=dialog-error",
                            "--expire-time=5000"
                        ], timeout=5)
                    except:
                        pass
                        
            except Exception as e:
                print(f"Exception during auto-typing: {e}", file=sys.stderr)
                try:
                    subprocess.run([
                        "notify-send", 
                        "KDE Pass Runner", 
                        f"Auto-typing crashed: {str(e)}",
                        "--icon=dialog-error",
                        "--expire-time=5000"
                    ], timeout=5)
                except:
                    pass
        else:
            # Default action: copy to clipboard
            if self.pass_interface.copy_password(password_name):
                print(f"Copied password for '{password_name}' to clipboard", file=sys.stderr)
                # Send notification
                try:
                    subprocess.run([
                        "notify-send", 
                        "KDE Pass Runner", 
                        f"Password for '{password_name}' copied to clipboard",
                        "--icon=edit-copy",
                        "--expire-time=3000"
                    ], timeout=5)
                except:
                    pass
            else:
                print(f"Failed to copy password for '{password_name}'", file=sys.stderr)
    
    @dbus.service.method(KRUNNER_IFACE, in_signature='s', out_signature='a(sss)')
    def Actions(self, match_id: str):
        """Return available actions for a match."""
        print(f"Actions requested for match_id: '{match_id}'", file=sys.stderr)
        
        if not match_id.startswith("pass:"):
            print("Not a pass match, returning no actions", file=sys.stderr)
            return []
        
        actions = [
            (dbus.String("copy"), dbus.String("Copy Password"), dbus.String("edit-copy")),
        ]
        
        # Only add type action if auto-typing is available
        if self.extended_interface:
            actions.append((dbus.String("type"), dbus.String("Type Password"), dbus.String("input-keyboard")))
            print("Added type action (auto-typing available)", file=sys.stderr)
        else:
            print("Auto-typing not available, only copy action", file=sys.stderr)
        
        return actions

def main():
    """Main entry point."""
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            print("KDE Pass Runner - DBus service for KRunner integration with pass")
            print("Usage: kde-pass-runner.py")
            print("")
            print("This service provides KRunner integration for the standard Unix password manager 'pass'.")
            print("It should be started automatically by DBus when KRunner needs it.")
            print("")
            print("Features:")
            print("  - Search passwords by typing 'pass [search-term]' in KRunner")
            print("  - Copy passwords to clipboard (default action)")
            print("  - Auto-type passwords (requires xdotool)")
            print("")
            sys.exit(0)
        elif sys.argv[1] in ['--version', '-v']:
            print("KDE Pass Runner v1.0")
            sys.exit(0)
    
    if not os.getenv('DBUS_SESSION_BUS_ADDRESS'):
        print("No DBus session bus available", file=sys.stderr)
        sys.exit(1)
    
    # Initialize DBus
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    
    # Create the service
    try:
        service = KDEPassRunner()
        
        # Run the main loop
        loop = GLib.MainLoop()
        print("KDE Pass Runner service ready", file=sys.stderr)
        loop.run()
        
    except KeyboardInterrupt:
        print("Service interrupted", file=sys.stderr)
    except Exception as e:
        print(f"Service error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 