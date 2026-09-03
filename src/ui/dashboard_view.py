"""Database-backed production dashboard for the attendance system."""
from __future__ import annotations

import logging
from datetime import datetime

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.ui.attendance_reporting import DashboardSnapshot, build_dashboard_snapshot

logger = logging.getLogger(__name__)


class DashboardView(ctk.CTkFrame):
    """Show live attendance statistics from the canonical SQLite database."""

    def __init__(self, master, auth_system, db_handler, **kwargs):
        super().__init__(master, **kwargs)
        self.auth_system = auth_system
        self.db = db_handler
        self.current_user = auth_system.get_current_user()
        self.trend_period = "week"
        self._trend_canvas: FigureCanvasTkAgg | None = None
        self._subject_canvas: FigureCanvasTkAgg | None = None
        self.stat_cards: dict[str, dict[str, ctk.CTkLabel]] = {}
        self._build_ui()
        self.load_data()

    def _build_ui(self) -> None:
        self.configure(fg_color=("gray95", "gray17"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        username = self.current_user.get("username", "User")
        ctk.CTkLabel(
            header,
            text=f"Welcome back, {username}",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            header,
            text=datetime.now().astimezone().strftime("%A, %B %d, %Y"),
            text_color=("gray50", "gray70"),
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 18))
        ctk.CTkButton(
            header,
            text="Refresh",
            width=90,
            command=self.load_data,
        ).grid(row=0, column=1, rowspan=2, padx=20)

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1)
        definitions = (
            ("total", "Total Records", "All time"),
            ("students", "Enrolled Students", "Active database records"),
            ("today", "Today's Attendance", "Records today"),
            ("subjects", "Subjects", "Configured subjects"),
        )
        for column, (key, title, subtitle) in enumerate(definitions):
            self.stat_cards[key] = self._create_stat_card(
                stats,
                title=title,
                subtitle=subtitle,
                column=column,
            )

        charts = ctk.CTkFrame(self, fg_color="transparent")
        charts.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        charts.grid_columnconfigure((0, 1), weight=1)

        self.trend_frame = ctk.CTkFrame(charts, corner_radius=12)
        self.trend_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ctk.CTkLabel(
            self.trend_frame,
            text="Attendance Trend",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(15, 5))
        period_row = ctk.CTkFrame(self.trend_frame, fg_color="transparent")
        period_row.pack(fill="x", padx=15, pady=(0, 5))
        for period in ("week", "month", "semester"):
            ctk.CTkButton(
                period_row,
                text=period.capitalize(),
                width=84,
                height=28,
                command=lambda value=period: self._on_period_change(value),
            ).pack(side="left", padx=(0, 5))
        self.trend_plot_frame = ctk.CTkFrame(self.trend_frame, fg_color="transparent")
        self.trend_plot_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.subject_frame = ctk.CTkFrame(charts, corner_radius=12)
        self.subject_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        ctk.CTkLabel(
            self.subject_frame,
            text="Attendance by Subject",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(15, 5))
        self.subject_plot_frame = ctk.CTkFrame(self.subject_frame, fg_color="transparent")
        self.subject_plot_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        activity = ctk.CTkFrame(self, corner_radius=12)
        activity.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 20))
        ctk.CTkLabel(
            activity,
            text="Recent Attendance",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(15, 8))
        self.activity_list = ctk.CTkScrollableFrame(activity, fg_color="transparent")
        self.activity_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    @staticmethod
    def _create_stat_card(parent, *, title: str, subtitle: str, column: int):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.grid(row=0, column=column, sticky="nsew", padx=5)
        ctk.CTkLabel(
            card,
            text=title,
            text_color=("gray50", "gray70"),
        ).pack(anchor="w", padx=15, pady=(14, 4))
        value = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=28, weight="bold"))
        value.pack(anchor="w", padx=15, pady=(0, 4))
        subtitle_label = ctk.CTkLabel(
            card,
            text=subtitle,
            text_color=("gray50", "gray70"),
        )
        subtitle_label.pack(anchor="w", padx=15, pady=(0, 14))
        return {"value": value, "subtitle": subtitle_label}

    def load_data(self) -> None:
        """Refresh every dashboard element from the database source of truth."""
        try:
            snapshot = build_dashboard_snapshot(self.db, trend_period=self.trend_period)
            self._render_snapshot(snapshot)
        except Exception as exc:
            logger.exception("Could not refresh dashboard")
            self._render_error(str(exc))

    def _render_snapshot(self, snapshot: DashboardSnapshot) -> None:
        self.stat_cards["total"]["value"].configure(text=str(snapshot.total_records))
        self.stat_cards["students"]["value"].configure(text=str(snapshot.enrolled_students))
        self.stat_cards["today"]["value"].configure(text=str(snapshot.today_records))
        self.stat_cards["subjects"]["value"].configure(text=str(snapshot.subject_count))
        self._render_trend(snapshot)
        self._render_subjects(snapshot)
        self._render_recent(snapshot)

    def _replace_canvas(self, attribute: str, frame, figure: Figure) -> None:
        previous = getattr(self, attribute)
        if previous is not None:
            previous.get_tk_widget().destroy()
        canvas = FigureCanvasTkAgg(figure, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        setattr(self, attribute, canvas)

    def _render_trend(self, snapshot: DashboardSnapshot) -> None:
        figure = Figure(figsize=(5.0, 2.4), tight_layout=True)
        axis = figure.add_subplot(111)
        if snapshot.attendance_by_date:
            dates, counts = zip(*snapshot.attendance_by_date, strict=True)
            axis.plot(dates, counts, marker="o")
            axis.tick_params(axis="x", rotation=35)
            axis.set_ylabel("Records")
        else:
            axis.text(0.5, 0.5, "No attendance in this period", ha="center", va="center")
            axis.set_axis_off()
        self._replace_canvas("_trend_canvas", self.trend_plot_frame, figure)

    def _render_subjects(self, snapshot: DashboardSnapshot) -> None:
        figure = Figure(figsize=(5.0, 2.4), tight_layout=True)
        axis = figure.add_subplot(111)
        if snapshot.attendance_by_subject:
            subjects, counts = zip(*snapshot.attendance_by_subject, strict=True)
            axis.bar(subjects, counts)
            axis.tick_params(axis="x", rotation=30)
            axis.set_ylabel("Records")
        else:
            axis.text(0.5, 0.5, "No attendance recorded", ha="center", va="center")
            axis.set_axis_off()
        self._replace_canvas("_subject_canvas", self.subject_plot_frame, figure)

    def _render_recent(self, snapshot: DashboardSnapshot) -> None:
        for child in self.activity_list.winfo_children():
            child.destroy()
        if not snapshot.recent_records:
            ctk.CTkLabel(
                self.activity_list,
                text="No recent attendance to display",
                text_color=("gray50", "gray70"),
            ).pack(pady=20)
            return

        for record in snapshot.recent_records:
            row = ctk.CTkFrame(self.activity_list, corner_radius=8)
            row.pack(fill="x", padx=4, pady=4)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                row,
                text=record["Name"],
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(
                row,
                text=f"{record['Subject']} - {record['Status']}",
                text_color=("gray50", "gray70"),
            ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))
            ctk.CTkLabel(
                row,
                text=f"{record['Date']} {record['Time']}",
                text_color=("gray50", "gray70"),
            ).grid(row=0, column=1, rowspan=2, padx=12)

    def _render_error(self, message: str) -> None:
        for child in self.activity_list.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.activity_list,
            text=f"Dashboard refresh failed: {message}",
            text_color=("#b00020", "#ff8a80"),
        ).pack(pady=20)

    def _on_period_change(self, period: str) -> None:
        self.trend_period = period
        self.load_data()
