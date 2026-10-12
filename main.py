import cmd
import getpass
import secrets
import string
import threading
import pyperclip
import shutil
import gc
from vault import Vault

VAULT_PATH = "my_vault.enc"
CLIPBOARD_TIMEOUT = 15  # seconds

def generate_password(length=16):
    """Generates a cryptographically secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def copy_to_clipboard(text: str):
    """Copies text to clipboard and clears it after a timeout."""
    pyperclip.copy(text)
    print(f"[*] Password copied to clipboard. Will clear in {CLIPBOARD_TIMEOUT} seconds.")
    
    def clear_clipboard():
        if pyperclip.paste() == text:
            pyperclip.copy('')
            
    threading.Timer(CLIPBOARD_TIMEOUT, clear_clipboard).start()

class PasswordManagerCLI(cmd.Cmd):
    intro = "Welcome to PyManager. Type 'help' or '?' to list commands.\n"
    prompt = "(locked) > "

    def __init__(self):
        super().__init__()
        self.vault = Vault(VAULT_PATH)
        self.unlocked = False

    def precmd(self, line):
        # Force unlocking for most commands
        unprotected_commands = ['unlock', 'init', 'quit', 'EOF', 'help']
        command = line.split()[0] if line else ''
        if not self.unlocked and command not in unprotected_commands:
            print("[!] Vault is locked. Please 'unlock' or 'init' first.")
            return ''
        return line

    def do_init(self, arg):
        """Initialize a new password vault."""
        if self.vault.is_initialized():
            print("[!] Vault already exists. Use 'unlock' instead.")
            return
        
        pwd = getpass.getpass("Enter new master password: ")
        pwd2 = getpass.getpass("Confirm master password: ")
        if pwd != pwd2:
            print("[!] Passwords do not match.")
            return
        
        self.vault.initialize(pwd)
        self.unlocked = True
        self.prompt = "(unlocked) > "
        print("[*] Vault initialized and unlocked.")

    def do_unlock(self, arg):
        """Unlock an existing password vault."""
        if not self.vault.is_initialized():
            print("[!] No vault found. Use 'init' first.")
            return
            
        pwd = getpass.getpass("Master password: ")
        try:
            self.vault.unlock(pwd)
            self.unlocked = True
            self.prompt = "(unlocked) > "
            print("[*] Vault unlocked successfully.")
        except ValueError as e:
            print(f"[!] Error: {e}")

    def do_add(self, arg):
        """Add a new entry. (Prompts for details)"""
        site = input("Site/Service: ")
        username = input("Username: ")
        
        gen_choice = input("Generate a strong password? (y/n): ").strip().lower()
        if gen_choice == 'y':
            length = input("Length [16]: ").strip()
            length = int(length) if length.isdigit() else 16
            pwd = generate_password(length)
            print(f"[*] Generated password: {pwd}")
        else:
            pwd = getpass.getpass("Password (hidden): ")
            
        notes = input("Notes (optional): ")
        
        self.vault.add_entry(site, username, pwd, notes)
        print("[*] Entry added.")

    def do_list(self, arg):
        """List all stored entries."""
        if not self.vault.entries:
            print("Vault is empty.")
            return
            
        print("\nID | Site | Username")
        print("-" * 30)
        for eid, data in self.vault.entries.items():
            # Print the first 8 chars of the UUID for cleaner UI
            print(f"{eid[:8]} | {data['site']} | {data['username']}")
        print()

    def do_search(self, arg):
        """Search entries by site name. Usage: search <query>"""
        if not arg:
            print("Usage: search <query>")
            return
            
        results = [(eid, data) for eid, data in self.vault.entries.items() if arg.lower() in data['site'].lower()]
        if not results:
            print("No matches found.")
            return
            
        for eid, data in results:
            print(f"{eid[:8]} | {data['site']} | {data['username']}")

    def do_copy(self, arg):
        """Copy a password to the clipboard by ID. Usage: copy <id>"""
        if not arg:
            print("Usage: copy <id> (first 8 chars is fine)")
            return
            
        for eid, data in self.vault.entries.items():
            if eid.startswith(arg):
                copy_to_clipboard(data['password'])
                return
        print("[!] ID not found.")

    def do_show(self, arg):
        """Show full details of an entry. Usage: show <id>"""
        if not arg:
            print("Usage: show <id>")
            return
            
        for eid, data in self.vault.entries.items():
            if eid.startswith(arg):
                print(f"\nSite:     {data['site']}")
                print(f"Username: {data['username']}")
                print(f"Password: {data['password']}")
                print(f"Notes:    {data['notes']}\n")
                return
        print("[!] ID not found.")

    def do_delete(self, arg):
        """Delete an entry. Usage: delete <id>"""
        if not arg:
            print("Usage: delete <id>")
            return
            
        for eid in list(self.vault.entries.keys()):
            if eid.startswith(arg):
                self.vault.delete_entry(eid)
                print("[*] Entry deleted.")
                return
        print("[!] ID not found.")

    def do_passwd(self, arg):
        """Change the master password."""
        pwd = getpass.getpass("Enter NEW master password: ")
        pwd2 = getpass.getpass("Confirm NEW master password: ")
        if pwd != pwd2:
            print("[!] Passwords do not match.")
            return
            
        self.vault.change_password(pwd)
        print("[*] Master password updated successfully.")

    def do_export(self, arg):
        """Export the encrypted vault backup. Usage: export <path>"""
        if not arg:
            print("Usage: export <path>")
            return
        try:
            shutil.copy2(VAULT_PATH, arg)
            print(f"[*] Encrypted vault exported to {arg}")
        except Exception as e:
            print(f"[!] Export failed: {e}")

    def do_import(self, arg):
        """Import an encrypted vault backup. Usage: import <path>"""
        if not arg:
            print("Usage: import <path>")
            return
        try:
            shutil.copy2(arg, VAULT_PATH)
            print(f"[*] Vault imported from {arg}. Please 'unlock' to access.")
            self.do_lock('')
        except Exception as e:
            print(f"[!] Import failed: {e}")

    def do_lock(self, arg):
        """Lock the vault and clear memory."""
        self.vault.lock()
        self.unlocked = False
        self.prompt = "(locked) > "
        # Force garbage collection to clear dangling references to passwords
        gc.collect()
        print("[*] Vault locked.")

    def do_quit(self, arg):
        """Lock the vault and exit."""
        if self.unlocked:
            self.do_lock('')
        print("Goodbye.")
        return True
        
    def do_EOF(self, arg):
        return self.do_quit(arg)

if __name__ == '__main__':
    try:
        PasswordManagerCLI().cmdloop()
    except KeyboardInterrupt:
        print("\nExiting securely...")
        gc.collect()