"""Database-backed analytics view for attendance reporting."""
from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.core.database.db_handler import DatabaseHandler
from src.ui.attendance_reporting import export_attendance_data, load_analytics_data

logger = logging.getLogger(__name__)

_PERIOD_LABELS = {
    "Week": "week",
    "Month": "month",
    "Semester": "semester",
    "Year": "year",
    "All Time": "all",
}


class AnalyticsDashboard(ctk.CTkFrame):
    """Analyze and export attendance directly from the canonical SQLite database."""

    def __init__(self, master, db_handler=None):
        super().__init__(master)
        self.db = db_handler or DatabaseHandler()
        self._owns_database = db_handler is None
        self.attendance_data = pd.DataFrame()
        self._canvas: FigureCanvasTkAgg | None = None
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Attendance Analytics",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 3))
        self.summary_label = ctk.CTkLabel(
            header,
            text="Loading attendance data...",
            text_color=("gray50", "gray70"),
        )
        self.summary_label.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 18))

        controls = ctk.CTkFrame(self, corner_radius=12)
        controls.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        for column in range(4):
            controls.grid_columnconfigure(column, weight=1)

        subjects = self._subject_options()
        self.subject_var = ctk.StringVar(value="All")
        ctk.CTkLabel(controls, text="Subject").grid(
            row=0, column=0, sticky="w", padx=15, pady=(12, 4)
        )
        self.subject_menu = ctk.CTkOptionMenu(
            controls,
            values=subjects,
            variable=self.subject_var,
            command=lambda _value: self.refresh_data(),
        )
        self.subject_menu.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 12))

        self.period_var = ctk.StringVar(value="Month")
        ctk.CTkLabel(controls, text="Period").grid(
            row=0, column=1, sticky="w", padx=15, pady=(12, 4)
        )
        ctk.CTkOptionMenu(
            controls,
            values=list(_PERIOD_LABELS),
            variable=self.period_var,
            command=lambda _value: self.refresh_data(),
        ).grid(row=1, column=1, sticky="ew", padx=15, pady=(0, 12))

        self.chart_var = ctk.StringVar(value="Attendance Over Time")
        ctk.CTkLabel(controls, text="Chart").grid(
            row=0, column=2, sticky="w", padx=15, pady=(12, 4)
        )
        ctk.CTkOptionMenu(
            controls,
            values=[
                "Attendance Over Time",
                "Attendance by Subject",
                "Attendance by Status",
            ],
            variable=self.chart_var,
            command=lambda _value: self._render_chart(),
        ).grid(row=1, column=2, sticky="ew", padx=15, pady=(0, 12))

        actions = ctk.CTkFrame(controls, fg_color="transparent")
        actions.grid(row=0, column=3, rowspan=2, sticky="e", padx=15, pady=12)
        ctk.CTkButton(actions, text="Refresh", width=90, command=self.refresh_data).pack(
            side="left", padx=(0, 8)
        )
        self.export_button = ctk.CTkButton(
            actions,
            text="Export CSV",
            width=105,
            command=self._export_data,
        )
        self.export_button.pack(side="left")

        self.chart_frame = ctk.CTkFrame(self, corner_radius=12)
        self.chart_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10, 20))

    def _subject_options(self) -> list[str]:
        subjects = [subject for subject in self.db.get_subjects() if subject]
        return ["All", *subjects]

    def _refresh_subject_options(self) -> None:
        current = self.subject_var.get() if hasattr(self, "subject_var") else "All"
        subjects = self._subject_options()
        self.subject_menu.configure(values=subjects)
        self.subject_var.set(current if current in subjects else "All")

    def refresh_data(self) -> None:
        """Refresh the selected dataset and chart from SQLite."""
        try:
            if hasattr(self, "subject_menu"):
                self._refresh_subject_options()
            period = _PERIOD_LABELS[self.period_var.get()]
            self.attendance_data = load_analytics_data(
                self.db,
                subject=self.subject_var.get(),
                period=period,
            )
            self.summary_label.configure(
                text=self._summary_text(self.attendance_data),
            )
            self.export_button.configure(
                state="normal" if not self.attendance_data.empty else "disabled"
            )
            self._render_chart()
        except Exception as exc:
            logger.exception("Could not refresh analytics")
            self.summary_label.configure(text=f"Analytics refresh failed: {exc}")
            self.attendance_data = pd.DataFrame()
            self.export_button.configure(state="disabled")
            self._render_chart()

    @staticmethod
    def _summary_text(frame: pd.DataFrame) -> str:
        if frame.empty:
            return "No attendance records match the current filters."
        students = int(frame["Enrollment"].nunique())
        subjects = int(frame["Subject"].nunique())
        return f"{len(frame)} records - {students} students - {subjects} subjects"

    def _replace_canvas(self, figure: Figure) -> None:
        if self._canvas is not None:
            self._canvas.get_tk_widget().destroy()
        self._canvas = FigureCanvasTkAgg(figure, master=self.chart_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def _render_chart(self) -> None:
        figure = Figure(figsize=(8.0, 4.5), tight_layout=True)
        axis = figure.add_subplot(111)
        frame = self.attendance_data
        if frame.empty:
            axis.text(0.5, 0.5, "No attendance data to display", ha="center", va="center")
            axis.set_axis_off()
            self._replace_canvas(figure)
            return

        chart = self.chart_var.get()
        if chart == "Attendance Over Time":
            grouped = frame.groupby("Date").size().sort_index()
            axis.plot(grouped.index.astype(str), grouped.values, marker="o")
            axis.tick_params(axis="x", rotation=35)
            axis.set_ylabel("Records")
        elif chart == "Attendance by Subject":
            grouped = frame.groupby("Subject").size().sort_values(ascending=False)
            axis.bar(grouped.index.astype(str), grouped.values)
            axis.tick_params(axis="x", rotation=30)
            axis.set_ylabel("Records")
        else:
            grouped = frame.groupby("Status").size().sort_values(ascending=False)
            axis.bar(grouped.index.astype(str), grouped.values)
            axis.set_ylabel("Records")
        axis.set_title(chart)
        self._replace_canvas(figure)

    def _export_data(self) -> None:
        if self.attendance_data.empty:
            messagebox.showinfo("Nothing to export", "No attendance records match the filters.")
            return
        destination = filedialog.asksaveasfilename(
            parent=self,
            title="Export attendance analytics",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="attendance_analytics.csv",
        )
        if not destination:
            return
        try:
            path = export_attendance_data(self.attendance_data, Path(destination))
            messagebox.showinfo("Export complete", f"Attendance exported to:\n{path}", parent=self)
        except OSError as exc:
            logger.exception("Could not export analytics data")
            messagebox.showerror("Export failed", str(exc), parent=self)

    def destroy(self) -> None:
        if self._owns_database:
            try:
                self.db.close()
            except Exception:
                logger.exception("Could not close analytics database")
        super().destroy()
