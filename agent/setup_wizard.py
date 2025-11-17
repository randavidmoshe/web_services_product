#!/usr/bin/env python3
"""
Form Discoverer Agent - First Run Setup Wizard
Location: agent/setup_wizard.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import os
import json
import socket
from pathlib import Path
import uuid


class SetupWizard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Form Discoverer Agent - Setup")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Configuration
        self.config = {
            'api_url': '',
            'agent_token': '',
            'company_id': '',
            'user_id': '',
            'agent_id': f'agent-{uuid.uuid4().hex[:8]}',
            'browser': 'chrome',
            'headless': False,
            'screenshot_folder': str(Path.home() / 'FormDiscovererAgent' / 'screenshots'),
            'log_folder': str(Path.home() / 'FormDiscovererAgent' / 'logs'),
            'files_folder': str(Path.home() / 'FormDiscovererAgent' / 'files'),
        }
        
        self.current_step = 0
        self.steps = [
            self.step_welcome,
            self.step_api_discovery,
            self.step_login,
            self.step_configuration,
            self.step_complete
        ]
        
        # Main container
        self.container = ttk.Frame(self.root, padding="20")
        self.container.pack(fill=tk.BOTH, expand=True)
        
        # Navigation buttons
        self.nav_frame = ttk.Frame(self.root, padding="10")
        self.nav_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.btn_back = ttk.Button(self.nav_frame, text="Back", command=self.go_back, state=tk.DISABLED)
        self.btn_back.pack(side=tk.LEFT, padx=5)
        
        self.btn_next = ttk.Button(self.nav_frame, text="Next", command=self.go_next)
        self.btn_next.pack(side=tk.RIGHT, padx=5)
        
        # Show first step
        self.show_step()
    
    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()
    
    def show_step(self):
        self.clear_container()
        self.steps[self.current_step]()
        
        # Update navigation buttons
        self.btn_back.config(state=tk.NORMAL if self.current_step > 0 else tk.DISABLED)
        if self.current_step == len(self.steps) - 1:
            self.btn_next.config(text="Finish", command=self.finish_setup)
        else:
            self.btn_next.config(text="Next", command=self.go_next)
    
    def go_next(self):
        if self.validate_current_step():
            self.current_step += 1
            self.show_step()
    
    def go_back(self):
        self.current_step -= 1
        self.show_step()
    
    def validate_current_step(self):
        if self.current_step == 1:  # API Discovery
            if not self.config['api_url']:
                messagebox.showerror("Error", "Please enter or discover API URL")
                return False
        elif self.current_step == 2:  # Login
            if not self.config['agent_token']:
                messagebox.showerror("Error", "Please login first")
                return False
        return True
    
    # ========== STEP 1: WELCOME ==========
    
    def step_welcome(self):
        ttk.Label(
            self.container,
            text="Welcome to Form Discoverer Agent",
            font=('Arial', 16, 'bold')
        ).pack(pady=20)
        
        ttk.Label(
            self.container,
            text="This wizard will help you set up the agent to connect\nto your Form Discoverer server.",
            justify=tk.CENTER
        ).pack(pady=10)
        
        info_frame = ttk.LabelFrame(self.container, text="What happens next:", padding="15")
        info_frame.pack(pady=20, fill=tk.X)
        
        steps_text = """
1. Discover or enter your API server URL
2. Login with your credentials
3. Configure browser and folder settings
4. Start testing!
        """
        
        ttk.Label(info_frame, text=steps_text, justify=tk.LEFT).pack()
    
    # ========== STEP 2: API DISCOVERY ==========
    
    def step_api_discovery(self):
        ttk.Label(
            self.container,
            text="Discover API Server",
            font=('Arial', 14, 'bold')
        ).pack(pady=10)
        
        # Auto-discovery section
        discovery_frame = ttk.LabelFrame(self.container, text="Auto-Discovery", padding="15")
        discovery_frame.pack(pady=10, fill=tk.X)
        
        ttk.Label(discovery_frame, text="Searching for API server on local network...").pack()
        
        self.discovery_status = ttk.Label(discovery_frame, text="")
        self.discovery_status.pack(pady=5)
        
        ttk.Button(
            discovery_frame,
            text="🔍 Scan Network",
            command=self.scan_network
        ).pack(pady=5)
        
        # Manual entry section
        manual_frame = ttk.LabelFrame(self.container, text="Manual Configuration", padding="15")
        manual_frame.pack(pady=10, fill=tk.X)
        
        ttk.Label(manual_frame, text="API Server URL:").pack(anchor=tk.W)
        
        self.api_url_entry = ttk.Entry(manual_frame, width=50)
        self.api_url_entry.pack(fill=tk.X, pady=5)
        self.api_url_entry.insert(0, "http://localhost:8001")
        
        ttk.Button(
            manual_frame,
            text="Test Connection",
            command=self.test_connection
        ).pack(pady=5)
    
    def scan_network(self):
        self.discovery_status.config(text="Scanning...")
        self.root.update()
        
        # Try common ports
        found = False
        for port in [8001, 8000, 3000, 5000]:
            try:
                # Try localhost first
                response = requests.get(f"http://localhost:{port}/", timeout=1)
                if response.status_code == 200:
                    self.config['api_url'] = f"http://localhost:{port}"
                    self.api_url_entry.delete(0, tk.END)
                    self.api_url_entry.insert(0, self.config['api_url'])
                    self.discovery_status.config(
                        text=f"✅ Found API server at {self.config['api_url']}",
                        foreground="green"
                    )
                    found = True
                    break
            except:
                continue
        
        if not found:
            self.discovery_status.config(
                text="❌ No API server found. Please enter manually.",
                foreground="red"
            )
    
    def test_connection(self):
        url = self.api_url_entry.get().strip()
        try:
            response = requests.get(f"{url}/", timeout=5)
            if response.status_code == 200:
                self.config['api_url'] = url
                messagebox.showinfo("Success", "✅ Connection successful!")
            else:
                messagebox.showerror("Error", f"Server returned status {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")
    
    # ========== STEP 3: LOGIN ==========
    
    def step_login(self):
        ttk.Label(
            self.container,
            text="Login to Your Account",
            font=('Arial', 14, 'bold')
        ).pack(pady=10)
        
        login_frame = ttk.LabelFrame(self.container, text="Credentials", padding="15")
        login_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # Email
        ttk.Label(login_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.email_entry = ttk.Entry(login_frame, width=40)
        self.email_entry.grid(row=0, column=1, pady=5, padx=10)
        
        # Password
        ttk.Label(login_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(login_frame, width=40, show="*")
        self.password_entry.grid(row=1, column=1, pady=5, padx=10)
        
        # Login button
        ttk.Button(
            login_frame,
            text="Login",
            command=self.do_login
        ).grid(row=2, column=1, pady=15)
        
        # Status
        self.login_status = ttk.Label(login_frame, text="")
        self.login_status.grid(row=3, column=0, columnspan=2, pady=5)
    
    def do_login(self):
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not email or not password:
            messagebox.showerror("Error", "Please enter email and password")
            return
        
        try:
            response = requests.post(
                f"{self.config['api_url']}/api/auth/agent-login",
                json={'email': email, 'password': password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.config['agent_token'] = data.get('token')
                self.config['company_id'] = data.get('company_id')
                self.config['user_id'] = data.get('user_id')
                
                self.login_status.config(
                    text="✅ Login successful!",
                    foreground="green"
                )
                messagebox.showinfo("Success", "Login successful! Click Next to continue.")
            else:
                messagebox.showerror("Error", "Invalid credentials")
        except Exception as e:
            messagebox.showerror("Error", f"Login failed: {str(e)}")
    
    # ========== STEP 4: CONFIGURATION ==========
    
    def step_configuration(self):
        ttk.Label(
            self.container,
            text="Agent Configuration",
            font=('Arial', 14, 'bold')
        ).pack(pady=10)
        
        config_frame = ttk.LabelFrame(self.container, text="Settings", padding="15")
        config_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # Browser selection
        ttk.Label(config_frame, text="Default Browser:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.browser_var = tk.StringVar(value=self.config['browser'])
        browser_combo = ttk.Combobox(
            config_frame,
            textvariable=self.browser_var,
            values=['chrome', 'firefox', 'edge'],
            state='readonly',
            width=20
        )
        browser_combo.grid(row=0, column=1, pady=5, padx=10, sticky=tk.W)
        
        # Headless mode
        self.headless_var = tk.BooleanVar(value=self.config['headless'])
        ttk.Checkbutton(
            config_frame,
            text="Run in headless mode (no visible browser)",
            variable=self.headless_var
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Folders
        ttk.Label(config_frame, text="Screenshot Folder:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.screenshot_entry = ttk.Entry(config_frame, width=35)
        self.screenshot_entry.insert(0, self.config['screenshot_folder'])
        self.screenshot_entry.grid(row=2, column=1, pady=5, padx=10, sticky=tk.W)
        ttk.Button(config_frame, text="Browse...", command=lambda: self.browse_folder(self.screenshot_entry)).grid(row=2, column=2)
        
        ttk.Label(config_frame, text="Log Folder:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.log_entry = ttk.Entry(config_frame, width=35)
        self.log_entry.insert(0, self.config['log_folder'])
        self.log_entry.grid(row=3, column=1, pady=5, padx=10, sticky=tk.W)
        ttk.Button(config_frame, text="Browse...", command=lambda: self.browse_folder(self.log_entry)).grid(row=3, column=2)
        
        ttk.Label(config_frame, text="Files Folder:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.files_entry = ttk.Entry(config_frame, width=35)
        self.files_entry.insert(0, self.config['files_folder'])
        self.files_entry.grid(row=4, column=1, pady=5, padx=10, sticky=tk.W)
        ttk.Button(config_frame, text="Browse...", command=lambda: self.browse_folder(self.files_entry)).grid(row=4, column=2)
    
    def browse_folder(self, entry_widget):
        folder = filedialog.askdirectory()
        if folder:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, folder)
    
    # ========== STEP 5: COMPLETE ==========
    
    def step_complete(self):
        ttk.Label(
            self.container,
            text="Setup Complete!",
            font=('Arial', 16, 'bold'),
            foreground="green"
        ).pack(pady=20)
        
        ttk.Label(
            self.container,
            text="Your agent is ready to start testing.",
            font=('Arial', 12)
        ).pack(pady=10)
        
        summary_frame = ttk.LabelFrame(self.container, text="Configuration Summary", padding="15")
        summary_frame.pack(pady=20, fill=tk.BOTH, expand=True)
        
        summary_text = f"""
API Server: {self.config['api_url']}
Company ID: {self.config['company_id']}
User ID: {self.config['user_id']}
Agent ID: {self.config['agent_id']}

Browser: {self.config['browser']}
Headless: {'Yes' if self.config['headless'] else 'No'}

Screenshot Folder: {self.config['screenshot_folder']}
Log Folder: {self.config['log_folder']}
Files Folder: {self.config['files_folder']}
        """
        
        ttk.Label(summary_frame, text=summary_text, justify=tk.LEFT).pack()
    
    def finish_setup(self):
        # Update config with final values from UI
        self.config['browser'] = self.browser_var.get()
        self.config['headless'] = self.headless_var.get()
        self.config['screenshot_folder'] = self.screenshot_entry.get()
        self.config['log_folder'] = self.log_entry.get()
        self.config['files_folder'] = self.files_entry.get()
        
        # Save configuration
        self.save_config()
        
        # Close wizard
        messagebox.showinfo("Success", "Configuration saved! The agent will now start.")
        self.root.quit()
    
    def save_config(self):
        # Create .env file
        env_content = f"""# Form Discoverer Agent Configuration
API_URL={self.config['api_url']}
AGENT_TOKEN={self.config['agent_token']}
COMPANY_ID={self.config['company_id']}
USER_ID={self.config['user_id']}
AGENT_ID={self.config['agent_id']}

# Browser Settings
BROWSER={self.config['browser']}
HEADLESS={str(self.config['headless']).lower()}

# Folder Settings
SCREENSHOT_FOLDER={self.config['screenshot_folder']}
LOG_FOLDER={self.config['log_folder']}
FILES_FOLDER={self.config['files_folder']}
"""
        
        # Save to .env file
        with open('.env', 'w') as f:
            f.write(env_content)
        
        # Create folders
        for folder in [self.config['screenshot_folder'], self.config['log_folder'], self.config['files_folder']]:
            os.makedirs(folder, exist_ok=True)
        
        print("✅ Configuration saved to .env")
    
    def run(self):
        self.root.mainloop()


def main():
    wizard = SetupWizard()
    wizard.run()


if __name__ == "__main__":
    main()
