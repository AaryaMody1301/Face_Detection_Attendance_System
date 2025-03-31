def _create_sidebar_button(self, text, icon_name, command, is_active=False):
        """Create a custom sidebar button with an icon"""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        # Get icon from icon manager
        try:
            icon = self.parent.icons.get_icon(icon_name, size=(20, 20))
        except Exception as e:
            logger.error(f"Error loading icon {icon_name}: {e}")
            icon = None
        
        # Create button with optional icon
        button = ctk.CTkButton(
            button_frame,
            text=text,
            image=icon,
            compound="left",
            anchor="w",
            fg_color="transparent" if not is_active else self.active_color,
            text_color=self.text_color,
            hover_color=self.hover_color,
            corner_radius=6,
            height=40,
            border_spacing=10,
            command=command
        )
        button.pack(side="top", fill="x", padx=5)
        
        # Store button reference for active state management
        self.sidebar_buttons.append((button_frame, button, text.lower()))
        
        return button_frame 