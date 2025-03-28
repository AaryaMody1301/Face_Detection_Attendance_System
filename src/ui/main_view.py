"""
Main View for the Face Detection Attendance System

This module provides the main application view.
"""
import os
import tkinter as tk
from tkinter import ttk
import logging
import customtkinter as ctk
from PIL import Image, ImageTk
from typing import Dict, Any, List, Optional, Callable

from .base_view import BaseView
from ..utils.exceptions import AuthenticationError, AuthorizationError
from ..auth.auth_manager import AuthManager
from ..utils.app_config import AppConfig

# Configure logger
logger = logging.getLogger(__name__)

class MainView(BaseView):
    """
    Main application view
    
    Attributes:
        auth_manager: Authentication manager
        current_page: Currently displayed page
        sidebar_buttons: Dictionary of sidebar buttons
    """
    
    def __init__(self, master, auth_manager: AuthManager, **kwargs):
        """
        Initialize main view
        
        Args:
            master: Parent widget
            auth_manager: Authentication manager
            **kwargs: Additional arguments for BaseView
        """
        # Initialize base view
        super().__init__(master, **kwargs)
        
        # Store references
        self.auth_manager = auth_manager
        self.config = AppConfig()
        
        # Set view state
        self.current_page = None
        self.sidebar_buttons = {}
        self.content_frame = None
        self.sidebar_frame = None
        self.header_frame = None
        self.footer_frame = None
        self.status_var = tk.StringVar(value="Ready")
        self.title_var = tk.StringVar(value="Face Detection Attendance System")
        self.page_views = {}
        
        # Set up UI
        self.setup_ui()
        
        # Initial page load
        self.navigate_to("dashboard")
    
    def setup_ui(self):
        """Set up the main UI layout"""
        # Configure the main grid layout
        self.columnconfigure(0, weight=0)  # Sidebar
        self.columnconfigure(1, weight=1)  # Content
        self.rowconfigure(0, weight=0)  # Header
        self.rowconfigure(1, weight=1)  # Main content
        self.rowconfigure(2, weight=0)  # Footer
        
        # Create header
        self.header_frame = self._create_header()
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        # Create sidebar
        self.sidebar_frame = self._create_sidebar()
        self.sidebar_frame.grid(row=1, column=0, sticky="ns", padx=0, pady=0)
        
        # Create content area
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)
        
        # Create footer
        self.footer_frame = self._create_footer()
        self.footer_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
    
    def _create_header(self) -> ctk.CTkFrame:
        """
        Create header frame
        
        Returns:
            Header frame
        """
        header = ctk.CTkFrame(self, fg_color=("gray85", "gray25"), corner_radius=0, height=60)
        header.columnconfigure(0, weight=0)  # Logo
        header.columnconfigure(1, weight=1)  # Title
        header.columnconfigure(2, weight=0)  # User menu
        
        # Logo (if available)
        try:
            logo_path = os.path.join("assets", "icons", "app_icon.png")
            if os.path.exists(logo_path):
                logo = Image.open(logo_path).resize((40, 40))
                logo_img = ctk.CTkImage(
                    light_image=logo, 
                    dark_image=logo, 
                    size=(40, 40)
                )
                logo_label = ctk.CTkLabel(header, image=logo_img, text="")
                logo_label.grid(row=0, column=0, padx=15, pady=10)
            else:
                # Fallback logo
                logo_label = ctk.CTkLabel(
                    header, 
                    text="FR",
                    font=ctk.CTkFont(size=20, weight="bold"),
                    width=40
                )
                logo_label.grid(row=0, column=0, padx=15, pady=10)
        except Exception as e:
            logger.warning(f"Error loading logo: {e}")
            # Fallback logo
            logo_label = ctk.CTkLabel(
                header, 
                text="FR",
                font=ctk.CTkFont(size=20, weight="bold"),
                width=40
            )
            logo_label.grid(row=0, column=0, padx=15, pady=10)
        
        # Title label (dynamic)
        title_label = ctk.CTkLabel(
            header, 
            textvariable=self.title_var,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=1, padx=10, sticky="w")
        
        # User menu
        user_frame = ctk.CTkFrame(header, fg_color="transparent")
        user_frame.grid(row=0, column=2, padx=10, pady=10, sticky="e")
        
        # Get user info
        current_user = self.auth_manager.get_current_user()
        username = current_user.get('username', 'Guest') if current_user else 'Guest'
        role = current_user.get('role', 'guest') if current_user else 'guest'
        
        # User name and role
        user_label = ctk.CTkLabel(
            user_frame, 
            text=username,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        user_label.pack(anchor="e")
        
        role_label = ctk.CTkLabel(
            user_frame, 
            text=f"Role: {role.capitalize()}",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70")
        )
        role_label.pack(anchor="e")
        
        return header
    
    def _create_sidebar(self) -> ctk.CTkFrame:
        """
        Create sidebar frame
        
        Returns:
            Sidebar frame
        """
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        
        # Menu items based on user permissions
        menu_items = self._get_menu_items()
        
        # Create menu buttons
        for i, item in enumerate(menu_items):
            if item.get("type") == "separator":
                # Add separator
                separator = ttk.Separator(sidebar, orient="horizontal")
                separator.pack(fill="x", padx=10, pady=5)
                continue
                
            # Create button
            button = ctk.CTkButton(
                sidebar,
                text=item.get("label", "Unknown"),
                command=lambda page=item.get("page"): self.navigate_to(page),
                fg_color="transparent",
                border_spacing=10,
                anchor="w",
                height=40,
                font=ctk.CTkFont(size=13)
            )
            button.pack(fill="x", padx=5, pady=(2, 2))
            
            # Store button reference
            self.sidebar_buttons[item.get("page")] = button
        
        # Add logout button at bottom
        separator = ttk.Separator(sidebar, orient="horizontal")
        separator.pack(fill="x", padx=10, pady=5)
        
        logout_button = ctk.CTkButton(
            sidebar,
            text="Logout",
            command=self._handle_logout,
            fg_color="transparent",
            border_spacing=10,
            anchor="w",
            height=40,
            font=ctk.CTkFont(size=13)
        )
        logout_button.pack(fill="x", padx=5, pady=(2, 2))
        
        return sidebar
    
    def _create_footer(self) -> ctk.CTkFrame:
        """
        Create footer frame
        
        Returns:
            Footer frame
        """
        footer = ctk.CTkFrame(self, fg_color=("gray85", "gray25"), corner_radius=0, height=25)
        footer.columnconfigure(0, weight=1)  # Status
        footer.columnconfigure(1, weight=0)  # Version
        
        # Status label
        status_label = ctk.CTkLabel(
            footer, 
            textvariable=self.status_var,
            font=ctk.CTkFont(size=10)
        )
        status_label.grid(row=0, column=0, padx=10, pady=2, sticky="w")
        
        # Version label
        version = self.config.get("version", "1.0.0")
        version_label = ctk.CTkLabel(
            footer, 
            text=f"v{version}",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray70")
        )
        version_label.grid(row=0, column=1, padx=10, pady=2, sticky="e")
        
        return footer
    
    def _get_menu_items(self) -> List[Dict[str, Any]]:
        """
        Get menu items based on user permissions
        
        Returns:
            List of menu item dictionaries
        """
        # Default menu items that everyone can see
        menu_items = [
            {"label": "Dashboard", "page": "dashboard"},
            {"type": "separator"}
        ]
        
        # Attendance related items
        if self.auth_manager.has_permission("mark_attendance"):
            menu_items.append({"label": "Take Attendance", "page": "take_attendance"})
            
        if self.auth_manager.has_permission("view_attendance"):
            menu_items.append({"label": "View Attendance", "page": "view_attendance"})
            
        # Student management
        if self.auth_manager.has_permission("view_students"):
            menu_items.append({"type": "separator"})
            menu_items.append({"label": "Students", "page": "students"})
            
        if self.auth_manager.has_permission("add_student"):
            menu_items.append({"label": "Add Student", "page": "add_student"})
            
        # Analytics
        if self.auth_manager.has_permission("view_analytics"):
            menu_items.append({"type": "separator"})
            menu_items.append({"label": "Analytics", "page": "analytics"})
            
        # Admin functions
        if self.auth_manager.has_permission("system_settings"):
            menu_items.append({"type": "separator"})
            menu_items.append({"label": "Settings", "page": "settings"})
            
        if self.auth_manager.has_permission("manage_users"):
            menu_items.append({"label": "User Management", "page": "users"})
        
        return menu_items
    
    def navigate_to(self, page_name: str):
        """
        Navigate to a specific page
        
        Args:
            page_name: Name of the page to navigate to
        """
        # Check if page exists and user has permission
        if not self._has_permission_for_page(page_name):
            self.show_error("You don't have permission to access this page")
            return
            
        # Update current page and UI
        self.current_page = page_name
        self._update_ui_for_page(page_name)
        
        # Update page content
        self._load_page_content(page_name)
        
        # Update status
        self.status_var.set(f"Viewing {page_name.replace('_', ' ').title()}")
        
        # Log navigation
        logger.info(f"Navigated to page: {page_name}")
    
    def _has_permission_for_page(self, page_name: str) -> bool:
        """
        Check if current user has permission to access a page
        
        Args:
            page_name: Name of the page
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        # Map pages to required permissions
        page_permissions = {
            "dashboard": None,  # All authenticated users
            "take_attendance": "mark_attendance",
            "view_attendance": "view_attendance",
            "students": "view_students",
            "add_student": "add_student",
            "analytics": "view_analytics",
            "settings": "system_settings",
            "users": "manage_users"
        }
        
        # Get required permission for the page
        required_permission = page_permissions.get(page_name)
        
        # If no specific permission required, allow access to all authenticated users
        if required_permission is None:
            return True
            
        return self.auth_manager.has_permission(required_permission)
    
    def _update_ui_for_page(self, page_name: str):
        """
        Update UI for the selected page
        
        Args:
            page_name: Name of the page
        """
        # Update sidebar button states
        for page, button in self.sidebar_buttons.items():
            if page == page_name:
                button.configure(fg_color=("gray75", "gray40"))
            else:
                button.configure(fg_color="transparent")
        
        # Update window title
        page_title = page_name.replace("_", " ").title()
        self.title_var.set(f"Face Detection Attendance - {page_title}")
        
        # Update master window title
        if hasattr(self.master, "title"):
            self.master.title(f"Face Detection Attendance System - {page_title}")
    
    def _load_page_content(self, page_name: str):
        """
        Load content for the selected page
        
        Args:
            page_name: Name of the page
        """
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Check if we've already created this view
        if page_name in self.page_views:
            view = self.page_views[page_name]
            if view.winfo_exists():
                view.pack(fill="both", expand=True)
                view.refresh()  # Refresh view data
                return
        
        # Create placeholder content (will be replaced by actual views)
        placeholder = ctk.CTkFrame(self.content_frame)
        placeholder.pack(fill="both", expand=True)
        
        title_label = ctk.CTkLabel(
            placeholder,
            text=f"{page_name.replace('_', ' ').title()} Page",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=30)
        
        # Show appropriate message
        message = ctk.CTkLabel(
            placeholder,
            text=f"This is the {page_name.replace('_', ' ')} page.\nThis content will be replaced with actual functionality.",
            font=ctk.CTkFont(size=14),
            justify="center"
        )
        message.pack(pady=10)
        
        # Import and create the view class based on the page name
        # TODO: Replace this placeholder with actual view classes as they're implemented
        self.page_views[page_name] = placeholder
    
    def _handle_logout(self):
        """Handle logout button press"""
        # Ask for confirmation
        self.show_confirmation(
            message="Are you sure you want to logout?",
            title="Confirm Logout",
            on_yes=self._perform_logout
        )
    
    def _perform_logout(self):
        """Perform logout"""
        try:
            # Attempt to logout
            success = self.auth_manager.logout()
            
            if success:
                # Notify parent to switch to login view
                if hasattr(self.master, "show_login"):
                    self.master.show_login()
                else:
                    # Fallback: Show success message and exit
                    self.show_success("Logged out successfully")
                    self.master.destroy()
            else:
                self.show_error("Failed to logout")
                
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            self.show_error(f"An error occurred during logout")
    
    def refresh(self):
        """Refresh the current page"""
        if self.current_page and self.current_page in self.page_views:
            view = self.page_views[self.current_page]
            if hasattr(view, "refresh"):
                view.refresh()
    
    def set_status(self, message: str):
        """
        Set status message in footer
        
        Args:
            message: Status message to display
        """
        self.status_var.set(message)
        
    def on_close(self):
        """Clean up resources when view is closed"""
        super().on_close()
        # Close all page views
        for view in self.page_views.values():
            if hasattr(view, "on_close"):
                view.on_close()