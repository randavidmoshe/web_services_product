#!/usr/bin/env python3
"""
Form Discoverer Agent - Settings Panel
Location: agent/settings_panel.py

Run this to change agent settings after initial setup
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from pathlib import Path
from dotenv import load_dotenv, set_key


class SettingsPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Form Discoverer Agent - Settings")
        self.root.geometry("700x600")
        
        # Load current settings
        load_dotenv()
        self.settings = {
            'api_url': os.getenv('API_URL', ''),
            'agent_id': os.getenv('AGENT_ID', ''),
            'company_id': os.getenv('COMPANY_ID', ''),
            'user_id': os.getenv('USER_ID', ''),
            'browser': os.getenv('BROWSER', 'chrome'),
            'headless': os.getenv('HEADLESS', 'false') == 'true',
            'screenshot_folder': os.getenv('SCREENSHOT_FOLDER', ''),
            'log_folder': os.getenv('LOG_FOLDER', ''),
            'files_folder': os.getenv('FILES_FOLDER', ''),
        }
        
        # Create UI
        self.create_ui()
    
    def create_ui(self):
        # Title
        title_frame = ttk.Frame(self.root, padding="20")
        title_frame.pack(fill=tk.X)
        
        ttk.Label(
            title_frame,
            text="Agent Settings",
            font=('Arial', 16, 'bold')
        ).pack()
        
        # Notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Connection Tab
        connection_frame = ttk.Frame(notebook, padding="15")
        notebook.add(connection_frame, text="Connection")
        self.create_connection_tab(connection_frame)
        
        # Browser Tab
        browser_frame = ttk.Frame(notebook, padding="15")
        notebook.add(browser_frame, text="Browser")
        self.create_browser_tab(browser_frame)
        
        # Folders Tab
        folders_frame = ttk.Frame(notebook, padding="15")
        notebook.add(folders_frame, text="Folders")
        self.create_folders_tab(folders_frame)
        
        # Advanced Tab
        advanced_frame = ttk.Frame(notebook, padding="15")
        notebook.add(advanced_frame, text="Advanced")
        self.create_advanced_tab(advanced_frame)
        
        # Buttons
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="Save",
            command=self.save_settings
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.root.quit
        ).pack(side=tk.RIGHT, padx=5)
    
    def create_connection_tab(self, parent):
        # API URL
        ttk.Label(parent, text="API Server URL:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=10)
        self.api_url_entry = ttk.Entry(parent, width=50)
        self.api_url_entry.insert(0, self.settings['api_url'])
        self.api_url_entry.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Agent ID
        ttk.Label(parent, text="Agent ID:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=10)
        self.agent_id_label = ttk.Label(parent, text=self.settings['agent_id'], foreground='gray')
        self.agent_id_label.grid(row=3, column=0, sticky=tk.W)
        
        # Company/User IDs
        ttk.Label(parent, text="Company ID:", font=('Arial', 10, 'bold')).grid(row=4, column=0, sticky=tk.W, pady=10)
        self.company_id_label = ttk.Label(parent, text=self.settings['company_id'], foreground='gray')
        self.company_id_label.grid(row=5, column=0, sticky=tk.W)
        
        ttk.Label(parent, text="User ID:", font=('Arial', 10, 'bold')).grid(row=6, column=0, sticky=tk.W, pady=10)
        self.user_id_label = ttk.Label(parent, text=self.settings['user_id'], foreground='gray')
        self.user_id_label.grid(row=7, column=0, sticky=tk.W)
        
        # Test connection button
        ttk.Button(
            parent,
            text="Test Connection",
            command=self.test_connection
        ).grid(row=8, column=0, pady=20, sticky=tk.W)
    
    def create_browser_tab(self, parent):
        # Browser selection
        ttk.Label(parent, text="Default Browser:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=10)
        
        self.browser_var = tk.StringVar(value=self.settings['browser'])
        browsers = ['chrome', 'firefox', 'edge']
        
        for i, browser in enumerate(browsers):
            ttk.Radiobutton(
                parent,
                text=browser.capitalize(),
                variable=self.browser_var,
                value=browser
            ).grid(row=i+1, column=0, sticky=tk.W, padx=20, pady=5)
        
        # Headless mode
        self.headless_var = tk.BooleanVar(value=self.settings['headless'])
        ttk.Checkbutton(
            parent,
            text="Run in headless mode (no visible browser window)",
            variable=self.headless_var
        ).grid(row=5, column=0, sticky=tk.W, pady=20)
        
        ttk.Label(
            parent,
            text="Note: Headless mode is faster but you won't see the browser.",
            foreground='gray',
            wraplength=500
        ).grid(row=6, column=0, sticky=tk.W, pady=5)
    
    def create_folders_tab(self, parent):
        folders = [
            ('Screenshots:', 'screenshot_folder', 0),
            ('Logs:', 'log_folder', 3),
            ('Files:', 'files_folder', 6)
        ]
        
        self.folder_entries = {}
        
        for label, key, row in folders:
            ttk.Label(parent, text=label, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=10)
            
            entry = ttk.Entry(parent, width=50)
            entry.insert(0, self.settings[key])
            entry.grid(row=row+1, column=0, sticky=tk.W, pady=5)
            
            ttk.Button(
                parent,
                text="Browse...",
                command=lambda e=entry: self.browse_folder(e)
            ).grid(row=row+1, column=1, padx=10)
            
            self.folder_entries[key] = entry
    
    def create_advanced_tab(self, parent):
        ttk.Label(
            parent,
            text="Advanced Settings",
            font=('Arial', 12, 'bold')
        ).pack(pady=10)
        
        # Auto-start option
        self.autostart_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            parent,
            text="Start agent automatically when computer starts",
            variable=self.autostart_var
        ).pack(anchor=tk.W, pady=10)
        
        # Test selection
        test_frame = ttk.LabelFrame(parent, text="Default Tests", padding="10")
        test_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(
            test_frame,
            text="Select which tests to run by default:",
            wraplength=500
        ).pack(anchor=tk.W, pady=5)
        
        # Placeholder for test list (would be populated from API)
        self.test_vars = {}
        for test_name in ["Form Discovery", "Link Testing", "Navigation Testing"]:
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                test_frame,
                text=test_name,
                variable=var
            ).pack(anchor=tk.W, padx=20, pady=2)
            self.test_vars[test_name] = var
        
        # Reset button
        ttk.Button(
            parent,
            text="Reset to Defaults",
            command=self.reset_to_defaults
        ).pack(pady=20)
    
    def browse_folder(self, entry_widget):
        folder = filedialog.askdirectory()
        if folder:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, folder)
    
    def test_connection(self):
        import requests
        url = self.api_url_entry.get().strip()
        try:
            response = requests.get(f"{url}/", timeout=5)
            if response.status_code == 200:
                messagebox.showinfo("Success", "✅ Connection successful!")
            else:
                messagebox.showerror("Error", f"Server returned status {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")
    
    def reset_to_defaults(self):
        if messagebox.askyesno("Confirm", "Reset all settings to defaults?"):
            # Reset to default values
            self.browser_var.set('chrome')
            self.headless_var.set(False)
            # ... reset other fields
            messagebox.showinfo("Success", "Settings reset to defaults")
    
    def save_settings(self):
        try:
            # Update settings
            env_file = Path('.env')
            
            set_key(env_file, 'API_URL', self.api_url_entry.get())
            set_key(env_file, 'BROWSER', self.browser_var.get())
            set_key(env_file, 'HEADLESS', str(self.headless_var.get()).lower())
            
            for key, entry in self.folder_entries.items():
                set_key(env_file, key.upper(), entry.get())
                # Create folders if they don't exist
                os.makedirs(entry.get(), exist_ok=True)
            
            messagebox.showinfo("Success", "✅ Settings saved! Restart agent for changes to take effect.")
            self.root.quit()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def run(self):
        self.root.mainloop()


def main():
    panel = SettingsPanel()
    panel.run()


if __name__ == "__main__":
    main()
