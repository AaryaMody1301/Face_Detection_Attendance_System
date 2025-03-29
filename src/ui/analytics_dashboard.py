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

# Set up logging
logger = logging.getLogger(__name__)

class AnalyticsDashboard(ctk.CTkFrame):
    """Analytics Dashboard for attendance data visualization"""
    
    def __init__(self, master):
        """
        Initialize the analytics dashboard
        
        Args:
            master: Parent widget
        """
        super().__init__(master)
        
        # Initialize variables
        self.attendance_data = None
        self.selected_course = "All"
        self.time_period = "month"
        self.chart_type = "attendance_over_time"
        
        # Load data
        self.load_data()
        
        # Create UI elements
        self._setup_ui()
        
        # Load initial chart
        self.update_chart()
        
        logger.info("Analytics Dashboard initialized")
    
    def _setup_ui(self):
        """Set up the analytics UI"""
        # Configure grid layout
        self.grid_rowconfigure(2, weight=1)  # Chart area
        self.grid_columnconfigure(0, weight=1)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="Attendance Analytics",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Control panel frame
        self.control_panel = ctk.CTkFrame(self)
        self.control_panel.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="ew")
        self.control_panel.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Course selection
        self.course_label = ctk.CTkLabel(
            self.control_panel,
            text="Course:",
            font=ctk.CTkFont(size=12)
        )
        self.course_label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="e")
        
        self.courses = ["All"] + self.get_unique_courses()
        self.course_var = ctk.StringVar(value=self.selected_course)
        self.course_dropdown = ctk.CTkOptionMenu(
            self.control_panel,
            values=self.courses,
            variable=self.course_var,
            command=self._on_course_change,
            width=120
        )
        self.course_dropdown.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="w")
        
        # Time period selection
        self.period_label = ctk.CTkLabel(
            self.control_panel,
            text="Period:",
            font=ctk.CTkFont(size=12)
        )
        self.period_label.grid(row=0, column=2, padx=(10, 5), pady=10, sticky="e")
        
        self.period_var = ctk.StringVar(value=self.time_period)
        self.period_dropdown = ctk.CTkOptionMenu(
            self.control_panel,
            values=["week", "month", "semester", "year"],
            variable=self.period_var,
            command=self._on_period_change,
            width=120
        )
        self.period_dropdown.grid(row=0, column=3, padx=(0, 10), pady=10, sticky="w")
        
        # Chart type selection
        self.chart_label = ctk.CTkLabel(
            self.control_panel,
            text="Chart:",
            font=ctk.CTkFont(size=12)
        )
        self.chart_label.grid(row=1, column=0, padx=(10, 5), pady=(0, 10), sticky="e")
        
        self.chart_var = ctk.StringVar(value=self.chart_type)
        self.chart_dropdown = ctk.CTkOptionMenu(
            self.control_panel,
            values=["attendance_over_time", "student_comparison", "attendance_by_day", "attendance_heatmap"],
            variable=self.chart_var,
            command=self._on_chart_change,
            width=120
        )
        self.chart_dropdown.grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="w")
        
        # Refresh button
        self.refresh_button = ctk.CTkButton(
            self.control_panel,
            text="Refresh Data",
            command=self._on_refresh,
            width=120
        )
        self.refresh_button.grid(row=1, column=3, padx=(0, 10), pady=(0, 10), sticky="w")
        
        # Chart frame
        self.chart_frame = ctk.CTkFrame(self)
        self.chart_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.chart_frame.grid_rowconfigure(0, weight=1)
        self.chart_frame.grid_columnconfigure(0, weight=1)
        
        # Create a frame for matplotlib
        self.plot_frame = tk.Frame(self.chart_frame, bg=self.chart_frame.cget("fg_color"))
        self.plot_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Empty plot placeholder
        self.canvas = None
        self.fig = None
    
    def get_unique_courses(self):
        """Get list of unique courses from attendance data"""
        if self.attendance_data is None or self.attendance_data.empty:
            return []
        
        if 'Subject' in self.attendance_data.columns:
            return sorted(self.attendance_data['Subject'].unique().tolist())
        return []
    
    def load_data(self):
        """Load attendance data from database or CSV files"""
        try:
            # Try to load from SQLite database first
            db_path = os.path.join("Data", "attendance.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                query = "SELECT * FROM attendance"
                self.attendance_data = pd.read_sql(query, conn)
                conn.close()
                logger.info(f"Loaded {len(self.attendance_data)} attendance records from database")
                return
        except Exception as e:
            logger.warning(f"Failed to load data from database: {e}")
        
        # Fall back to CSV files
        try:
            # Load attendance data from CSV files
            attendance_dir = "Attendance"
            csv_files = []
            
            if os.path.exists(attendance_dir):
                for file in os.listdir(attendance_dir):
                    if file.endswith(".csv"):
                        csv_files.append(os.path.join(attendance_dir, file))
            
            # Also check backups
            backup_dir = os.path.join("backups", "attendance_backup")
            if os.path.exists(backup_dir):
                for file in os.listdir(backup_dir):
                    if file.endswith(".csv"):
                        csv_files.append(os.path.join(backup_dir, file))
            
            if csv_files:
                # Load and concatenate all CSV files
                dfs = []
                for file in csv_files:
                    try:
                        df = pd.read_csv(file)
                        
                        # Try to extract subject from filename
                        filename = os.path.basename(file)
                        if '_' in filename:
                            subject = filename.split('_')[0]
                            if subject not in df.columns:
                                df['Subject'] = subject
                        
                        # Try to extract date from filename
                        if 'Date' not in df.columns:
                            for date_format in [
                                r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                                r'(\d{4}_\d{2}_\d{2})',  # YYYY_MM_DD
                                r'(\d{2}-\d{2}-\d{4})',  # DD-MM-YYYY
                                r'(\d{2}_\d{2}_\d{4})',  # DD_MM_YYYY
                            ]:
                                import re
                                match = re.search(date_format, filename)
                                if match:
                                    date_str = match.group(1).replace('_', '-')
                                    df['Date'] = date_str
                                    break
                        
                        dfs.append(df)
                    except Exception as e:
                        logger.warning(f"Failed to load {file}: {e}")
                
                if dfs:
                    self.attendance_data = pd.concat(dfs, ignore_index=True)
                    logger.info(f"Loaded {len(self.attendance_data)} attendance records from {len(dfs)} CSV files")
                else:
                    # Create empty DataFrame with expected columns
                    self.attendance_data = pd.DataFrame(columns=[
                        'ID', 'Name', 'Date', 'Time', 'Status', 'Subject'
                    ])
                    logger.warning("No attendance data could be loaded")
            else:
                # Create empty DataFrame with expected columns
                self.attendance_data = pd.DataFrame(columns=[
                    'ID', 'Name', 'Date', 'Time', 'Status', 'Subject'
                ])
                logger.warning("No attendance CSV files found")
            
        except Exception as e:
            logger.error(f"Error loading attendance data: {e}")
            # Create empty DataFrame with expected columns
            self.attendance_data = pd.DataFrame(columns=[
                'ID', 'Name', 'Date', 'Time', 'Status', 'Subject'
            ])
    
    def update_chart(self):
        """Update the chart based on current selections"""
        # Clear previous chart if any
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        
        if self.fig:
            plt.close(self.fig)
        
        # Create new figure
        self.fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
        
        # Apply filters to data
        filtered_data = self.filter_data()
        
        # Render appropriate chart type
        if self.chart_type == "attendance_over_time":
            self.render_attendance_over_time(filtered_data, ax)
        elif self.chart_type == "student_comparison":
            self.render_student_comparison(filtered_data, ax)
        elif self.chart_type == "attendance_by_day":
            self.render_attendance_by_day(filtered_data, ax)
        elif self.chart_type == "attendance_heatmap":
            self.render_attendance_heatmap(filtered_data, ax)
        
        # Set chart style
        plt.tight_layout()
        
        # Create canvas and add to frame
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def filter_data(self):
        """Filter data based on selected course and time period"""
        if self.attendance_data is None or self.attendance_data.empty:
            return pd.DataFrame()
        
        data = self.attendance_data.copy()
        
        # Filter by course if not "All"
        if self.selected_course != "All" and 'Subject' in data.columns:
            data = data[data['Subject'] == self.selected_course]
        
        # Filter by time period
        if 'Date' in data.columns:
            # Convert Date column to datetime if it's not
            if not pd.api.types.is_datetime64_any_dtype(data['Date']):
                try:
                    data['Date'] = pd.to_datetime(data['Date'])
                except:
                    # If conversion fails, try to fix common format issues
                    try:
                        data['Date'] = pd.to_datetime(data['Date'], format='%Y-%m-%d')
                    except:
                        logger.warning("Failed to convert Date column to datetime")
            
            # Apply time filter
            now = datetime.now()
            if self.time_period == "week":
                start_date = now - timedelta(days=7)
                data = data[data['Date'] >= start_date]
            elif self.time_period == "month":
                start_date = now - timedelta(days=30)
                data = data[data['Date'] >= start_date]
            elif self.time_period == "semester":
                start_date = now - timedelta(days=120)  # Approx 4 months
                data = data[data['Date'] >= start_date]
            elif self.time_period == "year":
                start_date = now - timedelta(days=365)
                data = data[data['Date'] >= start_date]
        
        return data
    
    def render_attendance_over_time(self, data, ax):
        """Render attendance over time chart"""
        if data.empty or 'Date' not in data.columns:
            ax.text(0.5, 0.5, "No data available for this selection", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.set_title("Attendance Over Time")
            return
        
        # Group by date and count
        try:
            # Convert Date column to datetime if it's not
            if not pd.api.types.is_datetime64_any_dtype(data['Date']):
                data['Date'] = pd.to_datetime(data['Date'])
                
            daily_counts = data.groupby(['Date']).size().reset_index(name='Count')
            daily_counts = daily_counts.sort_values('Date')
            
            # Plot
            ax.plot(daily_counts['Date'], daily_counts['Count'], marker='o', linestyle='-')
            ax.set_title(f"Attendance Over Time - {self.selected_course}")
            ax.set_xlabel("Date")
            ax.set_ylabel("Number of Students")
            ax.tick_params(axis='x', rotation=45)
            ax.grid(True, alpha=0.3)
        except Exception as e:
            logger.error(f"Error rendering attendance over time chart: {e}")
            ax.text(0.5, 0.5, f"Error rendering chart: {str(e)}", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
    
    def render_student_comparison(self, data, ax):
        """Render student comparison chart"""
        if data.empty or 'Name' not in data.columns:
            ax.text(0.5, 0.5, "No data available for this selection", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.set_title("Student Attendance Comparison")
            return
        
        try:
            # Group by student name and count
            student_counts = data.groupby(['Name']).size().reset_index(name='Count')
            student_counts = student_counts.sort_values('Count', ascending=False).head(15)  # Top 15 students
            
            # Plot
            bars = ax.barh(student_counts['Name'], student_counts['Count'])
            ax.set_title(f"Student Attendance Comparison - {self.selected_course}")
            ax.set_xlabel("Number of Attendances")
            ax.set_ylabel("Student")
            ax.tick_params(axis='y', labelsize=8)
            
            # Add count labels
            for i, bar in enumerate(bars):
                ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2, 
                        str(int(student_counts['Count'].iloc[i])),
                        va='center')
        except Exception as e:
            logger.error(f"Error rendering student comparison chart: {e}")
            ax.text(0.5, 0.5, f"Error rendering chart: {str(e)}", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
    
    def render_attendance_by_day(self, data, ax):
        """Render attendance by day of week chart"""
        if data.empty or 'Date' not in data.columns:
            ax.text(0.5, 0.5, "No data available for this selection", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.set_title("Attendance by Day of Week")
            return
        
        try:
            # Convert to datetime and extract day of week
            if not pd.api.types.is_datetime64_any_dtype(data['Date']):
                data['Date'] = pd.to_datetime(data['Date'])
            
            data['Day'] = data['Date'].dt.day_name()
            
            # Get correct day order
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            # Group by day and count
            day_counts = data.groupby(['Day']).size().reset_index(name='Count')
            
            # Reindex to ensure all days are included and in correct order
            day_counts = day_counts.set_index('Day').reindex(days_order).fillna(0).reset_index()
            
            # Plot
            colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(day_counts)))
            bars = ax.bar(day_counts['Day'], day_counts['Count'], color=colors)
            ax.set_title(f"Attendance by Day of Week - {self.selected_course}")
            ax.set_xlabel("Day of Week")
            ax.set_ylabel("Number of Students")
            ax.tick_params(axis='x', rotation=45)
            
            # Add count labels
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f"{int(height)}",
                        ha='center', va='bottom')
        except Exception as e:
            logger.error(f"Error rendering attendance by day chart: {e}")
            ax.text(0.5, 0.5, f"Error rendering chart: {str(e)}", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
    
    def render_attendance_heatmap(self, data, ax):
        """Render attendance heatmap by date and hour"""
        if data.empty or 'Date' not in data.columns or 'Time' not in data.columns:
            ax.text(0.5, 0.5, "No data available for this selection", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.set_title("Attendance Heatmap")
            return
        
        try:
            # Convert Date column to datetime
            if not pd.api.types.is_datetime64_any_dtype(data['Date']):
                data['Date'] = pd.to_datetime(data['Date'])
            
            # Extract hour from Time column
            if 'Hour' not in data.columns:
                try:
                    # Try parsing time as string
                    data['Time'] = pd.to_datetime(data['Time']).dt.time
                    data['Hour'] = data['Time'].apply(lambda x: x.hour if x else 0)
                except:
                    # If that fails, try regex to extract hour
                    import re
                    def extract_hour(time_str):
                        if not time_str or pd.isna(time_str):
                            return 0
                        match = re.search(r'(\d+)[:\.]', str(time_str))
                        return int(match.group(1)) if match else 0
                    
                    data['Hour'] = data['Time'].apply(extract_hour)
            
            # Create hour and weekday columns
            data['Weekday'] = data['Date'].dt.day_name()
            
            # Group by weekday and hour and count
            heatmap_data = data.groupby(['Weekday', 'Hour']).size().reset_index(name='Count')
            
            # Pivot for heatmap format
            pivot_table = heatmap_data.pivot_table(values='Count', 
                                                   index='Hour',
                                                   columns='Weekday',
                                                   fill_value=0)
            
            # Reorder columns for correct weekday order
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            pivot_table = pivot_table[days_order]
            
            # Plot heatmap
            im = ax.imshow(pivot_table, cmap='viridis')
            
            # Add colorbar
            self.fig.colorbar(im, ax=ax, label="Number of Students")
            
            # Set labels
            ax.set_title(f"Attendance Heatmap - {self.selected_course}")
            ax.set_xlabel("Day of Week")
            ax.set_ylabel("Hour of Day")
            
            # Set x and y ticks
            ax.set_xticks(np.arange(len(days_order)))
            ax.set_xticklabels(days_order, rotation=45)
            ax.set_yticks(np.arange(len(pivot_table.index)))
            ax.set_yticklabels(pivot_table.index)
            
            # Loop over data dimensions and create text annotations
            for i in range(len(pivot_table.index)):
                for j in range(len(days_order)):
                    if pivot_table.iloc[i, j] > 0:
                        text = ax.text(j, i, pivot_table.iloc[i, j],
                                       ha="center", va="center", color="w", fontsize=8)
            
        except Exception as e:
            logger.error(f"Error rendering attendance heatmap: {e}")
            ax.text(0.5, 0.5, f"Error rendering chart: {str(e)}", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
    
    def _on_course_change(self, value):
        """Handle course selection change"""
        self.selected_course = value
        self.update_chart()
    
    def _on_period_change(self, value):
        """Handle time period selection change"""
        self.time_period = value
        self.update_chart()
    
    def _on_chart_change(self, value):
        """Handle chart type selection change"""
        self.chart_type = value
        self.update_chart()
    
    def _on_refresh(self):
        """Refresh data and update chart"""
        self.load_data()
        
        # Update course dropdown with potentially new courses
        current_courses = ["All"] + self.get_unique_courses()
        self.course_dropdown.configure(values=current_courses)
        
        # Update chart
        self.update_chart()
    
    def cleanup(self):
        """Clean up resources before destroying the widget"""
        if self.fig:
            plt.close(self.fig)