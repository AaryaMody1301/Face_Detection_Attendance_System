"""
Attendance Analytics Dashboard - UI for visualizing attendance data
"""
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import datetime
import os
import sys
import threading
from tkcalendar import DateEntry  # You might need to pip install tkcalendar

from src.utils.attendance_analytics import AttendanceAnalytics


class AnalyticsDashboard:
    """
    Analytics Dashboard Window for attendance visualization
    """
    
    def __init__(self, root):
        """
        Initialize the analytics dashboard
        
        Args:
            root (tk.Tk): Root window
        """
        self.root = root
        self.root.title("Attendance Analytics Dashboard")
        self.root.geometry("1200x800")
        self.root.configure(background='white')
        
        # Initialize analytics engine
        self.analytics = AttendanceAnalytics()
        
        # Selected subject and student
        self.selected_subject = tk.StringVar()
        self.selected_student = tk.StringVar()
        
        # Date range
        self.start_date = tk.StringVar()
        self.end_date = tk.StringVar()
        
        # Setup UI components
        self.setup_ui()
        
        # Load data when window is shown
        self.root.after(100, self.load_data_async)
    
    def setup_ui(self):
        """Setup the user interface components"""
        # Header with title and controls
        self.setup_header()
        
        # Setup the left panel with controls
        self.setup_control_panel()
        
        # Setup the right panel with visualization
        self.setup_visualization_panel()
        
        # Status bar
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_header(self):
        """Setup the header section with title and controls"""
        header_frame = tk.Frame(self.root, bg='#f0f0f0', height=50)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Title
        title_label = tk.Label(header_frame, text="Attendance Analytics Dashboard", 
                             font=('Helvetica', 16, 'bold'), bg='#f0f0f0')
        title_label.pack(side=tk.LEFT, padx=10)
        
        # Export button
        export_frame = tk.Frame(header_frame, bg='#f0f0f0')
        export_frame.pack(side=tk.RIGHT, padx=10)
        
        export_label = tk.Label(export_frame, text="Export as:", bg='#f0f0f0')
        export_label.pack(side=tk.LEFT, padx=5)
        
        export_csv_btn = tk.Button(export_frame, text="CSV", 
                                 command=lambda: self.export_data('csv'),
                                 bg="#4CAF50", fg="white")
        export_csv_btn.pack(side=tk.LEFT, padx=2)
        
        export_excel_btn = tk.Button(export_frame, text="Excel", 
                                   command=lambda: self.export_data('excel'),
                                   bg="#FFA000", fg="white")
        export_excel_btn.pack(side=tk.LEFT, padx=2)
        
        export_html_btn = tk.Button(export_frame, text="HTML", 
                                  command=lambda: self.export_data('html'),
                                  bg="#2196F3", fg="white")
        export_html_btn.pack(side=tk.LEFT, padx=2)
        
        # Refresh button
        refresh_btn = tk.Button(header_frame, text="Refresh Data", 
                              command=self.load_data_async,
                              bg="#673AB7", fg="white")
        refresh_btn.pack(side=tk.RIGHT, padx=10)
    
    def setup_control_panel(self):
        """Setup the control panel on the left side"""
        control_frame = tk.LabelFrame(self.root, text="Controls", 
                                     bg='#f0f0f0', font=('Helvetica', 12))
        control_frame.pack(fill=tk.X, padx=5, pady=5, ipady=5)
        
        # Subject selection
        subject_frame = tk.Frame(control_frame, bg='#f0f0f0')
        subject_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(subject_frame, text="Subject:", bg='#f0f0f0').pack(side=tk.LEFT)
        
        self.subject_combo = ttk.Combobox(subject_frame, textvariable=self.selected_subject)
        self.subject_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.subject_combo.bind("<<ComboboxSelected>>", self.on_subject_selected)
        
        # Student selection
        student_frame = tk.Frame(control_frame, bg='#f0f0f0')
        student_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(student_frame, text="Student:", bg='#f0f0f0').pack(side=tk.LEFT)
        
        self.student_combo = ttk.Combobox(student_frame, textvariable=self.selected_student)
        self.student_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.student_combo.bind("<<ComboboxSelected>>", self.on_student_selected)
        
        # Date range
        date_frame = tk.LabelFrame(control_frame, text="Date Range", bg='#f0f0f0')
        date_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Try to use tkcalendar if available, otherwise use Entry
        try:
            start_date_frame = tk.Frame(date_frame, bg='#f0f0f0')
            start_date_frame.pack(fill=tk.X, padx=5, pady=5)
            
            tk.Label(start_date_frame, text="Start:", bg='#f0f0f0').pack(side=tk.LEFT)
            self.start_date_picker = DateEntry(start_date_frame, width=12, 
                                            background='darkblue', foreground='white', 
                                            borderwidth=2, date_pattern='yyyy-mm-dd')
            self.start_date_picker.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            end_date_frame = tk.Frame(date_frame, bg='#f0f0f0')
            end_date_frame.pack(fill=tk.X, padx=5, pady=5)
            
            tk.Label(end_date_frame, text="End:", bg='#f0f0f0').pack(side=tk.LEFT)
            self.end_date_picker = DateEntry(end_date_frame, width=12,
                                          background='darkblue', foreground='white',
                                          borderwidth=2, date_pattern='yyyy-mm-dd')
            self.end_date_picker.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            # Apply button
            apply_btn = tk.Button(date_frame, text="Apply Date Filter", 
                                command=self.apply_date_filter,
                                bg="#FF5722", fg="white")
            apply_btn.pack(fill=tk.X, padx=5, pady=5)
            
        except (ImportError, ModuleNotFoundError):
            # Fallback to simple Entry widgets if tkcalendar is not available
            start_date_frame = tk.Frame(date_frame, bg='#f0f0f0')
            start_date_frame.pack(fill=tk.X, padx=5, pady=5)
            
            tk.Label(start_date_frame, text="Start (YYYY-MM-DD):", bg='#f0f0f0').pack(side=tk.LEFT)
            self.start_date_entry = tk.Entry(start_date_frame, textvariable=self.start_date)
            self.start_date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            end_date_frame = tk.Frame(date_frame, bg='#f0f0f0')
            end_date_frame.pack(fill=tk.X, padx=5, pady=5)
            
            tk.Label(end_date_frame, text="End (YYYY-MM-DD):", bg='#f0f0f0').pack(side=tk.LEFT)
            self.end_date_entry = tk.Entry(end_date_frame, textvariable=self.end_date)
            self.end_date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            # Apply button
            apply_btn = tk.Button(date_frame, text="Apply Date Filter", 
                                command=self.apply_date_filter,
                                bg="#FF5722", fg="white")
            apply_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Chart type selection
        chart_frame = tk.LabelFrame(control_frame, text="Chart Type", bg='#f0f0f0')
        chart_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Chart type buttons
        trend_btn = tk.Button(chart_frame, text="Attendance Trend", 
                            command=self.show_trend_chart,
                            bg="#2196F3", fg="white")
        trend_btn.pack(fill=tk.X, padx=5, pady=2)
        
        weekly_btn = tk.Button(chart_frame, text="Weekly Pattern", 
                             command=self.show_weekly_pattern,
                             bg="#4CAF50", fg="white")
        weekly_btn.pack(fill=tk.X, padx=5, pady=2)
        
        student_btn = tk.Button(chart_frame, text="Student Attendance", 
                              command=self.show_student_chart,
                              bg="#FFA000", fg="white")
        student_btn.pack(fill=tk.X, padx=5, pady=2)
        
        subject_btn = tk.Button(chart_frame, text="Subject Comparison", 
                              command=self.show_subject_comparison,
                              bg="#9C27B0", fg="white")
        subject_btn.pack(fill=tk.X, padx=5, pady=2)
        
        heatmap_btn = tk.Button(chart_frame, text="Attendance Heatmap", 
                              command=self.show_heatmap,
                              bg="#607D8B", fg="white")
        heatmap_btn.pack(fill=tk.X, padx=5, pady=2)
        
        # Summary section
        self.summary_frame = tk.LabelFrame(self.root, text="Summary", 
                                         bg='#f0f0f0', font=('Helvetica', 12))
        self.summary_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Will be populated when data is loaded
        self.summary_content = tk.Text(self.summary_frame, wrap=tk.WORD, bg='#f5f5f5',
                                     height=10, width=30, font=('Helvetica', 10))
        self.summary_content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.summary_content.config(state=tk.DISABLED)
    
    def setup_visualization_panel(self):
        """Setup the visualization panel on the right side"""
        # Right side - visualization area
        self.right_frame = tk.Frame(self.root, bg='white', bd=1, relief=tk.GROOVE)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Title for the visualization
        self.chart_title = tk.Label(self.right_frame, text="Attendance Visualization", 
                                  font=('Helvetica', 14, 'bold'), bg='white')
        self.chart_title.pack(padx=10, pady=10)
        
        # Frame for the chart
        self.chart_frame = tk.Frame(self.right_frame, bg='white')
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Initialize with a blank figure
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.text(0.5, 0.5, "Select data and chart type to visualize", 
                   ha='center', va='center', fontsize=12)
        self.fig.tight_layout()
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.draw()
        
        # Pack the canvas
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar
        self.toolbar_frame = tk.Frame(self.chart_frame)
        self.toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
        self.toolbar.update()
    
    def load_data_async(self):
        """Load data asynchronously to keep UI responsive"""
        self.update_status("Loading attendance data...")
        
        # Disable controls during loading
        self.disable_controls()
        
        # Create and start loading thread
        loading_thread = threading.Thread(target=self.load_data)
        loading_thread.daemon = True
        loading_thread.start()
    
    def load_data(self):
        """Load attendance data"""
        try:
            # Load the data
            success = self.analytics.load_attendance_data()
            
            # Update UI in the main thread
            self.root.after(0, self.update_ui_after_loading, success)
            
        except Exception as e:
            # Update status in main thread
            self.root.after(0, self.update_status, f"Error loading data: {e}")
            self.root.after(0, self.enable_controls)
    
    def update_ui_after_loading(self, success):
        """Update UI after data is loaded"""
        if success:
            # Populate subjects dropdown
            if hasattr(self.analytics, 'subjects') and self.analytics.subjects:
                self.subject_combo['values'] = ['All'] + list(self.analytics.subjects)
                self.subject_combo.current(0)  # Select 'All'
            
            # Populate students dropdown
            if hasattr(self.analytics, 'student_ids') and self.analytics.student_ids:
                # Get student names
                student_names = {}
                for student_id in self.analytics.student_ids:
                    student_data = self.analytics.attendance_data[
                        self.analytics.attendance_data['Enrollment'] == student_id
                    ]
                    if not student_data.empty:
                        student_name = student_data['Name'].iloc[0]
                        student_names[student_id] = f"{student_name} ({student_id})"
                
                self.student_combo['values'] = ['All'] + [student_names.get(id, id) for id in self.analytics.student_ids]
                self.student_combo.current(0)  # Select 'All'
            
            # Set date range if available
            if hasattr(self.analytics, 'date_range') and self.analytics.date_range:
                start_date = self.analytics.date_range[0]
                end_date = self.analytics.date_range[1]
                
                # Update date pickers if using tkcalendar
                if hasattr(self, 'start_date_picker') and hasattr(self, 'end_date_picker'):
                    self.start_date_picker.set_date(start_date)
                    self.end_date_picker.set_date(end_date)
                else:
                    # Update string variables for Entry widgets
                    self.start_date.set(start_date.strftime('%Y-%m-%d'))
                    self.end_date.set(end_date.strftime('%Y-%m-%d'))
            
            # Show default visualization
            self.show_trend_chart()
            
            # Update status
            self.update_status("Data loaded successfully")
        else:
            # Show error message
            messagebox.showerror("Loading Error", 
                               "Failed to load attendance data. Please check the data files.")
            self.update_status("Failed to load data")
        
        # Re-enable controls
        self.enable_controls()
    
    def update_summary(self):
        """Update the summary panel with statistics"""
        # Get subject filter
        subject = None if self.selected_subject.get() == 'All' else self.selected_subject.get()
        
        # Get date range
        start_date = None
        end_date = None
        
        if hasattr(self, 'start_date_picker'):
            start_date = self.start_date_picker.get_date()
            end_date = self.end_date_picker.get_date()
        elif self.start_date.get() and self.end_date.get():
            try:
                start_date = self.start_date.get()
                end_date = self.end_date.get()
            except:
                pass
        
        # Get summary statistics
        summary = self.analytics.get_attendance_summary(subject, start_date, end_date)
        
        if not summary:
            summary_text = "No data available for the selected filters."
        else:
            subject_text = f"Subject: {subject}" if subject else "All Subjects"
            date_range_text = "Date Range: "
            
            if summary.get('date_range'):
                date_range_text += f"{summary['date_range'][0].strftime('%Y-%m-%d')} to {summary['date_range'][1].strftime('%Y-%m-%d')}"
            else:
                date_range_text += "All dates"
            
            top_attendees_text = "Top Attendees:\n"
            for attendee in summary.get('top_attendees', []):
                top_attendees_text += f"- {attendee['name']} ({attendee['id']}): {attendee['count']} days\n"
            
            # Build the full summary text
            summary_text = f"{subject_text}\n\n" \
                         f"Total Students: {summary.get('total_students', 0)}\n" \
                         f"Total Records: {summary.get('total_records', 0)}\n" \
                         f"Average Attendance: {summary.get('avg_attendance', 0)}\n\n" \
                         f"{date_range_text}\n\n" \
                         f"{top_attendees_text}"
        
        # Update the summary text widget
        self.summary_content.config(state=tk.NORMAL)
        self.summary_content.delete(1.0, tk.END)
        self.summary_content.insert(tk.END, summary_text)
        self.summary_content.config(state=tk.DISABLED)
    
    def on_subject_selected(self, event=None):
        """Handle subject selection change"""
        self.update_summary()
        
        # Update visualization based on current chart type
        current_title = self.chart_title.cget("text").lower()
        
        if "trend" in current_title:
            self.show_trend_chart()
        elif "weekly" in current_title:
            self.show_weekly_pattern()
        elif "student" in current_title:
            self.show_student_chart()
        elif "subject" in current_title:
            self.show_subject_comparison()
        elif "heatmap" in current_title:
            self.show_heatmap()
    
    def on_student_selected(self, event=None):
        """Handle student selection change"""
        # If a student is selected, show their attendance
        if self.selected_student.get() and self.selected_student.get() != 'All':
            self.show_student_chart()
    
    def apply_date_filter(self):
        """Apply date filter to the visualization"""
        self.update_summary()
        self.on_subject_selected()  # Reapply the current chart with new date filter
    
    def show_trend_chart(self):
        """Show attendance trend chart"""
        self.update_status("Generating attendance trend chart...")
        
        # Get subject filter
        subject = None if self.selected_subject.get() == 'All' else self.selected_subject.get()
        
        # Update chart title
        title_text = f"Attendance Trend - {subject}" if subject else "Attendance Trend - All Subjects"
        self.chart_title.config(text=title_text)
        
        # Generate the chart
        self.analytics.create_attendance_trend_plot(subject, self.canvas)
        
        # Update summary
        self.update_summary()
        
        self.update_status("Attendance trend chart generated")
    
    def show_weekly_pattern(self):
        """Show weekly attendance pattern chart"""
        self.update_status("Generating weekly pattern chart...")
        
        # Get subject filter
        subject = None if self.selected_subject.get() == 'All' else self.selected_subject.get()
        
        # Update chart title
        title_text = f"Weekly Pattern - {subject}" if subject else "Weekly Pattern - All Subjects"
        self.chart_title.config(text=title_text)
        
        # Generate the chart
        self.analytics.create_weekly_pattern_plot(subject, self.canvas)
        
        # Update summary
        self.update_summary()
        
        self.update_status("Weekly pattern chart generated")
    
    def show_student_chart(self):
        """Show student attendance chart"""
        self.update_status("Generating student attendance chart...")
        
        # Get student ID
        student_selection = self.selected_student.get()
        
        if student_selection == 'All':
            messagebox.showinfo("Selection Required", "Please select a specific student")
            self.update_status("No student selected")
            return
        
        # Extract student ID from the selection (format: "Name (ID)")
        import re
        match = re.search(r"\((.+?)\)$", student_selection)
        student_id = match.group(1) if match else student_selection
        
        # Update chart title
        self.chart_title.config(text=f"Student Attendance - {student_selection}")
        
        # Generate the chart
        self.analytics.create_student_attendance_plot(student_id, self.canvas)
        
        self.update_status("Student attendance chart generated")
    
    def show_subject_comparison(self):
        """Show subject comparison chart"""
        self.update_status("Generating subject comparison chart...")
        
        # Update chart title
        self.chart_title.config(text="Subject Comparison")
        
        # Generate the chart
        self.analytics.create_subject_comparison_plot(self.canvas)
        
        self.update_status("Subject comparison chart generated")
    
    def show_heatmap(self):
        """Show attendance heatmap"""
        self.update_status("Generating attendance heatmap...")
        
        # Get subject filter
        subject = None if self.selected_subject.get() == 'All' else self.selected_subject.get()
        
        # Update chart title
        title_text = f"Attendance Heatmap - {subject}" if subject else "Attendance Heatmap - All Subjects"
        self.chart_title.config(text=title_text)
        
        # Generate the chart
        self.analytics.create_attendance_heatmap(subject, self.canvas)
        
        self.update_status("Attendance heatmap generated")
    
    def export_data(self, format_type):
        """Export attendance data to the specified format"""
        # Get subject filter
        subject = None if self.selected_subject.get() == 'All' else self.selected_subject.get()
        
        self.update_status(f"Exporting data to {format_type}...")
        
        # Export the data
        export_path = self.analytics.export_attendance_report(subject, format_type)
        
        if export_path:
            messagebox.showinfo("Export Successful", 
                             f"Data exported successfully to:\n{export_path}")
            self.update_status(f"Data exported to {format_type}")
        else:
            messagebox.showerror("Export Failed", 
                               "Failed to export data. Please check the console for details.")
            self.update_status("Export failed")
    
    def update_status(self, message):
        """Update the status bar message"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()
    
    def disable_controls(self):
        """Disable UI controls during data loading"""
        for widget in self.root.winfo_children():
            self._set_widget_state(widget, tk.DISABLED)
    
    def enable_controls(self):
        """Enable UI controls after data loading"""
        for widget in self.root.winfo_children():
            self._set_widget_state(widget, tk.NORMAL)
    
    def _set_widget_state(self, widget, state):
        """Recursively set the state of a widget and its children"""
        if widget.winfo_children:
            for child in widget.winfo_children():
                self._set_widget_state(child, state)
        
        # Only set state for widgets that support it
        if hasattr(widget, 'state') and callable(getattr(widget, 'state')):
            try:
                widget.state(['!disabled' if state == tk.NORMAL else 'disabled'])
            except:
                pass
        elif hasattr(widget, 'config') and callable(getattr(widget, 'config')):
            try:
                widget.config(state=state)
            except:
                pass
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Main function to run the analytics dashboard standalone"""
    root = tk.Tk()
    app = AnalyticsDashboard(root)
    app.run()


if __name__ == "__main__":
    main()