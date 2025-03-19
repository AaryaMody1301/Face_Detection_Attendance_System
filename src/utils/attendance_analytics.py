"""
Attendance Analytics Module - Provides data visualization and analytics for attendance records
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy import stats
import seaborn as sns
from typing import Dict, List, Optional, Any, Tuple
import json
import plotly.graph_objects as go
import plotly.express as px
from .data_cache import DataCache
from .user_preferences import UserPreferences

class AttendanceAnalytics:
    """Class for analyzing and visualizing attendance data"""
    
    def __init__(self, attendance_dir="Attendance"):
        """
        Initialize the analytics module
        
        Args:
            attendance_dir (str): Path to the attendance directory
        """
        self.attendance_dir = attendance_dir
        self.attendance_data = None
        self.subjects = []
        self.student_ids = []
        self.date_range = []
        self.cache = DataCache()
        self.preferences = UserPreferences()
    
    def load_attendance_data(self, force_refresh=False):
        """
        Load all attendance data from CSV files with caching
        
        Args:
            force_refresh (bool): Force refresh of cached data
            
        Returns:
            bool: True if data was loaded successfully, False otherwise
        """
        # Try to get from cache first
        if not force_refresh:
            cached_data = self.cache.get('attendance_data', {})
            if cached_data is not None:
                self.attendance_data = cached_data
                self._update_metadata()
                return True
        
        # If not in cache or force refresh, load from files
        if not os.path.isdir(self.attendance_dir):
            print(f"Attendance directory not found: {self.attendance_dir}")
            return False
        
        all_data = []
        subject_directories = [d for d in os.listdir(self.attendance_dir) 
                              if os.path.isdir(os.path.join(self.attendance_dir, d)) and 
                              d not in ["Backup", "Exports", "Duplicates"]]
        
        # Process regular attendance files in main directory
        csv_files = [f for f in os.listdir(self.attendance_dir) 
                    if os.path.isfile(os.path.join(self.attendance_dir, f)) and 
                    f.lower().endswith('.csv')]
        
        for file in csv_files:
            try:
                file_path = os.path.join(self.attendance_dir, file)
                df = pd.read_csv(file_path)
                
                # Extract subject from filename
                subject = self._extract_subject_from_filename(file)
                df['Subject'] = subject
                
                all_data.append(df)
            except Exception as e:
                print(f"Error reading {file}: {e}")
        
        # Process subject directories
        for subject_dir in subject_directories:
            dir_path = os.path.join(self.attendance_dir, subject_dir)
            subject_files = [f for f in os.listdir(dir_path)
                           if os.path.isfile(os.path.join(dir_path, f)) and
                           f.lower().endswith('.csv')]
            
            for file in subject_files:
                try:
                    file_path = os.path.join(dir_path, file)
                    df = pd.read_csv(file_path)
                    
                    # Set subject from directory name if not in filename
                    if 'Subject' not in df.columns:
                        df['Subject'] = subject_dir
                    
                    all_data.append(df)
                except Exception as e:
                    print(f"Error reading {subject_dir}/{file}: {e}")
        
        # Also check Exports directory for consolidated files
        exports_dir = os.path.join(self.attendance_dir, "Exports")
        if os.path.isdir(exports_dir):
            export_files = [f for f in os.listdir(exports_dir)
                          if os.path.isfile(os.path.join(exports_dir, f)) and
                          f.lower().endswith('.csv')]
            
            for file in export_files:
                try:
                    file_path = os.path.join(exports_dir, file)
                    df = pd.read_csv(file_path)
                    
                    # Extract subject from filename
                    subject = self._extract_subject_from_filename(file)
                    if 'Subject' not in df.columns:
                        df['Subject'] = subject
                    
                    all_data.append(df)
                except Exception as e:
                    print(f"Error reading {exports_dir}/{file}: {e}")
        
        if not all_data:
            print("No attendance data found")
            return False
        
        # Combine all data
        self.attendance_data = pd.concat(all_data, ignore_index=True)
        
        # Ensure required columns exist
        required_columns = ['Enrollment', 'Name', 'Date', 'Time']
        for col in required_columns:
            if col not in self.attendance_data.columns:
                print(f"Required column missing: {col}")
                return False
        
        # Convert date to datetime
        try:
            self.attendance_data['Date'] = pd.to_datetime(self.attendance_data['Date'])
        except Exception as e:
            print(f"Error converting dates: {e}")
            # Try with different format
            try:
                self.attendance_data['Date'] = pd.to_datetime(self.attendance_data['Date'], 
                                                           format='%Y-%m-%d')
            except:
                print("Could not convert dates to datetime format")
        
        # Update metadata
        self._update_metadata()
        
        # Cache the data
        self.cache.set('attendance_data', {}, self.attendance_data)
        
        return True
    
    def _update_metadata(self):
        """Update metadata from attendance data"""
        if self.attendance_data is not None:
            if 'Subject' in self.attendance_data.columns:
                self.subjects = sorted(self.attendance_data['Subject'].unique())
            self.student_ids = sorted(self.attendance_data['Enrollment'].unique())
            if pd.api.types.is_datetime64_dtype(self.attendance_data['Date']):
                self.date_range = [
                    self.attendance_data['Date'].min(),
                    self.attendance_data['Date'].max()
                ]
    
    def _extract_subject_from_filename(self, filename):
        """
        Extract subject name from attendance filename
        
        Args:
            filename (str): Attendance file name
            
        Returns:
            str: Extracted subject name or 'Unknown'
        """
        # Try to extract subject from filename
        parts = filename.split('_')
        
        if filename.startswith('Attendance'):
            # Format: Attendance{Subject}_{date}_Time_{time}.csv
            subject = filename.split('Attendance')[-1].split('_')[0]
            return subject if subject else 'Unknown'
        
        if filename.startswith('Manually Attendance'):
            # Format: Manually Attendance{Subject}_{date}_Time_{time}.csv
            subject = filename.split('Manually Attendance')[-1].split('_')[0]
            return subject if subject else 'Unknown'
        
        if 'Consolidated' in filename:
            # Format: {Subject}_Consolidated_{date}.csv
            subject = filename.split('_Consolidated_')[0]
            return subject if subject else 'Unknown'
        
        return 'Unknown'
    
    def get_attendance_by_subject(self, subject=None):
        """
        Get attendance data filtered by subject
        
        Args:
            subject (str, optional): Subject to filter by
            
        Returns:
            pd.DataFrame: Filtered attendance data
        """
        if self.attendance_data is None:
            self.load_attendance_data()
            
        if self.attendance_data is None:
            return pd.DataFrame()
            
        if subject and 'Subject' in self.attendance_data.columns:
            return self.attendance_data[self.attendance_data['Subject'] == subject]
        
        return self.attendance_data
    
    def get_attendance_summary(self, subject=None, start_date=None, end_date=None):
        """
        Generate attendance summary statistics
        
        Args:
            subject (str, optional): Subject to filter by
            start_date (str, optional): Start date for filtering
            end_date (str, optional): End date for filtering
            
        Returns:
            dict: Summary statistics
        """
        # Get filtered data
        data = self.get_attendance_by_subject(subject)
        
        if data.empty:
            return {}
            
        # Apply date filters if provided
        if start_date:
            start_date = pd.to_datetime(start_date)
            data = data[data['Date'] >= start_date]
            
        if end_date:
            end_date = pd.to_datetime(end_date)
            data = data[data['Date'] <= end_date]
        
        # Count unique students
        total_students = len(data['Enrollment'].unique())
        
        # Count attendance by date
        attendance_by_date = data.groupby('Date').size().reset_index(name='Count')
        
        # Calculate average attendance
        avg_attendance = attendance_by_date['Count'].mean() if not attendance_by_date.empty else 0
        
        # Get most recent date
        most_recent = data['Date'].max() if not data.empty else None
        
        # Count by student to find frequent and infrequent attendees
        attendance_by_student = data.groupby('Enrollment').size().reset_index(name='Count')
        attendance_by_student = attendance_by_student.sort_values('Count', ascending=False)
        
        top_attendees = []
        if not attendance_by_student.empty:
            # Get top 5 attendees
            top_5 = attendance_by_student.head(5)
            for _, row in top_5.iterrows():
                student_name = data[data['Enrollment'] == row['Enrollment']]['Name'].iloc[0]
                top_attendees.append({
                    'id': row['Enrollment'],
                    'name': student_name,
                    'count': row['Count']
                })
        
        # Summary dictionary
        summary = {
            'total_students': total_students,
            'total_records': len(data),
            'avg_attendance': round(avg_attendance, 2),
            'most_recent': most_recent,
            'top_attendees': top_attendees,
            'date_range': [data['Date'].min(), data['Date'].max()] if not data.empty else None
        }
        
        return summary
    
    def create_attendance_trend_plot(self, subject=None, canvas=None):
        """
        Create attendance trend plot over time
        
        Args:
            subject (str, optional): Subject to filter by
            canvas (FigureCanvasTkAgg, optional): Canvas to draw on
            
        Returns:
            matplotlib.figure.Figure: Created figure
        """
        # Get filtered data
        data = self.get_attendance_by_subject(subject)
        
        if data.empty:
            fig = Figure(figsize=(8, 4))
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No attendance data available", 
                   ha='center', va='center', fontsize=12)
            ax.set_xlabel("Date")
            ax.set_ylabel("Number of Students")
            ax.set_title("Attendance Trend")
            fig.tight_layout()
            
            if canvas:
                canvas.figure = fig
                canvas.draw()
            
            return fig
        
        # Count attendance by date
        attendance_by_date = data.groupby('Date').size().reset_index(name='Count')
        attendance_by_date = attendance_by_date.sort_values('Date')
        
        # Create a full date range to show gaps
        if len(attendance_by_date) > 1:
            full_date_range = pd.date_range(
                start=attendance_by_date['Date'].min(),
                end=attendance_by_date['Date'].max()
            )
            
            # Create a new dataframe with all dates
            full_df = pd.DataFrame({'Date': full_date_range})
            
            # Merge with attendance counts
            attendance_by_date = pd.merge(
                full_df, attendance_by_date, on='Date', how='left'
            ).fillna(0)
        
        fig = Figure(figsize=(8, 4))
        ax = fig.add_subplot(111)
        
        # Plot the attendance trend
        ax.plot(attendance_by_date['Date'], attendance_by_date['Count'], 
              marker='o', linestyle='-', color='#1976D2', linewidth=2, markersize=6)
        
        # Add title and labels
        title = f"Attendance Trend for {subject}" if subject else "Attendance Trend"
        ax.set_title(title, fontsize=14)
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Number of Students", fontsize=12)
        
        # Format the x-axis date labels
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        if len(attendance_by_date) > 10:
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        fig.autofmt_xdate()  # Rotate date labels
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Add average line
        avg = attendance_by_date['Count'].mean()
        ax.axhline(y=avg, color='#F44336', linestyle='--', alpha=0.8)
        ax.text(attendance_by_date['Date'].iloc[-3], avg + 0.5, 
              f'Average: {avg:.1f}', color='#F44336')
        
        fig.tight_layout()
        
        if canvas:
            canvas.figure = fig
            canvas.draw()
        
        return fig
    
    def create_student_attendance_plot(self, student_id=None, canvas=None):
        """
        Create attendance plot for a specific student
        
        Args:
            student_id (str): Student ID to filter by
            canvas (FigureCanvasTkAgg, optional): Canvas to draw on
            
        Returns:
            matplotlib.figure.Figure: Created figure
        """
        if self.attendance_data is None:
            self.load_attendance_data()
            
        if self.attendance_data is None or student_id is None:
            fig = Figure(figsize=(8, 4))
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No student data available", 
                   ha='center', va='center', fontsize=12)
            fig.tight_layout()
            
            if canvas:
                canvas.figure = fig
                canvas.draw()
            
            return fig
        
        # Filter by student ID
        student_data = self.attendance_data[self.attendance_data['Enrollment'] == student_id]
        
        if student_data.empty:
            fig = Figure(figsize=(8, 4))
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"No attendance data for student ID: {student_id}", 
                   ha='center', va='center', fontsize=12)
            fig.tight_layout()
            
            if canvas:
                canvas.figure = fig
                canvas.draw()
            
            return fig
        
        # Get student name
        student_name = student_data['Name'].iloc[0]
        
        # Group by subject and date
        if 'Subject' in student_data.columns:
            subject_attendance = student_data.groupby(['Subject', 'Date']).size().reset_index(name='Count')
            
            fig = Figure(figsize=(8, 4))
            ax = fig.add_subplot(111)
            
            # Get unique subjects
            subjects = sorted(subject_attendance['Subject'].unique())
            
            # Plot attendance for each subject
            for i, subject in enumerate(subjects):
                subject_data = subject_attendance[subject_attendance['Subject'] == subject]
                ax.plot(subject_data['Date'], subject_data['Count'], 
                      marker='o', linestyle='-', label=subject, 
                      color=plt.cm.tab10(i % 10))
            
            # Add legend
            ax.legend()
            
            # Add title and labels
            ax.set_title(f"Attendance for {student_name} ({student_id})", fontsize=14)
            ax.set_xlabel("Date", fontsize=12)
            ax.set_ylabel("Attendance Count", fontsize=12)
            
            # Format the x-axis date labels
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig.autofmt_xdate()  # Rotate date labels
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
        else:
            # If no subject information, just plot attendance dates
            attendance_dates = student_data['Date'].value_counts().sort_index()
            
            fig = Figure(figsize=(8, 4))
            ax = fig.add_subplot(111)
            
            ax.bar(attendance_dates.index, attendance_dates.values, color='#1976D2')
            
            # Add title and labels
            ax.set_title(f"Attendance for {student_name} ({student_id})", fontsize=14)
            ax.set_xlabel("Date", fontsize=12)
            ax.set_ylabel("Attendance Count", fontsize=12)
            
            # Format the x-axis date labels
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig.autofmt_xdate()  # Rotate date labels
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
        
        fig.tight_layout()
        
        if canvas:
            canvas.figure = fig
            canvas.draw()
        
        return fig
    
    def create_subject_comparison_plot(self, canvas=None):
        """
        Create a comparison plot of attendance across different subjects
        
        Args:
            canvas (FigureCanvasTkAgg, optional): Canvas to draw on
            
        Returns:
            matplotlib.figure.Figure: Created figure
        """
        if self.attendance_data is None:
            self.load_attendance_data()
            
        if self.attendance_data is None or 'Subject' not in self.attendance_data.columns:
            fig = Figure(figsize=(8, 4))
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No subject data available", 
                   ha='center', va='center', fontsize=12)
            fig.tight_layout()
            
            if canvas:
                canvas.figure = fig
                canvas.draw()
            
            return fig
        
        # Group by subject
        subject_stats = self.attendance_data.groupby('Subject').agg({
            'Enrollment': pd.Series.nunique,
            'Date': pd.Series.nunique
        }).reset_index()
        
        subject_stats.columns = ['Subject', 'Unique Students', 'Days with Attendance']
        
        # Sort by number of students
        subject_stats = subject_stats.sort_values('Unique Students', ascending=False)
        
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        # Plotting
        x = np.arange(len(subject_stats))
        width = 0.35
        
        ax.bar(x - width/2, subject_stats['Unique Students'], width, 
              label='Unique Students', color='#1976D2')
        ax.bar(x + width/2, subject_stats['Days with Attendance'], width,
              label='Days with Attendance', color='#FFA000')
        
        # Add labels and title
        ax.set_xlabel('Subject', fontsize=12)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_title('Attendance Statistics by Subject', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(subject_stats['Subject'], rotation=45, ha='right')
        
        # Add legend
        ax.legend()
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.3, axis='y')
        
        # Add value labels on top of bars
        for i, v in enumerate(subject_stats['Unique Students']):
            ax.text(i - width/2, v + 0.1, str(v), ha='center', fontsize=9)
            
        for i, v in enumerate(subject_stats['Days with Attendance']):
            ax.text(i + width/2, v + 0.1, str(v), ha='center', fontsize=9)
        
        fig.tight_layout()
        
        if canvas:
            canvas.figure = fig
            canvas.draw()
        
        return fig
    
    def create_weekly_pattern_plot(self, subject=None, canvas=None):
        """
        Create a plot showing attendance patterns by day of week
        
        Args:
            subject (str, optional): Subject to filter by
            canvas (FigureCanvasTkAgg, optional): Canvas to draw on
            
        Returns:
            matplotlib.figure.Figure: Created figure
        """
        # Get filtered data
        data = self.get_attendance_by_subject(subject)
        
        if data.empty or not pd.api.types.is_datetime64_dtype(data['Date']):
            fig = Figure(figsize=(8, 4))
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No valid attendance data available", 
                   ha='center', va='center', fontsize=12)
            fig.tight_layout()
            
            if canvas:
                canvas.figure = fig
                canvas.draw()
            
            return fig
        
        # Extract day of week
        data['Day of Week'] = data['Date'].dt.day_name()
        
        # Order days properly
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Group by day of week
        attendance_by_dow = data.groupby('Day of Week').size().reset_index(name='Count')
        
        # Reindex to ensure all days are included
        day_dict = {day: i for i, day in enumerate(day_order)}
        attendance_by_dow['Day_Num'] = attendance_by_dow['Day of Week'].map(day_dict)
        attendance_by_dow = attendance_by_dow.sort_values('Day_Num')
        
        fig = Figure(figsize=(8, 4))
        ax = fig.add_subplot(111)
        
        # Create bar chart
        bars = ax.bar(attendance_by_dow['Day of Week'], attendance_by_dow['Count'], 
                     color='#4CAF50')
        
        # Add title and labels
        title = f"Weekly Attendance Pattern for {subject}" if subject else "Weekly Attendance Pattern"
        ax.set_title(title, fontsize=14)
        ax.set_xlabel("Day of Week", fontsize=12)
        ax.set_ylabel("Total Attendance", fontsize=12)
        
        # Format the x-axis to show all days in correct order
        ax.set_xticks(range(len(day_order)))
        ax.set_xticklabels(day_order)
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.3, axis='y')
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                  f'{height:.0f}', ha='center', va='bottom')
        
        fig.tight_layout()
        
        if canvas:
            canvas.figure = fig
            canvas.draw()
        
        return fig
    
    def create_attendance_heatmap(self, subject=None, canvas=None):
        """
        Create a heatmap of attendance over calendar days
        
        Args:
            subject (str, optional): Subject to filter by
            canvas (FigureCanvasTkAgg, optional): Canvas to draw on
            
        Returns:
            matplotlib.figure.Figure: Created figure
        """
        # Get filtered data
        data = self.get_attendance_by_subject(subject)
        
        if data.empty or not pd.api.types.is_datetime64_dtype(data['Date']):
            fig = Figure(figsize=(10, 6))
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No valid attendance data available", 
                   ha='center', va='center', fontsize=12)
            fig.tight_layout()
            
            if canvas:
                canvas.figure = fig
                canvas.draw()
            
            return fig
        
        # Extract month and day
        data['Month'] = data['Date'].dt.month_name()
        data['Day'] = data['Date'].dt.day
        
        # Group by month and day
        attendance_by_day = data.groupby(['Month', 'Day']).size().reset_index(name='Count')
        
        # Create a pivot table for the heatmap
        if not attendance_by_day.empty:
            pivot = attendance_by_day.pivot(index='Month', columns='Day', values='Count')
            
            # Ensure month order is correct
            month_order = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]
            pivot = pivot.reindex(month_order)
            
            # Create the figure
            fig = Figure(figsize=(12, 6))
            ax = fig.add_subplot(111)
            
            # Create heatmap
            im = ax.imshow(pivot, cmap='YlGnBu')
            
            # Set x and y labels
            ax.set_xticks(np.arange(pivot.shape[1]))
            ax.set_xticklabels(pivot.columns)
            ax.set_yticks(np.arange(pivot.shape[0]))
            ax.set_yticklabels(pivot.index)
            
            # Rotate x labels for better readability
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right',
                   rotation_mode='anchor')
            
            # Add colorbar
            cbar = fig.colorbar(im, ax=ax)
            cbar.set_label('Attendance Count')
            
            # Add title
            title = f"Attendance Heatmap for {subject}" if subject else "Attendance Heatmap"
            ax.set_title(title, fontsize=14)
            
            fig.tight_layout()
            
        else:
            fig = Figure(figsize=(10, 6))
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "Insufficient data for heatmap", 
                   ha='center', va='center', fontsize=12)
            fig.tight_layout()
        
        if canvas:
            canvas.figure = fig
            canvas.draw()
        
        return fig

    def create_bubble_chart(self, subject=None, canvas=None):
        """
        Create a bubble chart showing attendance vs student performance
        
        Args:
            subject (str, optional): Subject to filter by
            canvas (FigureCanvasTkAgg, optional): Canvas to draw on
            
        Returns:
            matplotlib.figure.Figure: Created figure
        """
        # Get filtered data
        data = self.get_attendance_by_subject(subject)
        
        if data.empty:
            fig = Figure(figsize=(10, 6))
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No attendance data available", 
                   ha='center', va='center', fontsize=12)
            fig.tight_layout()
            
            if canvas:
                canvas.figure = fig
                canvas.draw()
            
            return fig
        
        # Calculate attendance rate per student
        student_stats = data.groupby('Enrollment').agg({
            'Date': 'count',
            'Name': 'first'
        }).reset_index()
        
        # Calculate average attendance
        avg_attendance = student_stats['Date'].mean()
        
        # Create bubble chart
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        # Plot bubbles
        for _, row in student_stats.iterrows():
            size = row['Date'] / avg_attendance * 100
            ax.scatter(row['Enrollment'], row['Date'], 
                      s=size, alpha=0.6, 
                      label=row['Name'])
        
        # Add title and labels
        title = f"Student Attendance Distribution for {subject}" if subject else "Student Attendance Distribution"
        ax.set_title(title, fontsize=14)
        ax.set_xlabel("Student ID", fontsize=12)
        ax.set_ylabel("Total Attendance", fontsize=12)
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.3)
        
        # Add legend
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, bbox_to_anchor=(1.05, 1), loc='upper left')
        
        fig.tight_layout()
        
        if canvas:
            canvas.figure = fig
            canvas.draw()
        
        return fig
    
    def create_radar_chart(self, student_id=None, canvas=None):
        """
        Create a radar chart showing student attendance patterns
        
        Args:
            student_id (str): Student ID to filter by
            canvas (FigureCanvasTkAgg, optional): Canvas to draw on
            
        Returns:
            matplotlib.figure.Figure: Created figure
        """
        if self.attendance_data is None or student_id is None:
            fig = Figure(figsize=(8, 8))
            ax = fig.add_subplot(111, projection='polar')
            ax.text(0.5, 0.5, "No student data available", 
                   ha='center', va='center', fontsize=12)
            fig.tight_layout()
            
            if canvas:
                canvas.figure = fig
                canvas.draw()
            
            return fig
        
        # Filter by student ID
        student_data = self.attendance_data[self.attendance_data['Enrollment'] == student_id]
        
        if student_data.empty:
            fig = Figure(figsize=(8, 8))
            ax = fig.add_subplot(111, projection='polar')
            ax.text(0.5, 0.5, f"No attendance data for student ID: {student_id}", 
                   ha='center', va='center', fontsize=12)
            fig.tight_layout()
            
            if canvas:
                canvas.figure = fig
                canvas.draw()
            
            return fig
        
        # Get student name
        student_name = student_data['Name'].iloc[0]
        
        # Calculate attendance by day of week
        student_data['Day of Week'] = student_data['Date'].dt.day_name()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        attendance_by_dow = student_data.groupby('Day of Week').size()
        attendance_by_dow = attendance_by_dow.reindex(day_order).fillna(0)
        
        # Create radar chart
        fig = Figure(figsize=(8, 8))
        ax = fig.add_subplot(111, projection='polar')
        
        # Calculate angles for each day
        angles = np.linspace(0, 2*np.pi, len(day_order), endpoint=False)
        
        # Close the plot by appending first value
        values = attendance_by_dow.values
        values = np.concatenate((values, [values[0]]))
        angles = np.concatenate((angles, [angles[0]]))
        
        # Plot the radar chart
        ax.plot(angles, values, 'o-', linewidth=2, label='Attendance')
        ax.fill(angles, values, alpha=0.25)
        
        # Set the labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(day_order)
        
        # Add title
        ax.set_title(f"Attendance Pattern for {student_name}", pad=20)
        
        fig.tight_layout()
        
        if canvas:
            canvas.figure = fig
            canvas.draw()
        
        return fig
    
    def create_box_plot(self, subject=None, canvas=None):
        """
        Create a box plot showing attendance distribution
        
        Args:
            subject (str, optional): Subject to filter by
            canvas (FigureCanvasTkAgg, optional): Canvas to draw on
            
        Returns:
            matplotlib.figure.Figure: Created figure
        """
        # Get filtered data
        data = self.get_attendance_by_subject(subject)
        
        if data.empty:
            fig = Figure(figsize=(8, 6))
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No attendance data available", 
                   ha='center', va='center', fontsize=12)
            fig.tight_layout()
            
            if canvas:
                canvas.figure = fig
                canvas.draw()
            
            return fig
        
        # Calculate attendance by student
        student_attendance = data.groupby('Enrollment').size().reset_index(name='Count')
        
        # Create box plot
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        
        # Create box plot
        bp = ax.boxplot(student_attendance['Count'])
        
        # Add title and labels
        title = f"Attendance Distribution for {subject}" if subject else "Attendance Distribution"
        ax.set_title(title, fontsize=14)
        ax.set_ylabel("Number of Attendance Records", fontsize=12)
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.3)
        
        # Add statistics
        stats_text = f"Mean: {student_attendance['Count'].mean():.1f}\n"
        stats_text += f"Median: {student_attendance['Count'].median():.1f}\n"
        stats_text += f"Std Dev: {student_attendance['Count'].std():.1f}"
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                verticalalignment='top', fontsize=10)
        
        fig.tight_layout()
        
        if canvas:
            canvas.figure = fig
            canvas.draw()
        
        return fig
    
    def create_sunburst_chart(self, subject=None, canvas=None):
        """
        Create an interactive sunburst chart showing attendance hierarchy
        
        Args:
            subject (str, optional): Subject to filter by
            canvas (FigureCanvasTkAgg, optional): Canvas to draw on
            
        Returns:
            plotly.graph_objects.Figure: Created figure
        """
        # Get filtered data
        data = self.get_attendance_by_subject(subject)
        
        if data.empty:
            fig = go.Figure()
            fig.add_annotation(text="No attendance data available",
                            xref="paper", yref="paper",
                            x=0.5, y=0.5,
                            showarrow=False)
            return fig
        
        # Prepare data for sunburst chart
        data['Month'] = data['Date'].dt.strftime('%B')
        data['Day'] = data['Date'].dt.day
        
        # Create hierarchy
        hierarchy = {
            'ids': [],
            'labels': [],
            'parents': [],
            'values': []
        }
        
        # Add root
        hierarchy['ids'].append('root')
        hierarchy['labels'].append('Total')
        hierarchy['parents'].append('')
        hierarchy['values'].append(len(data))
        
        # Add months
        for month in data['Month'].unique():
            month_data = data[data['Month'] == month]
            hierarchy['ids'].append(month)
            hierarchy['labels'].append(month)
            hierarchy['parents'].append('root')
            hierarchy['values'].append(len(month_data))
            
            # Add days
            for day in month_data['Day'].unique():
                day_data = month_data[month_data['Day'] == day]
                day_id = f"{month}-{day}"
                hierarchy['ids'].append(day_id)
                hierarchy['labels'].append(f"Day {day}")
                hierarchy['parents'].append(month)
                hierarchy['values'].append(len(day_data))
        
        # Create sunburst chart
        fig = go.Figure(go.Sunburst(
            ids=hierarchy['ids'],
            labels=hierarchy['labels'],
            parents=hierarchy['parents'],
            values=hierarchy['values'],
            branchvalues="total",
            hovertemplate="<b>%{label}</b><br>" +
                         "Attendance: %{value}<br>" +
                         "<extra></extra>"
        ))
        
        # Update layout
        title = f"Attendance Hierarchy for {subject}" if subject else "Attendance Hierarchy"
        fig.update_layout(
            title=title,
            width=800,
            height=600
        )
        
        return fig
    
    def perform_statistical_analysis(self, subject=None):
        """
        Perform statistical analysis on attendance data
        
        Args:
            subject (str, optional): Subject to filter by
            
        Returns:
            dict: Statistical analysis results
        """
        # Get filtered data
        data = self.get_attendance_by_subject(subject)
        
        if data.empty:
            return {}
        
        # Calculate basic statistics
        student_attendance = data.groupby('Enrollment').size()
        
        stats_results = {
            'basic_stats': {
                'mean': student_attendance.mean(),
                'median': student_attendance.median(),
                'std': student_attendance.std(),
                'min': student_attendance.min(),
                'max': student_attendance.max(),
                'skew': student_attendance.skew(),
                'kurtosis': student_attendance.kurtosis()
            }
        }
        
        # Perform normality test
        _, p_value = stats.normaltest(student_attendance)
        stats_results['normality_test'] = {
            'p_value': p_value,
            'is_normal': p_value > 0.05
        }
        
        # Calculate correlation with time
        if len(data) > 1:
            data['Days'] = (data['Date'] - data['Date'].min()).dt.days
            correlation = stats.pearsonr(data['Days'], data.groupby('Date').size())
            stats_results['time_correlation'] = {
                'correlation': correlation[0],
                'p_value': correlation[1]
            }
        
        # Identify outliers
        z_scores = stats.zscore(student_attendance)
        outliers = student_attendance[abs(z_scores) > 2]
        stats_results['outliers'] = {
            'count': len(outliers),
            'student_ids': outliers.index.tolist()
        }
        
        return stats_results
    
    def export_attendance_report(self, subject=None, output_format='csv', output_path=None, 
                               include_charts=True, include_stats=True):
        """
        Export attendance report to various formats with enhanced options
        
        Args:
            subject (str, optional): Subject to filter by
            output_format (str): Format to export ('csv', 'excel', 'html', 'pdf', 'pptx')
            output_path (str, optional): Path to save the exported file
            include_charts (bool): Whether to include charts in the report
            include_stats (bool): Whether to include statistical analysis
            
        Returns:
            str: Path to the exported file or None if export failed
        """
        # Get filtered data
        data = self.get_attendance_by_subject(subject)
        
        if data.empty:
            print("No data to export")
            return None
            
        # Create exports directory if it doesn't exist
        exports_dir = os.path.join(self.attendance_dir, "Exports")
        os.makedirs(exports_dir, exist_ok=True)
        
        # Default output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"attendance_report_{timestamp}"
        if subject:
            filename = f"{subject}_report_{timestamp}"
            
        if not output_path:
            output_path = os.path.join(exports_dir, filename)
            
        try:
            if output_format.lower() == 'csv':
                export_path = f"{output_path}.csv"
                data.to_csv(export_path, index=False)
                return export_path
                
            elif output_format.lower() == 'excel':
                export_path = f"{output_path}.xlsx"
                with pd.ExcelWriter(export_path) as writer:
                    # Write main data
                    data.to_excel(writer, sheet_name='Attendance Data', index=False)
                    
                    # Write summary statistics
                    if include_stats:
                        summary = self.get_attendance_summary(subject)
                        pd.DataFrame([summary]).to_excel(writer, sheet_name='Summary')
                        
                        stats = self.perform_statistical_analysis(subject)
                        pd.DataFrame([stats]).to_excel(writer, sheet_name='Statistics')
                    
                    # Save charts if requested
                    if include_charts:
                        # Create and save charts
                        charts = {
                            'Trend': self.create_attendance_trend_plot(subject),
                            'Weekly Pattern': self.create_weekly_pattern_plot(subject),
                            'Subject Comparison': self.create_subject_comparison_plot(),
                            'Heatmap': self.create_attendance_heatmap(subject)
                        }
                        
                        for name, fig in charts.items():
                            fig.savefig(f"{output_path}_{name.lower().replace(' ', '_')}.png")
                
                return export_path
                
            elif output_format.lower() == 'html':
                export_path = f"{output_path}.html"
                
                # Create HTML report
                html_content = f"""
                <html>
                <head>
                    <title>Attendance Report - {subject if subject else 'All Subjects'}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        table {{ border-collapse: collapse; width: 100%; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                        .chart {{ margin: 20px 0; }}
                        .stats {{ margin: 20px 0; padding: 20px; background-color: #f9f9f9; }}
                    </style>
                </head>
                <body>
                    <h1>Attendance Report</h1>
                    <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Subject: {subject if subject else 'All Subjects'}</p>
                    
                    {data.to_html(index=False)}
                    
                    {f'<div class="stats"><h2>Summary Statistics</h2>{pd.DataFrame([self.get_attendance_summary(subject)]).to_html()}</div>' if include_stats else ''}
                    
                    {f'<div class="stats"><h2>Statistical Analysis</h2>{pd.DataFrame([self.perform_statistical_analysis(subject)]).to_html()}</div>' if include_stats else ''}
                    
                    {f'<div class="chart"><h2>Attendance Trend</h2><img src="{output_path}_trend.png"></div>' if include_charts else ''}
                    {f'<div class="chart"><h2>Weekly Pattern</h2><img src="{output_path}_weekly_pattern.png"></div>' if include_charts else ''}
                    {f'<div class="chart"><h2>Subject Comparison</h2><img src="{output_path}_subject_comparison.png"></div>' if include_charts else ''}
                    {f'<div class="chart"><h2>Attendance Heatmap</h2><img src="{output_path}_heatmap.png"></div>' if include_charts else ''}
                </body>
                </html>
                """
                
                with open(export_path, 'w') as f:
                    f.write(html_content)
                
                return export_path
                
            elif output_format.lower() == 'pdf':
                # Implementation for PDF export would go here
                # This would require additional libraries like reportlab
                print("PDF export not yet implemented")
                return None
                
            elif output_format.lower() == 'pptx':
                # Implementation for PowerPoint export would go here
                # This would require additional libraries like python-pptx
                print("PowerPoint export not yet implemented")
                return None
                
            else:
                print(f"Unsupported format: {output_format}")
                return None
                
        except Exception as e:
            print(f"Error exporting data: {e}")
            return None 