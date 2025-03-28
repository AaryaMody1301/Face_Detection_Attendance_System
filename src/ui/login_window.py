"""
Login screen for the Face Detection Attendance System
"""
import os
import logging
import threading
import tkinter as tk
from tkinter import messagebox, StringVar
import customtkinter as ctk
from PIL import Image, ImageTk

from .modern_app import ModernAttendanceApp
from ..auth.auth_system import AuthenticationSystem
from ..utils.credentials_manager import CredentialsManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set appearance mode and default color theme
ctk.set_appearance_mode("System")  # Options: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"

class LoginWindow(ctk.CTk):
    """
    Login window for user authentication
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize authentication system
        self.auth_system = AuthenticationSystem()
        
        # Initialize credentials manager
        self.credentials_manager = CredentialsManager()
        
        # Configure window
        self.title("Face Detection Attendance System - Login")
        self.geometry("800x500")
        self.resizable(True, True)
        
        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create a 2x1 grid layout
        self.main_frame.columnconfigure(0, weight=4)  # Left panel (image)
        self.main_frame.columnconfigure(1, weight=6)  # Right panel (login form)
        self.main_frame.rowconfigure(0, weight=1)
        
        # Create left panel (image)
        self.left_panel = ctk.CTkFrame(self.main_frame, corner_radius=15)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Load and display logo/illustration
        self.logo_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets/login_illustration.png")
        if os.path.exists(self.logo_path):
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(self.logo_path),
                dark_image=Image.open(self.logo_path),
                size=(350, 350)
            )
            self.logo_label = ctk.CTkLabel(
                self.left_panel,
                image=self.logo_image,
                text=""
            )
            self.logo_label.pack(fill="both", expand=True, padx=20, pady=20)
        else:
            # Display text if image not found
            self.logo_label = ctk.CTkLabel(
                self.left_panel,
                text="Face Detection\nAttendance System",
                font=ctk.CTkFont(size=30, weight="bold")
            )
            self.logo_label.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create right panel (login form)
        self.right_panel = ctk.CTkFrame(self.main_frame, corner_radius=15)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Configure right panel (3 rows)
        self.right_panel.rowconfigure(0, weight=2)  # Header
        self.right_panel.rowconfigure(1, weight=6)  # Login form
        self.right_panel.rowconfigure(2, weight=2)  # Footer
        self.right_panel.columnconfigure(0, weight=1)
        
        # Header section
        self.header_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        
        self.header_label = ctk.CTkLabel(
            self.header_frame,
            text="Welcome Back",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.header_label.pack(pady=10)
        
        self.subheader_label = ctk.CTkLabel(
            self.header_frame,
            text="Sign in to continue",
            font=ctk.CTkFont(size=14)
        )
        self.subheader_label.pack()
        
        # Login form section
        self.form_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.form_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        # Username field
        self.username_label = ctk.CTkLabel(
            self.form_frame,
            text="Username",
            font=ctk.CTkFont(size=14)
        )
        self.username_label.pack(anchor="w", pady=(10, 5))
        
        self.username_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="Enter your username",
            width=300,
            height=40,
            border_width=1,
            corner_radius=8
        )
        self.username_entry.pack(pady=(0, 15))
        
        # Password field
        self.password_label = ctk.CTkLabel(
            self.form_frame,
            text="Password",
            font=ctk.CTkFont(size=14)
        )
        self.password_label.pack(anchor="w", pady=(10, 5))
        
        self.password_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="Enter your password",
            width=300,
            height=40,
            border_width=1,
            corner_radius=8,
            show="•"
        )
        self.password_entry.pack(pady=(0, 15))
        
        # Remember me checkbox
        self.remember_var = ctk.BooleanVar(value=False)
        self.remember_checkbox = ctk.CTkCheckBox(
            self.form_frame,
            text="Remember me",
            variable=self.remember_var,
            checkbox_width=20,
            checkbox_height=20
        )
        self.remember_checkbox.pack(anchor="w", pady=10)
        
        # Login button
        self.login_button = ctk.CTkButton(
            self.form_frame,
            text="Sign In",
            width=300,
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.login
        )
        self.login_button.pack(pady=15)
        
        # Reset password button
        self.reset_button = ctk.CTkButton(
            self.form_frame,
            text="Forgot Password?",
            fg_color="transparent",
            hover_color=("gray90", "gray20"),
            width=300,
            height=20,
            corner_radius=8,
            font=ctk.CTkFont(size=12),
            command=self.reset_password
        )
        self.reset_button.pack(pady=5)
        
        # Error message label
        self.error_label = ctk.CTkLabel(
            self.form_frame,
            text="",
            text_color="red",
            font=ctk.CTkFont(size=12)
        )
        self.error_label.pack(pady=5)
        
        # Footer section
        self.footer_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.footer_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        
        self.version_label = ctk.CTkLabel(
            self.footer_frame,
            text="v2.0.0 | © 2025 Face Detection Attendance System",
            font=ctk.CTkFont(size=10)
        )
        self.version_label.pack(side="bottom", pady=5)
        
        # Set initial focus to username field
        self.username_entry.focus_set()
        
        # Bind Enter key to login
        self.bind("<Return>", lambda event: self.login())
        
        # Center window on screen
        self.center_window()
        
        # Loading overlay
        self.loading_frame = None
        
        # Load saved credentials if available
        self.load_saved_credentials()
        
    def center_window(self):
        """Center the window on the screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def load_saved_credentials(self):
        """Load saved credentials if available"""
        username, password = self.credentials_manager.load_credentials()
        if username and password:
            self.username_entry.delete(0, tk.END)
            self.username_entry.insert(0, username)
            self.password_entry.delete(0, tk.END)
            self.password_entry.insert(0, password)
            self.remember_var.set(True)
            logger.info(f"Loaded saved credentials for user: {username}")
    
    def show_loading(self, show=True):
        """Show or hide loading overlay"""
        if show and not self.loading_frame:
            # Create loading overlay
            self.loading_frame = ctk.CTkFrame(self, corner_radius=0)
            self.loading_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            
            # Loading indicator
            loading_label = ctk.CTkLabel(
                self.loading_frame,
                text="Logging in...",
                font=ctk.CTkFont(size=16)
            )
            loading_label.place(relx=0.5, rely=0.5, anchor="center")
            
            # Update UI
            self.update_idletasks()
        elif not show and self.loading_frame:
            # Remove loading overlay
            self.loading_frame.destroy()
            self.loading_frame = None
            
            # Update UI
            self.update_idletasks()
    
    def display_error(self, message):
        """Display error message"""
        self.error_label.configure(text=message)
        
        # Clear error after 5 seconds
        self.after(5000, lambda: self.error_label.configure(text=""))
    
    def login(self):
        """Attempt to log in with provided credentials"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username:
            self.display_error("Username is required")
            self.username_entry.focus_set()
            return
        
        if not password:
            self.display_error("Password is required")
            self.password_entry.focus_set()
            return
        
        # Show loading overlay
        self.show_loading()
        
        # Use a thread for authentication to keep UI responsive
        threading.Thread(target=self._authenticate, args=(username, password), daemon=True).start()
    
    def _authenticate(self, username, password):
        """Perform authentication in a separate thread"""
        try:
            # Attempt to authenticate
            user_info = self.auth_system.authenticate(username, password)
            
            # Process result on the main thread
            self.after(0, lambda: self._process_auth_result(user_info, username, password))
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.after(0, lambda: self._handle_auth_error(str(e)))
    
    def _process_auth_result(self, user_info, username, password):
        """Process authentication result"""
        # Hide loading overlay
        self.show_loading(False)
        
        if user_info:
            # Authentication successful
            
            # Save credentials if "Remember me" is checked
            remember_me = self.remember_var.get()
            self.credentials_manager.save_credentials(username, password, remember_me)
            
            self.withdraw()  # Hide login window
            
            try:
                # Start main application with proper error handling for the icon
                app = ModernAttendanceApp(self.auth_system)
                
                # Remove the iconphoto call that might cause an error in the main app
                # Let the main app handle its own icon
                
                app.protocol("WM_DELETE_WINDOW", lambda: self._on_main_app_close(app))
                app.mainloop()
            except Exception as e:
                logger.error(f"Error starting main application: {e}")
                messagebox.showerror("Error", f"Failed to start application: {e}")
                self.deiconify()  # Show login window again
        else:
            # Authentication failed
            self.display_error("Invalid username or password")
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus_set()
    
    def _handle_auth_error(self, error_message):
        """Handle authentication error"""
        # Hide loading overlay
        self.show_loading(False)
        
        # Display error message
        self.display_error(f"Login error: {error_message}")
        
        # Reset password field
        self.password_entry.delete(0, tk.END)
        self.password_entry.focus_set()
    
    def _on_main_app_close(self, app):
        """Handle main application close"""
        # Destroy main application
        app.destroy()
        
        # Log out user
        self.auth_system.logout()
        
        # Show login window again
        self.deiconify()
        
        # Reset fields if "Remember me" is not checked
        if not self.remember_var.get():
            self.username_entry.delete(0, tk.END)
            self.password_entry.delete(0, tk.END)
        
        self.username_entry.focus_set()
    
    def reset_password(self):
        """Reset password functionality"""
        username = self.username_entry.get().strip()
        
        if not username:
            self.display_error("Enter username to reset password")
            self.username_entry.focus_set()
            return
        
        # Confirm reset
        confirm = messagebox.askyesno(
            "Reset Password",
            f"Do you want to reset password for '{username}'?\n\nA new password will be generated."
        )
        
        if confirm:
            try:
                # Reset password
                new_password = self.auth_system.reset_password(username=username)
                
                if new_password:
                    # Show new password
                    messagebox.showinfo(
                        "Password Reset Successful",
                        f"New password for '{username}':\n\n{new_password}\n\nPlease make note of this password."
                    )
                else:
                    # Reset failed
                    messagebox.showerror(
                        "Password Reset Failed",
                        f"Failed to reset password for '{username}'.\nUser may not exist or is inactive."
                    )
            except Exception as e:
                logger.error(f"Password reset error: {e}")
                messagebox.showerror("Error", f"Failed to reset password: {e}")

def main():
    """Main entry point for the login window"""
    try:
        app = LoginWindow()
        
        # Fix the icon loading
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icons", "app_icon.png")
            if os.path.exists(icon_path):
                icon_image = Image.open(icon_path)
                app_icon = ctk.CTkImage(light_image=icon_image, dark_image=icon_image, size=(64, 64))
                app.iconphoto(True, ImageTk.PhotoImage(icon_image))
                logger.info("Application icon set successfully")
            else:
                logger.warning(f"Icon file not found at {icon_path}")
        except Exception as icon_error:
            logger.warning(f"Failed to set application icon: {icon_error}")
            # Continue without the icon rather than failing
        
        app.mainloop()
    except Exception as e:
        logger.error(f"Error starting main application: {str(e)}")
        messagebox.showerror("Application Error", f"An error occurred while starting the application:\n{str(e)}")

if __name__ == "__main__":
    main()