"""
Analytics Dashboard for Face Detection Attendance System
"""
import os
import logging
import tkinter as tk
import customtkinter as ctk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
import sqlite3
import threading
import matplotlib.dates as mdates

# Import from core modules
from src.core.database.db_handler import DatabaseHandler

# Set up logging
logger = logging.getLogger(__name__)

class AnalyticsDashboard(ctk.CTkFrame):
    """Analytics Dashboard for attendance data visualization"""
    
    def __init__(self, master, db_handler=None):
        """
        Initialize the analytics dashboard
        
        Args:
            master: Parent widget
            db_handler: Optional database handler instance
        """
        super().__init__(master)
        
        # Initialize variables
        self.attendance_data = None
        self.selected_course = "All"
        self.time_period = "month"
        self.chart_type = "attendance_over_time"
        
        # Use provided database handler or create a new one
        self.db = db_handler if db_handler else DatabaseHandler()
        
        # Thread for data loading
        self.data_thread = None
        self.loading = False
        
        # Create UI elements
        self._setup_ui()
        
        # Load data in a background thread
        self.load_data_async()
        
        logger.info("Analytics Dashboard initialized")
    
    def _setup_ui(self):
        """Set up the analytics UI with modern design"""
        # Configure grid layout
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=0)  # Control panel 
        self.grid_rowconfigure(2, weight=1)  # Chart area
        self.grid_columnconfigure(0, weight=1)
        
        # Title section with modern styling
        self.header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("#ffffff", "#1e1e1e"))
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Attendance Analytics",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        # Subtitle with helpful context
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Analyze attendance patterns and trends across courses",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray70")
        )
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Control panel with modern styling
        self.control_panel = ctk.CTkFrame(self, corner_radius=12, fg_color=("#ffffff", "#1e1e1e"))
        self.control_panel.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="ew")
        
        # Create a 2x4 grid with balanced spacing
        for i in range(4):
            self.control_panel.grid_columnconfigure(i, weight=1, pad=10)
        
        # Course selection with improved styling
        self.course_label = ctk.CTkLabel(
            self.control_panel,
            text="Course:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.course_label.grid(row=0, column=0, padx=(20, 5), pady=(20, 5), sticky="e")
        
        self.courses = ["All", "Computer Science", "Mathematics", "Physics", "Biology"]
        self.course_var = ctk.StringVar(value=self.selected_course)
        self.course_dropdown = ctk.CTkOptionMenu(
            self.control_panel,
            values=self.courses,
            variable=self.course_var,
            command=self._on_course_change,
            width=150,
            height=32,
            corner_radius=8,
            dropdown_font=ctk.CTkFont(size=13),
            font=ctk.CTkFont(size=13),
            fg_color=("#f0f0f0", "#2d2d2d"),
            button_color=("#0078D7", "#2D5F9A"),
            button_hover_color=("#0063B1", "#1D4F8A"),
            dropdown_hover_color=("#e0e0e0", "#3d3d3d")
        )
        self.course_dropdown.grid(row=0, column=1, padx=(0, 10), pady=(20, 5), sticky="w")
        
        # Time period selection with improved styling
        self.period_label = ctk.CTkLabel(
            self.control_panel,
            text="Period:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.period_label.grid(row=0, column=2, padx=(10, 5), pady=(20, 5), sticky="e")
        
        self.period_var = ctk.StringVar(value=self.time_period)
        self.period_dropdown = ctk.CTkOptionMenu(
            self.control_panel,
            values=["week", "month", "semester", "year"],
            variable=self.period_var,
            command=self._on_period_change,
            width=150,
            height=32,
            corner_radius=8,
            dropdown_font=ctk.CTkFont(size=13),
            font=ctk.CTkFont(size=13),
            fg_color=("#f0f0f0", "#2d2d2d"),
            button_color=("#0078D7", "#2D5F9A"),
            button_hover_color=("#0063B1", "#1D4F8A"),
            dropdown_hover_color=("#e0e0e0", "#3d3d3d")
        )
        self.period_dropdown.grid(row=0, column=3, padx=(0, 20), pady=(20, 5), sticky="w")
        
        # Chart type selection with improved styling
        self.chart_label = ctk.CTkLabel(
            self.control_panel,
            text="Chart:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.chart_label.grid(row=1, column=0, padx=(20, 5), pady=(5, 20), sticky="e")
        
        # Use more descriptive chart names
        chart_options = {
            "attendance_over_time": "Attendance Over Time",
            "student_comparison": "Student Comparison",
            "attendance_by_day": "Attendance By Day",
            "attendance_heatmap": "Attendance Heatmap"
        }
        
        self.chart_var = ctk.StringVar(value=chart_options[self.chart_type])
        self.chart_dropdown = ctk.CTkOptionMenu(
            self.control_panel,
            values=[chart_options[k] for k in chart_options.keys()],
            variable=self.chart_var,
            command=lambda v: self._on_chart_change(list(chart_options.keys())[list(chart_options.values()).index(v)]),
            width=150,
            height=32,
            corner_radius=8,
            dropdown_font=ctk.CTkFont(size=13),
            font=ctk.CTkFont(size=13),
            fg_color=("#f0f0f0", "#2d2d2d"),
            button_color=("#0078D7", "#2D5F9A"),
            button_hover_color=("#0063B1", "#1D4F8A"),
            dropdown_hover_color=("#e0e0e0", "#3d3d3d")
        )
        self.chart_dropdown.grid(row=1, column=1, padx=(0, 10), pady=(5, 20), sticky="w")
        
        # Export data button
        self.export_button = ctk.CTkButton(
            self.control_panel,
            text="Export Data",
            command=self._export_data,
            width=120,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(size=13),
            fg_color=("#4CAF50", "#2E7D32"),
            hover_color=("#43A047", "#1B5E20"),
            border_spacing=10
        )
        self.export_button.grid(row=1, column=2, padx=(10, 5), pady=(5, 20), sticky="e")
        
        # Refresh button with improved styling
        self.refresh_button = ctk.CTkButton(
            self.control_panel,
            text="Refresh Data",
            command=self._on_refresh,
            width=120,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(size=13),
            fg_color=("#0078D7", "#2D5F9A"),
            hover_color=("#0063B1", "#1D4F8A"),
            border_spacing=10
        )
        self.refresh_button.grid(row=1, column=3, padx=(0, 20), pady=(5, 20), sticky="w")
        
        # Loading indicator with modern styling
        self.loading_label = ctk.CTkLabel(
            self.control_panel,
            text="Loading data...",
            text_color=("#0078D7", "#2D5F9A"),
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
        self.loading_label.lift()  # Bring to front
        self.loading_label.grid_remove()  # Hide initially
        
        # Chart frame with modern styling
        self.chart_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("#ffffff", "#1e1e1e"))
        self.chart_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.chart_frame.grid_rowconfigure(0, weight=1)
        self.chart_frame.grid_columnconfigure(0, weight=1)
        
        # Create a frame for matplotlib with proper background
        self.plot_frame = ctk.CTkFrame(
            self.chart_frame, 
            fg_color=("white", "#1e1e1e"),
            corner_radius=8
        )
        self.plot_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Empty plot placeholder with loading message and styling
        self.canvas = None
        self.fig = None
        
        # Create placeholder with loading animation
        self.placeholder_frame = ctk.CTkFrame(
            self.plot_frame,
            fg_color="transparent"
        )
        self.placeholder_frame.pack(expand=True, fill="both")
        
        self.placeholder_label = ctk.CTkLabel(
            self.placeholder_frame,
            text="Loading attendance data...",
            font=ctk.CTkFont(size=16)
        )
        self.placeholder_label.pack(pady=(100, 10))
        
        # Add a loading animation (spinner or progress bar)
        self.loading_spinner = ctk.CTkProgressBar(
            self.placeholder_frame,
            width=200,
            height=10,
            corner_radius=5,
            mode="indeterminate"
        )
        self.loading_spinner.pack(pady=10)
        self.loading_spinner.start()
    
    def _export_data(self):
        """Export data to CSV"""
        logger.info("Export data functionality would be implemented here")
        # This would be implemented to export data to CSV/Excel
    
    def load_data_async(self):
        """Load data in a background thread"""
        if self.loading:
            return
            
        self.loading = True
        
        # Show loading indicator
        self.refresh_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
        self.loading_label.configure(text="Loading data...")
        self.loading_label.grid()
        
        # Start loading thread
        self.data_thread = threading.Thread(target=self._load_data_thread)
        self.data_thread.daemon = True
        self.data_thread.start()
    
    def _load_data_thread(self):
        """Background thread for loading data"""
        try:
            # Create a new database connection for this thread
            from src.core.database.db_handler import DatabaseHandler
            thread_db = DatabaseHandler()
            
            try:
                # Get attendance data from the database using the thread-local connection
                attendance_data = self._get_attendance_data_from_db(thread_db)
                
                # Update UI on the main thread if the widget still exists
                if self.winfo_exists():
                    self.after(0, lambda: self._after_data_loaded(attendance_data))
            finally:
                # Close the thread-specific database connection
                thread_db.close()
            
        except Exception as e:
            logger.error(f"Error loading attendance data: {e}")
            if self.winfo_exists():
                self.after(0, lambda: self._show_error(f"Failed to load data: {str(e)}"))
                self.after(0, self._reset_loading_state)
    
    def _get_attendance_data_from_db(self, db_handler=None):
        """Get attendance data from database and backup files"""
        try:
            # Initialize empty DataFrame
            attendance_data = pd.DataFrame()
            
            # First try to get data from database
            try:
                # Use provided handler or create a thread-local one if needed
                should_close = False
                if db_handler is None:
                    db_handler = DatabaseHandler()
                    should_close = True
                    
                try:
                    # Get attendance records from database
                    db_data = db_handler.get_all_attendance_records()
                    if not db_data.empty:
                        attendance_data = db_data
                        logger.info(f"Loaded {len(db_data)} records from database")
                finally:
                    # Close connection if we created it
                    if should_close and db_handler:
                        db_handler.close()
            except Exception as e:
                logger.warning(f"Could not load data from database: {e}")
            
            # Then try to load backup attendance files from CSV
            csv_data = self._load_backup_attendance_files()
            if not csv_data.empty:
                # If we already have database data, combine them
                if not attendance_data.empty:
                    # Make sure columns match
                    csv_data = csv_data.rename(columns={
                        'ID': 'student_id',
                        'Name': 'student_name',
                        'Time': 'time',
                        'Date': 'date'
                    })
                    
                    # Combine data
                    attendance_data = pd.concat([attendance_data, csv_data], ignore_index=True)
                    logger.info(f"Combined {len(csv_data)} records from CSV files with database data")
                else:
                    # Just use CSV data
                    attendance_data = csv_data
                    logger.info(f"Loaded {len(csv_data)} records from CSV files")
            
            # If still no data, show warning
            if attendance_data.empty:
                logger.warning("No attendance data found in database or CSV files")
                
            return attendance_data
            
        except Exception as e:
            logger.error(f"Error getting attendance records: {e}")
            return pd.DataFrame()
    
    def _load_backup_attendance_files(self):
        """Load attendance data from backup CSV files"""
        try:
            # Get attendance directory from config or use default
            attendance_dir = os.path.join(os.getcwd(), "data", "attendance")
            if not os.path.exists(attendance_dir):
                logger.warning(f"Attendance directory not found: {attendance_dir}")
                return pd.DataFrame()
            
            # Look for CSV files in the attendance directory
            attendance_files = [f for f in os.listdir(attendance_dir) if f.endswith('.csv') and f.startswith('attendance_')]
            
            if not attendance_files:
                logger.warning(f"No attendance CSV files found in {attendance_dir}")
                return pd.DataFrame()
            
            # Load and combine all CSV files
            all_data = []
            for file in attendance_files:
                try:
                    file_path = os.path.join(attendance_dir, file)
                    df = pd.read_csv(file_path)
                    
                    # Add source file for tracking
                    df['source_file'] = file
                    
                    # Check required columns
                    required_cols = ['ID', 'Name', 'Time', 'Date']
                    if not all(col in df.columns for col in required_cols):
                        logger.warning(f"File {file} is missing required columns: {required_cols}")
                        continue
                        
                    all_data.append(df)
                    logger.info(f"Loaded {len(df)} records from {file}")
                except Exception as e:
                    logger.error(f"Error loading file {file}: {e}")
            
            if not all_data:
                logger.warning("No valid attendance data found in CSV files")
                return pd.DataFrame()
                
            # Combine all DataFrames
            combined_data = pd.concat(all_data, ignore_index=True)
            
            # Convert date strings to datetime objects for better handling
            try:
                combined_data['Date'] = pd.to_datetime(combined_data['Date'])
            except Exception as e:
                logger.warning(f"Error converting dates: {e}")
            
            return combined_data
            
        except Exception as e:
            logger.error(f"Error loading backup attendance files: {e}")
            return pd.DataFrame()

    def _after_data_loaded(self, attendance_data=None):
        """Process loaded data"""
        if attendance_data is not None:
            self.attendance_data = attendance_data
            
        if self.attendance_data is None or self.attendance_data.empty:
            self._show_error("No attendance data to display")
            logger.error("No attendance data to display")
        else:
            # Update charts and stats
            self._create_chart()
            logger.info(f"Loaded attendance data with {len(self.attendance_data)} records")
        
        self._reset_loading_state()
        
    def _reset_loading_state(self):
        """Reset the loading state"""
        self.loading = False
        self.refresh_button.configure(state="normal")
        self.export_button.configure(state="normal")
        self.loading_label.grid_remove()
        
    def _on_course_change(self, value):
        """Handle course change"""
        self.selected_course = value
        self.update_chart()
        
    def _on_period_change(self, value):
        """Handle period change"""
        self.time_period = value
        self.update_chart()
        
    def _on_chart_change(self, value):
        """Handle chart type change"""
        self.chart_type = value
        self.update_chart()
        
    def _on_refresh(self):
        """Handle refresh button click"""
        self.load_data_async()
        
    def _show_error(self, message):
        """Show error message in the chart area"""
        # Clear the plot frame
        for widget in self.plot_frame.winfo_children():
            widget.destroy()
            
        # Create error display
        error_frame = ctk.CTkFrame(self.plot_frame, fg_color="transparent")
        error_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Error icon
        error_label = ctk.CTkLabel(
            error_frame,
            text="⚠️",
            font=ctk.CTkFont(size=48)
        )
        error_label.pack(pady=(80, 10))
        
        # Error title
        error_title = ctk.CTkLabel(
            error_frame,
            text="Data Loading Error",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        error_title.pack(pady=(0, 10))
        
        # Error message
        error_message = ctk.CTkLabel(
            error_frame,
            text=message,
            font=ctk.CTkFont(size=14),
            wraplength=500
        )
        error_message.pack(pady=(0, 20))
        
        # Retry button
        retry_button = ctk.CTkButton(
            error_frame,
            text="Retry",
            command=self._on_refresh,
            width=120,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(size=13)
        )
        retry_button.pack(pady=10)
        
    def cleanup(self):
        """Clean up resources"""
        try:
            # Close any active database connections
            if hasattr(self, 'db') and self.db:
                self.db.close()
                
            # Clear plot resources
            if hasattr(self, 'fig') and self.fig:
                plt.close(self.fig)
                
            logger.info("Analytics dashboard resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def update_chart(self):
        """Update the chart based on current selections"""
        if self.loading:
            return
            
        if not self.attendance_data or self.attendance_data.empty:
            return
            
        # Apply filters and create appropriate chart
        self._create_chart()
    
    def _create_chart(self):
        """Create the appropriate chart based on the selection"""
        # Clear existing plot
        if hasattr(self, 'fig') and self.fig:
            plt.close(self.fig)
            
        # Clear the plot frame
        for widget in self.plot_frame.winfo_children():
            widget.destroy()
            
        # Get filtered data
        filtered_data = self.filter_data()
        
        if filtered_data.empty:
            self._show_error("No data available for the selected filters")
            return
            
        # Create figure and axis with modern styling
        bgcolor = "white" if ctk.get_appearance_mode() == "Light" else "#1e1e1e"
        textcolor = "#333333" if ctk.get_appearance_mode() == "Light" else "#ffffff"
        
        self.fig, ax = plt.subplots(figsize=(12, 6), facecolor=bgcolor)
        
        # Apply styling to the figure
        ax.set_facecolor(bgcolor)
        ax.xaxis.label.set_color(textcolor)
        ax.yaxis.label.set_color(textcolor)
        ax.tick_params(colors=textcolor, which='both')
        for spine in ax.spines.values():
            spine.set_color("#dddddd" if ctk.get_appearance_mode() == "Light" else "#333333")
            
        # Render the appropriate chart type
        if self.chart_type == "attendance_over_time":
            self.render_attendance_over_time(filtered_data, ax)
        elif self.chart_type == "student_comparison":
            self.render_student_comparison(filtered_data, ax)
        elif self.chart_type == "attendance_by_day":
            self.render_attendance_by_day(filtered_data, ax)
        elif self.chart_type == "attendance_heatmap":
            self.render_attendance_heatmap(filtered_data, ax)
        else:
            self.render_attendance_over_time(filtered_data, ax)
            
        # Add title with styling
        title_text = f"{self.chart_dropdown.get()} - {self.selected_course}"
        ax.set_title(title_text, color=textcolor, fontsize=14, pad=20)
        
        # Create canvas
        canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill="both", expand=True)
        
        # Add interactivity
        self._add_plot_interactivity()
        
        return canvas

    def _add_plot_interactivity(self):
        """Add interactivity to the plots"""
        # Connect hover event
        self.hover_id = self.fig.canvas.mpl_connect('motion_notify_event', self._on_hover)
        
        # Connect click event
        self.click_id = self.fig.canvas.mpl_connect('button_press_event', self._on_click)
    
    def _on_hover(self, event):
        """Handle hover events on the plot"""
        if event.inaxes:
            # Update status bar with coordinates
            status_text = f"x={event.xdata:.2f}, y={event.ydata:.2f}"
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.configure(text=status_text)
            else:
                # Create status label if it doesn't exist
                self.status_label = ctk.CTkLabel(
                    self.chart_frame, 
                    text=status_text,
                    height=20,
                    anchor="e",
                    font=ctk.CTkFont(size=10)
                )
                self.status_label.grid(row=2, column=1, padx=10, pady=(0, 5), sticky="e")
    
    def _on_click(self, event):
        """Handle click events on the plot"""
        if event.inaxes:
            # Get the selected data point
            x, y = event.xdata, event.ydata
            
            # Find the nearest data point
            # Implementation depends on the type of chart
            
            # Show detailed information about the point
            if hasattr(self, 'detail_window') and self.detail_window.winfo_exists():
                self.detail_window.destroy()
                
            self.detail_window = ctk.CTkToplevel(self)
            self.detail_window.title("Data Point Details")
            self.detail_window.geometry("300x200")
            self.detail_window.resizable(False, False)
            
            ctk.CTkLabel(
                self.detail_window,
                text=f"Position: ({x:.2f}, {y:.2f})",
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(pady=(20, 10))
            
            ctk.CTkLabel(
                self.detail_window,
                text="Click on a data point to view more details",
                wraplength=250
            ).pack(pady=10)
            
            ctk.CTkButton(
                self.detail_window,
                text="Close",
                command=self.detail_window.destroy
            ).pack(pady=20)

    def render_attendance_over_time(self, data, ax):
        """Render attendance over time chart"""
        try:
            # Check if data is empty
            if data is None or (hasattr(data, 'empty') and data.empty) or (isinstance(data, list) and len(data) == 0):
                ax.text(0.5, 0.5, "No attendance data available for the selected period", 
                      horizontalalignment='center', verticalalignment='center',
                      transform=ax.transAxes, fontsize=14, color='gray')
                return
            
            # Convert to DataFrame if it's a list or dictionary
            if isinstance(data, (list, dict)):
                data = pd.DataFrame(data)
            
            # Make sure we have a datetime column
            date_col = None
            for col in data.columns:
                if col.lower() in ['date', 'dates', 'datetime', 'timestamp']:
                    date_col = col
                    break
            
            if date_col is None:
                ax.text(0.5, 0.5, "No date information found in data", 
                      horizontalalignment='center', verticalalignment='center',
                      transform=ax.transAxes, fontsize=14, color='gray')
                return
            
            # Ensure date column is datetime type
            if not pd.api.types.is_datetime64_any_dtype(data[date_col]):
                try:
                    data[date_col] = pd.to_datetime(data[date_col])
                except Exception as e:
                    logger.error(f"Error converting dates: {e}")
                    ax.text(0.5, 0.5, f"Error processing dates: {str(e)}", 
                          horizontalalignment='center', verticalalignment='center',
                          transform=ax.transAxes, fontsize=14, color='red')
                    return
            
            # Group by date and count
            try:
                daily_counts = data.groupby(data[date_col].dt.date).size()
                
                # Convert to Series if needed
                if not isinstance(daily_counts, pd.Series):
                    daily_counts = pd.Series(daily_counts)
                
                # Sort by date
                daily_counts = daily_counts.sort_index()
                
                # Plot the data
                bars = ax.bar(daily_counts.index, daily_counts.values, 
                         color='#3498db', alpha=0.8, width=0.8)
                
                # Add value labels on top of bars
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:  # Only add text to non-zero bars
                        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                               f'{int(height)}', ha='center', va='bottom', fontsize=9)
                
                # Format x-axis as dates
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                
                # Rotate date labels for better readability
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
                
                # Set labels and title
                ax.set_title('Attendance Over Time')
                ax.set_xlabel('Date')
                ax.set_ylabel('Number of Students')
                
                # Add grid for y-axis
                ax.grid(True, axis='y', linestyle='--', alpha=0.7)
                
                # Adjust layout to make sure dates are fully visible
                plt.tight_layout()
                
                # Adjust colors for dark theme if needed
                if ctk.get_appearance_mode() == "Dark":
                    self._apply_dark_theme(ax)
                
            except Exception as e:
                logger.error(f"Error plotting attendance data: {e}")
                ax.text(0.5, 0.5, f"Error plotting data: {str(e)}", 
                      horizontalalignment='center', verticalalignment='center',
                      transform=ax.transAxes, fontsize=14, color='red')
            
        except Exception as e:
            logger.error(f"Error in render_attendance_over_time: {e}")
            ax.text(0.5, 0.5, f"Error rendering chart: {str(e)}", 
                  horizontalalignment='center', verticalalignment='center',
                  transform=ax.transAxes, fontsize=12, color='red')

    def render_student_comparison(self, data, ax):
        """Render student attendance comparison chart"""
        # Group data by student
        student_attendance = {}
        for record in data:
            name = record.get('name', 'Unknown')
            if name in student_attendance:
                student_attendance[name] += 1
            else:
                student_attendance[name] = 1
        
        # Sort by attendance count (descending)
        sorted_students = sorted(student_attendance.items(), key=lambda x: x[1], reverse=True)
        
        # Limit to top 15 students for readability
        if len(sorted_students) > 15:
            sorted_students = sorted_students[:15]
            
        # Extract data for plotting
        names = [s[0] for s in sorted_students]
        counts = [s[1] for s in sorted_students]
        
        # Create horizontal bar chart for better name display
        bars = ax.barh(names, counts, color='#2ecc71')
        
        # Add values at the end of each bar
        for i, v in enumerate(counts):
            ax.text(v + 0.1, i, str(v), va='center')
        
        # Set labels and title
        ax.set_title('Attendance by Student')
        ax.set_xlabel('Number of Attendances')
        ax.set_ylabel('Student')
        
        # Adjust colors for theme
        if ctk.get_appearance_mode() == "Dark":
            self._apply_dark_theme(ax)
            
        # Auto-adjust to fit all names
        self.fig.tight_layout()

    def render_attendance_by_day(self, data, ax):
        """Render attendance distribution by day of week"""
        # Map days of week
        day_map = {
            0: 'Monday',
            1: 'Tuesday',
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday'
        }
        
        # Count attendance by day of week
        day_counts = {day: 0 for day in range(7)}
        
        for record in data:
            date_str = record.get('date')
            try:
                # Parse date string
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                # Get day of week (0 = Monday, 6 = Sunday)
                day_of_week = date_obj.weekday()
                day_counts[day_of_week] += 1
            except (ValueError, TypeError):
                logger.warning(f"Could not parse date: {date_str}")
        
        # Prepare data for plotting
        days = [day_map[d] for d in range(7)]
        counts = [day_counts[d] for d in range(7)]
        
        # Define colors
        colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c', '#34495e']
        
        # Create bar chart
        bars = ax.bar(days, counts, color=colors)
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.0f}',
                    ha='center', va='bottom', fontsize=9)
        
        # Set labels and title
        ax.set_title('Attendance by Day of Week')
        ax.set_xlabel('Day')
        ax.set_ylabel('Number of Students')
        
        # Rotate x-axis labels for better readability
        ax.tick_params(axis='x', rotation=30)
        
        # Add grid lines for y-axis only
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # Adjust colors for theme
        if ctk.get_appearance_mode() == "Dark":
            self._apply_dark_theme(ax)

    def render_attendance_heatmap(self, data, ax):
        """Render attendance heatmap by day and hour"""
        # Extract hours and days from data
        day_hour_counts = {}
        
        # Define our time slots for readability (24h format)
        time_slots = ["8:00", "9:00", "10:00", "11:00", "12:00", "13:00", 
                     "14:00", "15:00", "16:00", "17:00", "18:00"]
        
        # Map days of week
        day_map = {
            0: 'Mon',
            1: 'Tue',
            2: 'Wed',
            3: 'Thu',
            4: 'Fri',
            5: 'Sat',
            6: 'Sun'
        }
        
        # Initialize the matrix with zeros
        attendance_matrix = np.zeros((7, len(time_slots)))
        
        # Helper function to extract hour from time string
        def extract_hour(time_str):
            try:
                if isinstance(time_str, str) and ":" in time_str:
                    hour = int(time_str.split(":")[0])
                    return hour
                return None
            except (ValueError, TypeError, IndexError):
                return None
        
        for record in data:
            try:
                date_str = record.get('date')
                time_str = record.get('time')
                
                if date_str and time_str:
                    # Parse date and get day of week
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    day_of_week = date_obj.weekday()  # 0=Monday, 6=Sunday
                    
                    # Extract hour
                    hour = extract_hour(time_str)
                    
                    if hour is not None:
                        # Map hour to time slot index
                        slot_index = max(0, min(len(time_slots) - 1, (hour - 8)))
                        
                        # Increment the count for this day and hour
                        attendance_matrix[day_of_week, slot_index] += 1
            except Exception as e:
                logger.error(f"Error processing record for heatmap: {e}")
        
        # Create heatmap
        im = ax.imshow(attendance_matrix, cmap='viridis', aspect='auto')
        
        # Add colorbar
        plt.colorbar(im, ax=ax, label='Number of Students')
        
        # Configure axis labels
        ax.set_xticks(np.arange(len(time_slots)))
        ax.set_yticks(np.arange(7))
        ax.set_xticklabels(time_slots)
        ax.set_yticklabels([day_map[d] for d in range(7)])
        
        # Rotate x-axis labels for better readability
        ax.tick_params(axis='x', rotation=45)
        
        # Set title
        ax.set_title('Attendance Heatmap (Day vs Hour)')
        
        # Add text annotations in each cell
        for i in range(7):
            for j in range(len(time_slots)):
                value = attendance_matrix[i, j]
                if value > 0:
                    text_color = 'white' if value > np.max(attendance_matrix) / 2 else 'black'
                    ax.text(j, i, f"{int(value)}", ha="center", va="center", color=text_color)

    def render_day_of_week_distribution(self, data, ax):
        """Render attendance distribution by day of week as a pie chart"""
        # Map days of week
        day_map = {
            0: 'Monday',
            1: 'Tuesday',
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday'
        }
        
        # Count attendance by day of week
        day_counts = {day: 0 for day in range(7)}
        
        for record in data:
            date_str = record.get('date')
            try:
                # Parse date string
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                # Get day of week (0 = Monday, 6 = Sunday)
                day_of_week = date_obj.weekday()
                day_counts[day_of_week] += 1
            except (ValueError, TypeError):
                logger.warning(f"Could not parse date: {date_str}")
        
        # Prepare data for plotting
        labels = [day_map[d] for d in range(7)]
        counts = [day_counts[d] for d in range(7)]
        
        # Define colors
        colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c', '#34495e']
        
        # Filter out days with no attendance
        non_zero_indices = [i for i, count in enumerate(counts) if count > 0]
        filtered_labels = [labels[i] for i in non_zero_indices]
        filtered_counts = [counts[i] for i in non_zero_indices]
        filtered_colors = [colors[i] for i in non_zero_indices]
        
        # If all counts are zero, show message
        if sum(counts) == 0:
            ax.text(0.5, 0.5, "No attendance data available", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.set_title('Day Distribution')
            return
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            filtered_counts, 
            labels=None,  # We'll add a legend instead
            autopct='%1.1f%%', 
            startangle=90, 
            colors=filtered_colors,
            wedgeprops={'edgecolor': 'white', 'linewidth': 1}
        )
        
        # Add a legend
        ax.legend(wedges, filtered_labels, title="Days", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
        
        # Set title
        ax.set_title('Attendance Distribution by Day')
        
        # Equal aspect ratio ensures circular pie
        ax.set_aspect('equal')
        
        # Style the percentage text
        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_weight('bold')

    def render_attendance_trends(self, data, ax):
        """Render attendance trends with moving average"""
        # Group data by date
        date_counts = {}
        for record in data:
            date = record.get('date')
            if date in date_counts:
                date_counts[date] += 1
            else:
                date_counts[date] = 1
                
        # Check if we have enough data
        if len(date_counts) < 2:
            ax.text(0.5, 0.5, "Insufficient data for trend analysis", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.set_title('Attendance Trend')
            return
                
        # Sort dates
        sorted_dates = sorted(date_counts.keys())
        counts = [date_counts[date] for date in sorted_dates]
        
        # Create scatter plot
        ax.scatter(sorted_dates, counts, color='#3498db', alpha=0.7, label='Daily')
        
        # Calculate moving average if enough data
        if len(counts) >= 3:
            window_size = min(3, len(counts))
            moving_avg = np.convolve(counts, np.ones(window_size)/window_size, mode='valid')
            
            # Plot moving average
            # Adjust x values for the moving average (center-aligned)
            ma_x = sorted_dates[window_size-1:]
            ax.plot(ma_x, moving_avg, color='#e74c3c', linewidth=2, label=f'{window_size}-day Avg')
        
        # Linear trend line
        if len(sorted_dates) > 1:
            try:
                # Convert dates to numeric for linear regression
                x_numeric = np.arange(len(sorted_dates))
                z = np.polyfit(x_numeric, counts, 1)
                p = np.poly1d(z)
                ax.plot(sorted_dates, p(x_numeric), linestyle='--', color='#2ecc71', label='Trend')
                
                # Calculate trend direction
                if z[0] > 0:
                    trend_direction = "Increasing"
                elif z[0] < 0:
                    trend_direction = "Decreasing"
                else:
                    trend_direction = "Stable"
                    
                # Add trend information text
                ax.text(0.05, 0.95, f"Trend: {trend_direction}", transform=ax.transAxes, 
                        fontsize=10, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.5))
            except Exception as e:
                logger.error(f"Error calculating trend line: {e}")
        
        # Set labels and title
        ax.set_title('Attendance Trend Analysis')
        ax.set_xlabel('Date')
        ax.set_ylabel('Attendance Count')
        
        # Format x-axis dates
        if len(sorted_dates) > 10:
            # If too many dates, show every nth label
            n = max(1, len(sorted_dates) // 10)
            for i, label in enumerate(ax.get_xticklabels()):
                if i % n != 0:
                    label.set_visible(False)
        
        ax.tick_params(axis='x', rotation=45)
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Add legend
        ax.legend()
        
        # Adjust colors for theme
        if ctk.get_appearance_mode() == "Dark":
            self._apply_dark_theme(ax)

    def _apply_dark_theme(self, ax):
        """Apply dark theme to an axis"""
        ax.set_facecolor('#1e1e1e')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.grid(color='gray')

    def filter_data(self):
        """Filter data based on current selections"""
        if self.attendance_data is None or self.attendance_data.empty:
            return pd.DataFrame()
            
        try:
            # Make a copy to avoid modifying the original
            filtered_data = self.attendance_data.copy()
            
            # Convert any date columns to datetime if they're not already
            date_columns = ['date', 'Date'] 
            for col in date_columns:
                if col in filtered_data.columns:
                    if not pd.api.types.is_datetime64_any_dtype(filtered_data[col]):
                        try:
                            filtered_data[col] = pd.to_datetime(filtered_data[col])
                        except Exception as e:
                            logger.warning(f"Could not convert {col} to datetime: {e}")
            
            # Filter by course if not "All"
            if self.selected_course != "All":
                course_columns = ['course', 'Course', 'subject', 'Subject']
                course_col = None
                
                # Find the first course column that exists
                for col in course_columns:
                    if col in filtered_data.columns:
                        course_col = col
                        break
                
                if course_col:
                    filtered_data = filtered_data[filtered_data[course_col].str.contains(self.selected_course, case=False, na=False)]
            
            # Filter by time period
            date_col = None
            for col in date_columns:
                if col in filtered_data.columns:
                    date_col = col
                    break
                    
            if date_col and pd.api.types.is_datetime64_any_dtype(filtered_data[date_col]):
                now = pd.Timestamp.now()
                
                if self.time_period == "week":
                    start_date = now - pd.Timedelta(days=7)
                    filtered_data = filtered_data[filtered_data[date_col] >= start_date]
                elif self.time_period == "month":
                    start_date = now - pd.Timedelta(days=30)
                    filtered_data = filtered_data[filtered_data[date_col] >= start_date]
                elif self.time_period == "semester":
                    # Assume a semester is about 4 months
                    start_date = now - pd.Timedelta(days=120)
                    filtered_data = filtered_data[filtered_data[date_col] >= start_date]
                elif self.time_period == "year":
                    start_date = now - pd.Timedelta(days=365)
                    filtered_data = filtered_data[filtered_data[date_col] >= start_date]
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error filtering data: {e}")
            return pd.DataFrame()