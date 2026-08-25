"""
Progress dashboard: a read-only window that reads sessions/history.json and
shows trends over past practice rounds (answer length over time, how many
rounds you've done per role). Purely local -- no network calls, just charts
over your own saved history.
"""
from collections import Counter, defaultdict

import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from app.session_store import load_history

BG_COLOR = "#242424"
FG_COLOR = "#dcdcdc"
ACCENT_COLOR = "#3b8ed0"


class DashboardWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Progress Dashboard")
        self.geometry("760x560")
        self.minsize(600, 460)

        history = load_history()  # newest first
        chronological = list(reversed(history))

        if not history:
            ctk.CTkLabel(
                self,
                text="No practice sessions saved yet.\nComplete a round to see your progress here.",
                font=ctk.CTkFont(size=15),
                justify="center",
            ).pack(expand=True)
            return

        self._build_summary(history)
        self._build_charts(chronological)

    def _build_summary(self, history: list):
        total = len(history)
        word_counts = [len((h.get("transcript") or "").split()) for h in history]
        avg_words = sum(word_counts) / total if total else 0
        role_counts = Counter(h.get("role", "Unknown") for h in history)
        top_role = role_counts.most_common(1)[0][0] if role_counts else "N/A"

        summary_frame = ctk.CTkFrame(self)
        summary_frame.pack(fill="x", padx=16, pady=(16, 8))

        stats = [
            ("Total rounds", str(total)),
            ("Avg. answer length", f"{avg_words:.0f} words"),
            ("Most practiced role", top_role),
        ]
        for i, (label, value) in enumerate(stats):
            cell = ctk.CTkFrame(summary_frame, fg_color="transparent")
            cell.grid(row=0, column=i, padx=16, pady=12, sticky="w")
            ctk.CTkLabel(cell, text=value, font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(cell, text=label, text_color="#9a9a9a").pack(anchor="w")
        for i in range(len(stats)):
            summary_frame.grid_columnconfigure(i, weight=1)

    def _build_charts(self, chronological: list):
        fig = Figure(figsize=(7.2, 4.2), dpi=100, facecolor=BG_COLOR)

        # --- Answer length over time ---
        ax1 = fig.add_subplot(1, 2, 1)
        ax1.set_facecolor(BG_COLOR)
        word_counts = [len((h.get("transcript") or "").split()) for h in chronological]
        ax1.plot(range(1, len(word_counts) + 1), word_counts, color=ACCENT_COLOR, marker="o", markersize=3)
        ax1.set_title("Answer length over time", color=FG_COLOR, fontsize=10)
        ax1.set_xlabel("Round #", color=FG_COLOR, fontsize=8)
        ax1.set_ylabel("Words", color=FG_COLOR, fontsize=8)
        self._style_axes(ax1)

        # --- Sessions by role ---
        ax2 = fig.add_subplot(1, 2, 2)
        ax2.set_facecolor(BG_COLOR)
        role_counts = defaultdict(int)
        for h in chronological:
            role_counts[h.get("role", "Unknown")] += 1
        roles = list(role_counts.keys())
        counts = [role_counts[r] for r in roles]
        short_labels = [r if len(r) <= 12 else r[:11] + "…" for r in roles]
        ax2.bar(short_labels, counts, color=ACCENT_COLOR)
        ax2.set_title("Rounds by role", color=FG_COLOR, fontsize=10)
        ax2.tick_params(axis="x", rotation=35)
        self._style_axes(ax2)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=16, pady=8)

    @staticmethod
    def _style_axes(ax):
        ax.tick_params(colors=FG_COLOR, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#555555")
