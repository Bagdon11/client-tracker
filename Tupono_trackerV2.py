import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
from tkinter import filedialog
from fpdf import FPDF
import tempfile
import pandas as pd  # For crosstab in program-by-gender chart

# Define advocacy types and their typical/max durations in weeks
ADVOCACY_TYPES = ["Family harm", "Sexual harm", "Mental health", "Oranga Tamariki", "MSD", "Housing"]

# List of Kaimahi
KAIMAHI_LIST = [
    "Shonny", "Mervyn", "Te rangi", "Ben", "Piwi", "Arianna", "Melissa", "Tipene Mary"
]
# Durations: Min 6 months (~26 weeks), Max 4 years (~208 weeks)
ADVOCACY_MIN_WEEKS = 26
ADVOCACY_MAX_WEEKS = 208

JSON_PATH = os.path.join(os.path.dirname(__file__), "participants.json")
print(f"JSON_PATH resolved to: {JSON_PATH}")
print(f"File exists: {os.path.exists(JSON_PATH)}")

class Participant:
    def __init__(self, name, age, gender, location, iwi, hapu, signup_date, advocacy=None, kaimahi=None):
        self.name = name
        self.age = age
        self.gender = gender
        self.location = location
        self.iwi = iwi
        self.hapu = hapu
        self.advocacy = advocacy if isinstance(advocacy, list) else []  # Always a list
        self.kaimahi = kaimahi if kaimahi in KAIMAHI_LIST else None
        self.signup_date = datetime.strptime(signup_date, "%Y-%m-%d").date()
        self.phase = "red"  # red, orange, green, completed
        self.weeks_completed = 0
        self.programs = []  # Now supports multiple programs
        self.weekly_progress = []  # For the 26-week program

        # === Advocacy Tracking Attributes ===
        self.advocacy_phase = "active" if self.advocacy else "none"  # 'none', 'active', 'completed'
        self.advocacy_weeks_completed = 0
        self.advocacy_weekly_progress = []  # For the long-term advocacy (up to 208 weeks)

        self.red_phase_assessments = {
            1: {"score": 0, "notes": ""},
            2: {"score": 0, "notes": ""},
            3: {"score": 0, "notes": ""},
            4: {"score": 0, "notes": ""},
            5: {"score": 0, "notes": ""},
            6: {"score": 0, "notes": ""}
        }

    def update_progress(self):
        today = datetime.now().date()
        weeks_since_signup = (today - self.signup_date).days // 7
        if weeks_since_signup < 0:
            return  # hasn't started yet

        # --- Update Standard 26-Week Program Progress ---
        if self.phase == "red":
            total_red_weeks = 6
            if weeks_since_signup >= total_red_weeks:
                self.phase = "orange"
                self.weeks_completed = 0
            else:
                self.weeks_completed = weeks_since_signup
        elif self.phase == "orange":
            total_orange_weeks = 8
            if weeks_since_signup >= 6 + total_orange_weeks:
                self.phase = "green"
                self.weeks_completed = 0
            else:
                self.weeks_completed = weeks_since_signup - 6
        elif self.phase == "green":
            total_green_weeks = 12
            green_start_week = 6 + 8  # week 14
            if weeks_since_signup >= green_start_week + total_green_weeks:
                self.phase = "completed"
                self.weeks_completed = 12
            else:
                self.weeks_completed = weeks_since_signup - green_start_week

        # Update weekly_progress for full 26-week journey
        total_weeks = 26
        self.weekly_progress = []
        for week in range(total_weeks):
            if week < weeks_since_signup:
                if week < 6:
                    self.weekly_progress.append("red")
                elif week < 14:
                    self.weekly_progress.append("orange")
                else:
                    self.weekly_progress.append("green")
            else:
                self.weekly_progress.append("")

        # --- Update Long-Term Advocacy Progress (if applicable) ---
        if self.advocacy and len(self.advocacy) > 0:
            self.advocacy_phase = "active"
            self.advocacy_weeks_completed = min(weeks_since_signup, ADVOCACY_MAX_WEEKS)

            # Build the advocacy progress bar (up to max duration)
            self.advocacy_weekly_progress = []
            for week in range(ADVOCACY_MAX_WEEKS):
                if week < weeks_since_signup:
                    self.advocacy_weekly_progress.append("advocacy_active")
                else:
                    self.advocacy_weekly_progress.append("")
        else:
            self.advocacy_phase = "none"
            self.advocacy_weeks_completed = 0
            self.advocacy_weekly_progress = []

    def to_dict(self):
        return {
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "location": self.location,
            "iwi": self.iwi,
            "hapu": self.hapu,
            "signup_date": self.signup_date.strftime("%Y-%m-%d"),
            "phase": self.phase,
            "weeks_completed": self.weeks_completed,
            "programs": self.programs,
            "weekly_progress": self.weekly_progress,
            "red_phase_assessments": self.red_phase_assessments,
            "advocacy": self.advocacy,  # List of strings
            "advocacy_phase": self.advocacy_phase,
            "advocacy_weeks_completed": self.advocacy_weeks_completed,
            "advocacy_weekly_progress": self.advocacy_weekly_progress,
            "kaimahi": self.kaimahi
        }

    @classmethod
    def from_dict(cls, data):
        try:
            participant = cls(
                data["name"],
                data["age"],
                data.get("gender", "Not specified"),
                data["location"],
                data["iwi"],
                data["hapu"],
                data["signup_date"],
                data.get("advocacy", []),
                data.get("kaimahi", None)
            )
            participant.phase = data.get("phase", "red")
            participant.weeks_completed = data.get("weeks_completed", 0)
            participant.programs = data.get("programs", [])
            participant.weekly_progress = data.get("weekly_progress", [])
            raw_assessments = data.get("red_phase_assessments", {})
            # Convert string keys to int keys
            red_phase_assessments = {}
            for k, v in raw_assessments.items():
                try:
                    red_phase_assessments[int(k)] = v
                except (ValueError, TypeError):
                    pass  # Skip invalid keys
            # Fill in missing weeks with defaults
            default = {"score": 0, "notes": ""}
            for week in range(1, 7):
                if week not in red_phase_assessments:
                    red_phase_assessments[week] = default.copy()
            participant.red_phase_assessments = red_phase_assessments

            # Load advocacy tracking data
            participant.advocacy_phase = data.get("advocacy_phase", "none")
            participant.advocacy_weeks_completed = data.get("advocacy_weeks_completed", 0)
            participant.advocacy_weekly_progress = data.get("advocacy_weekly_progress", [])

            return participant
        except Exception as e:
            print(f"FAILED to create Participant: {e}")
            raise

class ProgramTrackerApp:
    def __init__(self, root):
        print("Starting app initialization...")
        self.root = root
        self.root.title("Māori Support Program Tracker")
        self.participants = []
        self.current_participant = None
        self.statistics_window = None
        print("Basic attributes set...")

        # === Tu Pono Brand Colours ===
        self.bg_color = "#1A3A2A"           # Dark Green (Tu Pono)
        self.fg_color = "#FFFFFF"           # White
        self.primary_color = "#1A3A2A"      # Dark Green (Tu Pono)
        self.accent_color = "#4CAF50"       # Light Green
        self.card_bg = "#444444"            # Cards
        self.border_color = "#1A3A2A"       # Dark green borders
        self.progress_bg = "#444444"        # Progress bar bg
        self.font_family = "Segoe UI"
        print("Colors initialized...")

        print("Loading data...")
        self.load_data()
        print("Creating widgets...")
        self.create_widgets()
        print("Applying theme...")
        self.apply_theme()
        print("App initialization complete!")

    def new_file(self):
        if self.participants:
            if not messagebox.askyesno("Confirm", "This will clear all current data. Continue?"):
                return
        self.participants = []
        self.update_participants_list()
        self.clear_inputs()
        messagebox.showinfo("New File", "Created new empty participant list")

    def load_json_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Open Participant Data",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            self.load_json(filepath)

    def load_json(self, filepath):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            self.participants = [Participant.from_dict(item) for item in data]
            self.update_participants_list()
            messagebox.showinfo("Success", f"Loaded {len(self.participants)} participants")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")

    def save_json_dialog(self):
        if not self.participants:
            messagebox.showwarning("No Data", "There are no participants to save")
            return
        filepath = filedialog.asksaveasfilename(
            title="Save Participant Data",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            self.save_json(filepath)

    def save_json(self, filepath):
        try:
            data = [p.to_dict() for p in self.participants]
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Success", f"Saved {len(self.participants)} participants to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")

    def export_to_pdf(self, filename=None):
        if not self.participants:
            messagebox.showwarning("No Data", "No participants to export")
            return
        if not filename:
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                title="Save Full Report"
            )
            if not filename:
                return

        # Show "Please Wait" dialog
        wait_window = tk.Toplevel(self.root)
        wait_window.title("Generating Report")
        wait_window.geometry("300x100")
        wait_window.resizable(False, False)
        wait_window.transient(self.root)
        wait_window.grab_set()
        wait_window.focus_set()
        label = ttk.Label(wait_window, text="Generating PDF...\nPlease wait", font=("Helvetica", 12))
        label.pack(expand=True)
        wait_window.protocol("WM_DELETE_WINDOW", lambda: None)
        self.root.update_idletasks()

        def do_export():
            try:
                pdf = FPDF(orientation='P', unit='mm', format='A4')
                pdf.set_auto_page_break(auto=True, margin=15)

                # Cover Page
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 24)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 20, "Tu Pono IP - Full Report", 0, 1, "C")
                pdf.ln(10)
                pdf.set_font("Helvetica", "", 14)
                pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")
                pdf.ln(20)

                # Charts
                # Remove Advocacy Duration chart from export
                charts = self._generate_all_charts()
                for chart_name, fig in charts.items():
                    if chart_name == "Advocacy: Duration":
                        continue  # Skip the Advocacy Duration chart
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 16)
                    pdf.cell(0, 10, chart_name, 0, 1)
                    temp_img = os.path.join(tempfile.gettempdir(), f"{chart_name.replace(' ', '_')}.png")
                    fig.savefig(temp_img, dpi=300, bbox_inches='tight')
                    plt.close(fig)
                    pdf.image(temp_img, x=pdf.w / 2 - 80, w=160)
                    os.remove(temp_img)

                pdf.output(filename)
                messagebox.showinfo("Success", f"Full report saved to:\n{filename}")
                self._open_file(filename)
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to create PDF:\n{str(e)}")
            finally:
                try:
                    wait_window.destroy()
                except:
                    pass

        wait_window.after(100, do_export)

    def _generate_all_charts(self):
        charts = {}
        programs = ["Ko wai au", "Mental Health and Well-being", "Anger Management", "Domestic Violence"]
        allowed_genders = ["Male", "Female", "Non-binary"]

        # 1. Program Distribution
        program_counts = {p: sum(1 for part in self.participants if p in part.programs) for p in programs}
        values = list(program_counts.values())
        labels = list(program_counts.keys())
        if sum(values) == 0:
            values = [1]
            labels = ["No Programs Assigned"]
            autopct = None
        else:
            autopct = '%1.1f%%'
        fig1, ax1 = plt.subplots(figsize=(8, 6))
        ax1.pie(values, labels=labels, autopct=autopct, startangle=90)
        ax1.axis('equal')
        ax1.set_title("Program Distribution")
        charts["Program Distribution"] = fig1

        # 2. Gender Distribution
        gender_counts = {g: sum(1 for part in self.participants if part.gender == g) for g in allowed_genders}
        values = list(gender_counts.values())
        labels = list(gender_counts.keys())
        if sum(values) == 0:
            values = [1]
            labels = ["No Data"]
            autopct = None
        else:
            autopct = '%1.1f%%'
        fig2, ax2 = plt.subplots(figsize=(8, 6))
        ax2.pie(values, labels=labels, autopct=autopct, startangle=90)
        ax2.axis('equal')
        ax2.set_title("Gender Distribution")
        charts["Gender Distribution"] = fig2

        # 3. Iwi Affiliation
        iwi_counts = {}
        for p in self.participants:
            iwi = p.iwi if p.iwi else "Not specified"
            iwi_counts[iwi] = iwi_counts.get(iwi, 0) + 1
        if len(iwi_counts) > 8:
            total = sum(iwi_counts.values())
            threshold = total * 0.05
            grouped = {k: v for k, v in iwi_counts.items() if v >= threshold}
            other = sum(v for k, v in iwi_counts.items() if v < threshold)
            if other > 0:
                grouped["Other"] = other
            iwi_counts = grouped
        values = list(iwi_counts.values())
        labels = list(iwi_counts.keys())
        if sum(values) == 0:
            values = [1]
            labels = ["No Data"]
            autopct = None
        else:
            autopct = '%1.1f%%'
        fig3, ax3 = plt.subplots(figsize=(8, 6))
        ax3.pie(values, labels=labels, autopct=autopct, startangle=90)
        ax3.axis('equal')
        ax3.set_title("Iwi Affiliation")
        charts["Iwi Affiliation"] = fig3

        # 4. Program by Gender
        data_rows = []
        for p in self.participants:
            if p.gender in allowed_genders:
                if p.programs:
                    for prog in p.programs:
                        data_rows.append({'gender': p.gender, 'program': prog})
                else:
                    data_rows.append({'gender': p.gender, 'program': 'No Program'})
        df = pd.DataFrame(data_rows)
        if not df.empty:
            try:
                gender_program_data = pd.crosstab(df['gender'], df['program'])
                if not gender_program_data.empty:
                    fig4, ax4 = plt.subplots(figsize=(10, 6))
                    gender_program_data.plot(kind='bar', stacked=True, ax=ax4)
                    ax4.set_title("Program Participation by Gender")
                    ax4.set_ylabel("Count")
                    ax4.legend(title="Program")
                    charts["Program by Gender"] = fig4
            except Exception as e:
                print(f"Error generating Program by Gender chart: {e}")

        # === 5. Advocacy Statistics ===
        # With vs Without
        total_with_advocacy = sum(1 for p in self.participants if p.advocacy and len(p.advocacy) > 0)
        total_without_advocacy = len(self.participants) - total_with_advocacy
        fig_adv1, ax_adv1 = plt.subplots(figsize=(6, 6))
        labels = ['With Advocacy', 'Without Advocacy']
        sizes = [total_with_advocacy, total_without_advocacy]
        colors = ['#5D4037', '#BDBDBD']
        if sum(sizes) == 0:
            sizes = [1]
            labels = ["No Data"]
            autopct = None
        else:
            autopct = '%1.1f%%'
        ax_adv1.pie(sizes, labels=labels, autopct=autopct, colors=colors, startangle=90)
        ax_adv1.axis('equal')
        ax_adv1.set_title("Participants with Advocacy")
        charts["Advocacy: With vs Without"] = fig_adv1

        # By Type
        advocacy_type_counts = {atype: 0 for atype in ADVOCACY_TYPES}
        for p in self.participants:
            for atype in getattr(p, 'advocacy', []):
                if atype in advocacy_type_counts:
                    advocacy_type_counts[atype] += 1
        fig_adv2, ax_adv2 = plt.subplots(figsize=(8, 6))
        types = list(advocacy_type_counts.keys())
        counts = list(advocacy_type_counts.values())
        bars = ax_adv2.bar(types, counts, color='#5D4037')
        ax_adv2.set_title("Advocacy Type Distribution")
        ax_adv2.set_ylabel("Number of Participants")
        ax_adv2.tick_params(axis='x', rotation=45)
        for bar in bars:
            height = bar.get_height()
            ax_adv2.annotate(f'{int(height)}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=10)
        charts["Advocacy: By Type"] = fig_adv2

        # Duration Distribution
        duration_bins = {
            "<1 Year": 0,
            "1-2 Years": 0,
            "2-3 Years": 0,
            "3-4 Years": 0,
            "4+ Years": 0
        }
        for p in self.participants:
            if getattr(p, 'advocacy', None) and len(p.advocacy) > 0:
                weeks = getattr(p, 'advocacy_weeks_completed', 0)
                years = weeks / 52.0
                if years < 1:
                    duration_bins["<1 Year"] += 1
                elif years < 2:
                    duration_bins["1-2 Years"] += 1
                elif years < 3:
                    duration_bins["2-3 Years"] += 1
                elif years < 4:
                    duration_bins["3-4 Years"] += 1
                else:
                    duration_bins["4+ Years"] += 1
        fig_adv3, ax_adv3 = plt.subplots(figsize=(6, 6))
        labels = list(duration_bins.keys())
        sizes = list(duration_bins.values())
        colors_duration = ['#FFB347', '#FF8C00', '#E53935', '#B71C1C', '#5D4037']
        if sum(sizes) == 0:
            sizes = [1]
            labels = ["No Advocacy Participants"]
            autopct = None
        else:
            autopct = '%1.1f%%'
        ax_adv3.pie(sizes, labels=labels, autopct=autopct, colors=colors_duration, startangle=90)
        ax_adv3.axis('equal')
        ax_adv3.set_title("Advocacy Duration Distribution")
        charts["Advocacy: Duration"] = fig_adv3

        return charts

    def _open_file(self, path):
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["open", path])
        else:
            import subprocess
            subprocess.run(["xdg-open", path])

    def create_widgets(self):
        self.input_frame = ttk.LabelFrame(self.root, text="Participant Information", padding=10)
        self.input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.progress_frame = ttk.LabelFrame(self.root, text="Progress Tracking", padding=10)
        self.progress_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.list_frame = ttk.LabelFrame(self.root, text="Participants List", padding=10)
        self.list_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        # Input Fields
        ttk.Label(self.input_frame, text="Name:").grid(row=0, column=0, sticky="w")
        self.name_entry = ttk.Entry(self.input_frame)
        self.name_entry.grid(row=0, column=1, pady=5, sticky="ew")

        ttk.Label(self.input_frame, text="Age:").grid(row=1, column=0, sticky="w")
        self.age_entry = ttk.Entry(self.input_frame)
        self.age_entry.grid(row=1, column=1, pady=5, sticky="ew")

        ttk.Label(self.input_frame, text="Gender:").grid(row=2, column=0, sticky="w")
        self.gender_var = tk.StringVar()
        self.gender_dropdown = ttk.Combobox(self.input_frame, textvariable=self.gender_var,
                                          values=["Male", "Female", "Non-binary"])
        self.gender_dropdown.grid(row=2, column=1, pady=5, sticky="ew")


        # Advocacy (Multi-Select Listbox)
        ttk.Label(self.input_frame, text="Advocacy:").grid(row=3, column=0, sticky="w")
        self.advocacy_listbox = tk.Listbox(self.input_frame, height=6, selectmode="multiple")
        for a in ADVOCACY_TYPES:
            self.advocacy_listbox.insert(tk.END, a)
        self.advocacy_listbox.grid(row=3, column=1, pady=5, sticky="ew")

        # Kaimahi Dropdown
        ttk.Label(self.input_frame, text="Kaimahi:").grid(row=8, column=0, sticky="w")
        self.kaimahi_var = tk.StringVar()
        self.kaimahi_dropdown = ttk.Combobox(self.input_frame, textvariable=self.kaimahi_var, values=KAIMAHI_LIST, state="readonly")
        self.kaimahi_dropdown.grid(row=8, column=1, pady=5, sticky="ew")

        ttk.Label(self.input_frame, text="Location:").grid(row=4, column=0, sticky="w")
        self.location_entry = ttk.Entry(self.input_frame)
        self.location_entry.grid(row=4, column=1, pady=5, sticky="ew")

        ttk.Label(self.input_frame, text="Iwi:").grid(row=5, column=0, sticky="w")
        self.iwi_entry = ttk.Entry(self.input_frame)
        self.iwi_entry.grid(row=5, column=1, pady=5, sticky="ew")

        ttk.Label(self.input_frame, text="Hapū:").grid(row=6, column=0, sticky="w")
        self.hapu_entry = ttk.Entry(self.input_frame)
        self.hapu_entry.grid(row=6, column=1, pady=5, sticky="ew")

        ttk.Label(self.input_frame, text="Signup Date (YYYY-MM-DD):").grid(row=7, column=0, sticky="w")
        self.date_entry = ttk.Entry(self.input_frame)
        self.date_entry.grid(row=7, column=1, pady=5, sticky="ew")

        self.add_button = ttk.Button(self.input_frame, text="Add Participant", command=self.add_participant)
        self.add_button.grid(row=9, column=0, columnspan=2, pady=10, sticky="ew")

        self.update_button = ttk.Button(self.input_frame, text="Update Participant", command=self.update_participant, state="disabled")
        self.update_button.grid(row=10, column=0, columnspan=2, pady=5, sticky="ew")

        # Progress Display
        self.status_label = ttk.Label(self.progress_frame, text="Status: Not selected", font=('Helvetica', 12))
        self.status_label.grid(row=0, column=0, columnspan=2, pady=5, sticky="w")

        self.program_label = ttk.Label(self.progress_frame, text="Program(s): Not selected", font=('Helvetica', 12))
        self.program_label.grid(row=1, column=0, columnspan=2, pady=5, sticky="w")

        ttk.Label(self.progress_frame, text="Weekly Progress:").grid(row=2, column=0, columnspan=2, pady=5, sticky="w")

        # Progress Canvas (Reduced height for two bars)
        self.progress_canvas = tk.Canvas(self.progress_frame, width=520, height=80, bg="white")
        self.progress_canvas.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")

        # Program Selection
        ttk.Label(self.progress_frame, text="Select Programs:").grid(row=4, column=0, pady=5, sticky="w")
        self.program_listbox = tk.Listbox(self.progress_frame, height=4, selectmode="multiple")
        for p in ["Ko wai au", "Mental Health and Well-being", "Anger Management", "Domestic Violence"]:
            self.program_listbox.insert(tk.END, p)
        self.program_listbox.grid(row=4, column=1, pady=5, sticky="ew")

        self.select_program_button = ttk.Button(self.progress_frame, text="Set Programs", command=self.set_programs, state="disabled")
        self.select_program_button.grid(row=5, column=0, columnspan=2, pady=5, sticky="ew")

        self.assessment_button = ttk.Button(
            self.progress_frame,
            text="Weekly Assessment",
            command=self.show_assessment,
            state="disabled"
        )
        self.assessment_button.grid(row=6, column=0, columnspan=2, pady=5, sticky="ew")

        self.review_assessment_button = ttk.Button(
            self.progress_frame,
            text="Review Weekly Assessments",
            command=self.review_assessments,
            state="disabled"
        )
        self.review_assessment_button.grid(row=7, column=0, columnspan=2, pady=5, sticky="ew")

        self.stats_button = ttk.Button(self.progress_frame, text="View Statistics", command=self.show_statistics)
        self.stats_button.grid(row=8, column=0, columnspan=2, pady=5, sticky="ew")

        # Participants List
        self.participants_listbox = tk.Listbox(self.list_frame, height=10)
        self.participants_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.participants_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.participants_listbox.config(yscrollcommand=scrollbar.set)
        self.participants_listbox.bind("<<ListboxSelect>>", self.select_participant)

        self.delete_button = ttk.Button(self.list_frame, text="Delete Participant", command=self.delete_participant)
        self.delete_button.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        # File Menu
        self.file_frame = ttk.Frame(self.root)
        self.file_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        ttk.Button(self.file_frame, text="New", command=self.new_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.file_frame, text="Load JSON", command=self.load_json_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.file_frame, text="Save As...", command=self.save_json_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.file_frame, text="Export PDF", command=self.export_to_pdf).pack(side=tk.LEFT, padx=5)

        # Grid Configuration
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.input_frame.columnconfigure(1, weight=1)
        self.progress_frame.columnconfigure(1, weight=1)
        self.list_frame.columnconfigure(0, weight=1)
        self.list_frame.rowconfigure(0, weight=1)

        self.update_participants_list()

    def add_participant(self):
        name = self.name_entry.get()
        age = self.age_entry.get()
        gender = self.gender_var.get()
        selected_advocacy_indices = self.advocacy_listbox.curselection()
        selected_advocacy = [self.advocacy_listbox.get(i) for i in selected_advocacy_indices]
        location = self.location_entry.get()
        iwi = self.iwi_entry.get()
        hapu = self.hapu_entry.get()
        signup_date = self.date_entry.get()
        kaimahi = self.kaimahi_var.get()

        if not all([name, age, gender, location, iwi, hapu, signup_date, kaimahi]):
            messagebox.showerror("Error", "All fields are required (including Kaimahi)")
            return
        try:
            datetime.strptime(signup_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
            return

        participant = Participant(name, age, gender, location, iwi, hapu, signup_date, selected_advocacy, kaimahi)
        participant.update_progress()
        self.participants.append(participant)
        self.save_data()
        self.update_participants_list()
        self.clear_inputs()

    def update_participant(self):
        if not self.current_participant:
            return

        name = self.name_entry.get()
        age = self.age_entry.get()
        gender = self.gender_var.get()
        selected_advocacy_indices = self.advocacy_listbox.curselection()
        selected_advocacy = [self.advocacy_listbox.get(i) for i in selected_advocacy_indices]
        location = self.location_entry.get()
        iwi = self.iwi_entry.get()
        hapu = self.hapu_entry.get()
        signup_date = self.date_entry.get()
        kaimahi = self.kaimahi_var.get()

        if not all([name, age, gender, location, iwi, hapu, signup_date, kaimahi]):
            messagebox.showerror("Error", "All fields are required (including Kaimahi)")
            return
        try:
            datetime.strptime(signup_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
            return

        for i, p in enumerate(self.participants):
            if p.name == self.current_participant.name and p.signup_date == self.current_participant.signup_date:
                new_p = Participant(name, age, gender, location, iwi, hapu, signup_date, selected_advocacy, kaimahi)
                new_p.phase = self.current_participant.phase
                new_p.weeks_completed = self.current_participant.weeks_completed
                new_p.programs = self.current_participant.programs
                new_p.weekly_progress = self.current_participant.weekly_progress
                new_p.red_phase_assessments = self.current_participant.red_phase_assessments
                new_p.advocacy_phase = self.current_participant.advocacy_phase
                new_p.advocacy_weeks_completed = self.current_participant.advocacy_weeks_completed
                new_p.advocacy_weekly_progress = self.current_participant.advocacy_weekly_progress
                new_p.kaimahi = kaimahi
                new_p.update_progress()
                self.participants[i] = new_p
                break

        self.save_data()
        self.update_participants_list()
        self.clear_inputs()
        self.current_participant = None
        self.update_button.config(state="disabled")
        self.select_program_button.config(state="disabled")
        self.assessment_button.config(state="disabled")

    def delete_participant(self):
        if not self.current_participant:
            return
        for i, p in enumerate(self.participants):
            if p.name == self.current_participant.name and p.signup_date == self.current_participant.signup_date:
                del self.participants[i]
                break
        self.save_data()
        self.update_participants_list()
        self.clear_inputs()
        self.current_participant = None
        self.update_button.config(state="disabled")
        self.select_program_button.config(state="disabled")
        self.assessment_button.config(state="disabled")

    def select_participant(self, event):
        selection = self.participants_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        # Use sorted_participants for correct mapping
        if hasattr(self, 'sorted_participants') and index < len(self.sorted_participants):
            self.current_participant = self.sorted_participants[index]
        else:
            self.current_participant = self.participants[index]
        self.current_participant.update_progress()

        # Clear displays first
        self.status_label.config(text="Status: Loading...")
        self.program_label.config(text="Program(s): Loading...")
        self.progress_canvas.delete("all")

        # Populate input fields
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.current_participant.name)
        self.age_entry.delete(0, tk.END)
        self.age_entry.insert(0, self.current_participant.age)
        self.gender_var.set(self.current_participant.gender)

        # Pre-select advocacy items
        self.advocacy_listbox.selection_clear(0, tk.END)
        if self.current_participant.advocacy:
            for i in range(self.advocacy_listbox.size()):
                if self.advocacy_listbox.get(i) in self.current_participant.advocacy:
                    self.advocacy_listbox.selection_set(i)

        self.location_entry.delete(0, tk.END)
        self.location_entry.insert(0, self.current_participant.location)
        self.iwi_entry.delete(0, tk.END)
        self.iwi_entry.insert(0, self.current_participant.iwi)
        self.hapu_entry.delete(0, tk.END)
        self.hapu_entry.insert(0, self.current_participant.hapu)
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, self.current_participant.signup_date.strftime("%Y-%m-%d"))

        # Set Kaimahi dropdown
        if hasattr(self.current_participant, "kaimahi") and self.current_participant.kaimahi in KAIMAHI_LIST:
            self.kaimahi_var.set(self.current_participant.kaimahi)
        else:
            self.kaimahi_var.set("")

        # Refresh progress display
        self.update_progress_display()

        # Enable buttons
        self.update_button.config(state="normal")
        self.select_program_button.config(state="normal")
        self.assessment_button.config(state="normal")
        self.review_assessment_button.config(state="normal")

    def set_programs(self):
        if not self.current_participant:
            messagebox.showinfo("Info", "No participant selected")
            return

        selected_indices = self.program_listbox.curselection()
        selected_programs = [self.program_listbox.get(i) for i in selected_indices]
        if not selected_programs:
            messagebox.showerror("Error", "Please select at least one program")
            return

        for p in self.participants:
            if p.name == self.current_participant.name and p.signup_date == self.current_participant.signup_date:
                p.programs = selected_programs
                break
        self.current_participant.programs = selected_programs
        self.save_data()
        self.update_progress_display()

    def show_assessment(self):
        if not self.current_participant or self.current_participant.phase != "red":
            messagebox.showinfo("Info", "Assessments are only available in the Red phase")
            return

        week = min(self.current_participant.weeks_completed + 1, 6)
        assessment_window = tk.Toplevel(self.root)
        assessment_window.title(f"Week {week} Assessment")
        assessment_window.geometry("500x400")
        assessment_window.resizable(False, False)

        questions = {
            1: "How well did you do to create a safe space for your whaiora?",
            2: "How did you do to allow your whaiora to express their māmae?",
            3: "How well did you prepare a pathway of purpose for your whaiora?",
            4: "How well have you identified what barriers your whaiora is facing?",
            5: "How confident are you in assuring you whaiora is ready to proceed with their pathway forward?",
            6: "General reflection on progress this week"
        }

        assessment = self.current_participant.red_phase_assessments.get(week, {"score": 0, "notes": ""})

        main_frame = ttk.Frame(assessment_window, padding=20)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text=questions[week], wraplength=450, font=(self.font_family, 10)).pack(pady=(0, 15))

        ttk.Label(main_frame, text="Score (0–10):", font=(self.font_family, 10, "bold")).pack(anchor="w", pady=(0, 5))
        score_var = tk.IntVar(value=assessment["score"])
        score_slider = ttk.Scale(main_frame, from_=0, to=10, variable=score_var, orient="horizontal", length=300)
        score_slider.pack(pady=5)

        tick_frame = ttk.Frame(main_frame)
        tick_frame.pack(pady=5)
        for i in range(11):
            ttk.Label(tick_frame, text=str(i), font=(self.font_family, 8), width=4, anchor="center").pack(side=tk.LEFT, expand=True, fill="x", padx=1)

        ttk.Label(main_frame, text="Notes:", font=(self.font_family, 10, "bold")).pack(anchor="w", pady=(10, 5))
        notes_text = tk.Text(main_frame, height=5, width=50, font=(self.font_family, 10))
        notes_text.insert("1.0", assessment["notes"])
        notes_text.pack(pady=5)

        def save_assessment():
            score = int(score_slider.get())
            notes = notes_text.get("1.0", tk.END).strip()
            self.current_participant.red_phase_assessments[week] = {"score": score, "notes": notes}
            for i, p in enumerate(self.participants):
                if p.name == self.current_participant.name and p.signup_date == self.current_participant.signup_date:
                    p.red_phase_assessments[week] = self.current_participant.red_phase_assessments[week]
                    break
            self.save_data()
            assessment_window.destroy()

        ttk.Button(main_frame, text="Save", command=save_assessment).pack(pady=(20, 0))
        assessment_window.transient(self.root)
        assessment_window.grab_set()
        assessment_window.focus_force()

    def update_progress_display(self):
        if not self.current_participant:
            return

        status_text = "Status: "
        if self.current_participant.phase == "red":
            status_text += f"Red (Whitiwhiti Kōrero) - Week {self.current_participant.weeks_completed + 1}/6"
        elif self.current_participant.phase == "orange":
            status_text += f"Orange (Program) - Week {self.current_participant.weeks_completed + 1}/8"
        elif self.current_participant.phase == "green":
            status_text += f"Green (Whānau Integration) - Week {self.current_participant.weeks_completed + 1}/12"
        elif self.current_participant.phase == "completed":
            status_text += "Completed 🎉"
        else:
            status_text += "Unknown"

        # Add Advocacy status if applicable
        if self.current_participant.advocacy and len(self.current_participant.advocacy) > 0:
            weeks = self.current_participant.advocacy_weeks_completed
            advocacy_names = ", ".join(self.current_participant.advocacy)
            if weeks < 52:
                months = int(weeks / 4.3)
                status_text += f" | Advocacy: {advocacy_names} ({months} mo)"
            else:
                years = int(weeks / 52)
                remaining_months = int((weeks % 52) / 4.3)
                if remaining_months > 0:
                    status_text += f" | Advocacy: {advocacy_names} ({years} yr, {remaining_months} mo)"
                else:
                    status_text += f" | Advocacy: {advocacy_names} ({years} yr)"

        self.status_label.config(text=status_text)
        program_text = f"Program(s): {', '.join(self.current_participant.programs)}" if self.current_participant.programs else "Program(s): Not selected"
        self.program_label.config(text=program_text)
        self.draw_progress_bar()

    def draw_progress_bar(self):
        self.progress_canvas.delete("all")
        if not self.current_participant:
            return

        total_weeks = 26
        cell_width = 520 / total_weeks
        bar_height = 25
        gap = 5
        today = datetime.now().date()
        current_week = (today - self.current_participant.signup_date).days // 7

        # Draw Standard 26-Week Bar (Top)
        y_offset_top = 5
        for week in range(total_weeks):
            x1 = week * cell_width
            x2 = x1 + cell_width
            y1 = y_offset_top
            y2 = y1 + bar_height

            color_key = self.current_participant.weekly_progress[week] if week < len(self.current_participant.weekly_progress) else ""

            NEON_COLORS = {
                "red":    {"fill": "#E53935", "outline": "#FF6B6B"},
                "orange": {"fill": "#F4511E", "outline": "#FFB347"},
                "green":  {"fill": "#388E3C", "outline": "#34C759"}
            }

            if color_key in NEON_COLORS:
                c = NEON_COLORS[color_key]
                fill = c["fill"]
                outline = "white" if week == current_week else c["outline"]
                width = 3 if week == current_week else 1
            else:
                fill = "#333"
                outline = "#555"
                width = 1

            self.progress_canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)
            self.progress_canvas.create_line(x1 + 2, y1 + 2, x2 - 2, y1 + 2, fill="white", width=1)

            # Show week number every 4 weeks
            if (week + 1) % 4 == 0 or week == 0 or week == total_weeks - 1:
                self.progress_canvas.create_text(
                    x1 + cell_width / 2,
                    y1 + bar_height / 2,
                    text=str(week + 1),
                    font=("Segoe UI", 7, "bold"),
                    fill="white"
                )

        # Draw Advocacy Bar (Bottom) - Grouped by ~4-month blocks
        if self.current_participant.advocacy and len(self.current_participant.advocacy) > 0:
            blocks = [
                (0, 17, "0-4mo"),
                (17, 34, "4-8mo"),
                (34, 51, "8-12mo"),
                (51, 68, "1-1.5yr"),
                (68, 85, "1.5-2yr"),
                (85, 102, "2-2.5yr"),
                (102, 119, "2.5-3yr"),
                (119, 136, "3-3.5yr"),
                (136, 153, "3.5-4yr"),
                (153, 208, "4yr+")
            ]

            y_offset_bottom = y_offset_top + bar_height + gap
            block_width = 520 / len(blocks)
            weeks_in = self.current_participant.advocacy_weeks_completed

            for i, (start_wk, end_wk, label) in enumerate(blocks):
                x1 = i * block_width
                x2 = x1 + block_width
                y1 = y_offset_bottom
                y2 = y1 + bar_height

                is_active = weeks_in >= start_wk
                is_current = start_wk <= weeks_in < end_wk

                if is_active:
                    fill = "#335DAB"
                    outline = "white" if is_current else "#335DAB"
                    width = 3 if is_current else 1
                else:
                    fill = "#333"
                    outline = "#555"
                    width = 1

                self.progress_canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)
                self.progress_canvas.create_line(x1 + 2, y1 + 2, x2 - 2, y1 + 2, fill="white", width=1)

                # Label below block
                self.progress_canvas.create_text(
                    x1 + block_width / 2,
                    y2 + 10,
                    text=label,
                    font=("Segoe UI", 7),
                    fill="white" if is_active else "#AAA",
                    anchor="n"
                )

    def show_statistics(self):
        if self.statistics_window and self.statistics_window.winfo_exists():
            self.statistics_window.lift()
            return
        if not self.participants:
            messagebox.showinfo("No Data", "No participant data available")
            return

        self.statistics_window = tk.Toplevel(self.root)
        self.statistics_window.title("Program Statistics")
        notebook = ttk.Notebook(self.statistics_window)
        notebook.pack(fill="both", expand=True)

        program_frame = ttk.Frame(notebook)
        gender_frame = ttk.Frame(notebook)
        gender_program_frame = ttk.Frame(notebook)
        iwi_frame = ttk.Frame(notebook)

        notebook.add(program_frame, text="Program Distribution")
        notebook.add(gender_frame, text="Gender Distribution")
        notebook.add(gender_program_frame, text="Program by Gender")
        notebook.add(iwi_frame, text="Iwi Distribution")
        advocacy_frame = ttk.Frame(notebook)
        notebook.add(advocacy_frame, text="Advocacy Distribution")

        programs = ["Ko wai au", "Mental Health and Well-being", "Anger Management", "Domestic Violence"]
        genders = ["Male", "Female", "Non-binary"]

        # Program Distribution
        program_counts = {p: sum(1 for part in self.participants if p in part.programs) for p in programs}
        values = list(program_counts.values())
        labels = list(program_counts.keys())
        if sum(values) == 0:
            values = [1]
            labels = ["No Programs Assigned"]
            autopct = None
        else:
            autopct = '%1.1f%%'
        fig1, ax1 = plt.subplots(figsize=(5, 4))
        ax1.pie(values, labels=labels, autopct=autopct, startangle=90)
        ax1.axis('equal')
        canvas1 = FigureCanvasTkAgg(fig1, master=program_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True)

        # Gender Distribution
        gender_counts = {g: sum(1 for part in self.participants if part.gender == g) for g in genders}
        values = list(gender_counts.values())
        labels = list(gender_counts.keys())
        if sum(values) == 0:
            values = [1]
            labels = ["No Data"]
            autopct = None
        else:
            autopct = '%1.1f%%'
        fig2, ax2 = plt.subplots(figsize=(5, 4))
        ax2.pie(values, labels=labels, autopct=autopct, startangle=90)
        ax2.axis('equal')
        canvas2 = FigureCanvasTkAgg(fig2, master=gender_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True)

        # Program by Gender
        allowed_genders = ["Male", "Female", "Non-binary"]
        data_rows = []
        for p in self.participants:
            if p.gender in allowed_genders:
                if p.programs:
                    for prog in p.programs:
                        data_rows.append({'gender': p.gender, 'program': prog})
                else:
                    data_rows.append({'gender': p.gender, 'program': 'No Program'})
        df = pd.DataFrame(data_rows)
        if not df.empty:
            try:
                gender_program_data = pd.crosstab(df['gender'], df['program'])
                if not gender_program_data.empty:
                    fig3, ax3 = plt.subplots(figsize=(8, 6))
                    gender_program_data.plot(kind='bar', stacked=True, ax=ax3)
                    ax3.set_ylabel("Count")
                    ax3.set_title("Program Participation by Gender")
                    ax3.legend(title="Program")
                    canvas3 = FigureCanvasTkAgg(fig3, master=gender_program_frame)
                    canvas3.draw()
                    canvas3.get_tk_widget().pack(fill="both", expand=True)
                else:
                    label = ttk.Label(gender_program_frame, text="No program data to display", font=("Helvetica", 12))
                    label.pack(pady=20)
            except Exception as e:
                print(f"Error generating Program by Gender chart in stats: {e}")
                label = ttk.Label(gender_program_frame, text="Error generating chart", font=("Helvetica", 12))
                label.pack(pady=20)
        else:
            label = ttk.Label(gender_program_frame, text="No data available", font=("Helvetica", 12))
            label.pack(pady=20)

        # Iwi Distribution
        iwi_counts = {}
        for p in self.participants:
            iwi = p.iwi if p.iwi else "Not specified"
            iwi_counts[iwi] = iwi_counts.get(iwi, 0) + 1
        if len(iwi_counts) > 8:
            total = sum(iwi_counts.values())
            threshold = total * 0.05
            grouped = {k: v for k, v in iwi_counts.items() if v >= threshold}
            other = sum(v for k, v in iwi_counts.items() if v < threshold)
            if other > 0:
                grouped["Other"] = other
            iwi_counts = grouped
        values = list(iwi_counts.values())
        labels = list(iwi_counts.keys())
        if sum(values) == 0:
            values = [1]
            labels = ["No Data"]
            autopct = None
        else:
            autopct = '%1.1f%%'
        fig4, ax4 = plt.subplots(figsize=(8, 6))
        ax4.pie(values, labels=labels, autopct=autopct, startangle=90)
        ax4.axis('equal')
        ax4.set_title("Participants by Iwi Affiliation")
        canvas4 = FigureCanvasTkAgg(fig4, master=iwi_frame)
        canvas4.draw()
        canvas4.get_tk_widget().pack(fill="both", expand=True)

        # ===== 5. Advocacy Distribution =====
        # Count total participants with advocacy
        total_with_advocacy = sum(1 for p in self.participants if p.advocacy and len(p.advocacy) > 0)
        total_without_advocacy = len(self.participants) - total_with_advocacy

        # Pie chart: With vs Without Advocacy
        fig5, ax5 = plt.subplots(figsize=(5, 4))
        labels = ['With Advocacy', 'Without Advocacy']
        sizes = [total_with_advocacy, total_without_advocacy]
        colors = ['#5D4037', '#BDBDBD']  # Brown for advocacy, gray for none
        if sum(sizes) == 0:
            sizes = [1]
            labels = ["No Data"]
            autopct = None
        else:
            autopct = '%1.1f%%'
        ax5.pie(sizes, labels=labels, autopct=autopct, colors=colors, startangle=90)
        ax5.axis('equal')
        ax5.set_title("Participants with Advocacy")
        canvas5 = FigureCanvasTkAgg(fig5, master=advocacy_frame)
        canvas5.draw()
        canvas5.get_tk_widget().pack(fill="both", expand=True)

        # Breakdown by Advocacy Type
        advocacy_type_counts = {atype: 0 for atype in ADVOCACY_TYPES}
        for p in self.participants:
            for atype in getattr(p, 'advocacy', []):
                if atype in advocacy_type_counts:
                    advocacy_type_counts[atype] += 1

        # Bar chart: Advocacy Type Distribution
        # Use 'OT' instead of 'Oranga Tamariki' for label clarity
        types = [t if t != 'Oranga Tamariki' else 'OT' for t in advocacy_type_counts.keys()]
        counts = list(advocacy_type_counts.values())
        fig6, ax6 = plt.subplots(figsize=(10, 5))
        bars = ax6.bar(types, counts, color='#5D4037')
        ax6.set_title("Advocacy Type Distribution")
        ax6.set_ylabel("Number of Participants")
        ax6.tick_params(axis='x', rotation=30, labelsize=11)
        ax6.margins(x=0.05)
        fig6.tight_layout()

        # (No value labels on top of bars)

        canvas6 = FigureCanvasTkAgg(fig6, master=advocacy_frame)
        canvas6.draw()
        canvas6.get_tk_widget().pack(fill="both", expand=True, pady=(20, 0))

        # Duration Distribution (for those with advocacy)
        duration_bins = {
            "<1 Year": 0,
            "1-2 Years": 0,
            "2-3 Years": 0,
            "3-4 Years": 0,
            "4+ Years": 0
        }

        for p in self.participants:
            if getattr(p, 'advocacy', None) and len(p.advocacy) > 0:
                weeks = getattr(p, 'advocacy_weeks_completed', 0)
                years = weeks / 52.0
                if years < 1:
                    duration_bins["<1 Year"] += 1
                elif years < 2:
                    duration_bins["1-2 Years"] += 1
                elif years < 3:
                    duration_bins["2-3 Years"] += 1
                elif years < 4:
                    duration_bins["3-4 Years"] += 1
                else:
                    duration_bins["4+ Years"] += 1

        # Pie chart: Duration Distribution
        fig7, ax7 = plt.subplots(figsize=(5, 4))
        labels = list(duration_bins.keys())
        sizes = list(duration_bins.values())
        colors_duration = ['#FFB347', '#FF8C00', '#E53935', '#B71C1C', '#5D4037']
        if sum(sizes) == 0:
            sizes = [1]
            labels = ["No Advocacy Participants"]
            autopct = None
        else:
            autopct = '%1.1f%%'
        ax7.pie(sizes, labels=labels, autopct=autopct, colors=colors_duration, startangle=90)
        ax7.axis('equal')
        ax7.set_title("Advocacy Duration Distribution")
        canvas7 = FigureCanvasTkAgg(fig7, master=advocacy_frame)
        canvas7.draw()
        canvas7.get_tk_widget().pack(fill="both", expand=True, pady=(20, 0))

        self.statistics_window.protocol("WM_DELETE_WINDOW", lambda: self.on_stats_window_close())

    def on_stats_window_close(self):
        if self.statistics_window:
            self.statistics_window.destroy()
        self.statistics_window = None

    def update_participants_list(self):
        self.participants_listbox.delete(0, tk.END)
        # Store sorted list for correct selection mapping
        self.sorted_participants = sorted(self.participants, key=lambda x: x.signup_date)
        for p in self.sorted_participants:
            status = f"{p.name} ({p.age}, {p.gender}) - {p.phase.upper()}"
            if p.phase == "orange" and p.programs:
                status += f" - {', '.join(p.programs)}"
            self.participants_listbox.insert(tk.END, status)

    def clear_inputs(self):
        self.name_entry.delete(0, tk.END)
        self.age_entry.delete(0, tk.END)
        self.gender_var.set("")
        self.advocacy_listbox.selection_clear(0, tk.END)
        self.location_entry.delete(0, tk.END)
        self.iwi_entry.delete(0, tk.END)
        self.hapu_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)

    def load_data(self):
        try:
            if os.path.exists(JSON_PATH):
                with open(JSON_PATH, "r") as f:
                    data = json.load(f)
                self.participants = [Participant.from_dict(item) for item in data]
                print(f"Successfully loaded {len(self.participants)} participants")
            else:
                self.participants = []
        except Exception as e:
            print(f"Error loading data: {e}")
            self.participants = []

    def save_data(self):
        data = [p.to_dict() for p in self.participants]
        with open("participants.json", "w") as f:
            json.dump(data, f, indent=2)

    def review_assessments(self):
        if not self.current_participant:
            messagebox.showinfo("Info", "No participant selected")
            return

        review_window = tk.Toplevel(self.root)
        review_window.title(f"Weekly Assessments - {self.current_participant.name}")
        review_window.geometry("600x500")

        bg_color = self.bg_color
        fg_color = self.fg_color
        card_bg = self.card_bg
        accent_color = self.accent_color

        canvas = tk.Canvas(review_window, bg=bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(review_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        title_label = tk.Label(
            scrollable_frame,
            text="Weekly Assessment Review",
            font=(self.font_family, 16, "bold"),
            bg=bg_color,
            fg=fg_color
        )
        title_label.pack(pady=(20, 10))

        questions = {
            1: "How well did you do to create a safe space for your whaiora?",
            2: "How did you do to allow your whaiora to express their māmae?",
            3: "How well did you prepare a pathway of purpose for your whaiora?",
            4: "How well have you identified what barriers your whaiora is facing?",
            5: "How confident are you in assuring you whaiora is ready to proceed with their pathway forward?",
            6: "General reflection on progress this week"
        }

        for week_num in range(1, 7):
            assessment = self.current_participant.red_phase_assessments[week_num]
            score = assessment["score"]
            notes = assessment["notes"]

            card = tk.Frame(scrollable_frame, bg=card_bg, relief="flat", bd=0)
            card.pack(fill="x", padx=20, pady=8)

            week_label = tk.Label(
                card,
                text=f"Week {week_num}",
                font=(self.font_family, 12, "bold"),
                bg=card_bg,
                fg=accent_color
            )
            week_label.pack(anchor="w", padx=10, pady=(5, 2))

            question_label = tk.Label(
                card,
                text=questions[week_num],
                wraplength=520,
                justify="left",
                font=(self.font_family, 9, "italic"),
                bg=card_bg,
                fg=fg_color
            )
            question_label.pack(anchor="w", padx=10, pady=(0, 5))

            score_label = tk.Label(
                card,
                text=f"Score: {score}/10",
                font=(self.font_family, 10, "bold"),
                bg=card_bg,
                fg=fg_color
            )
            score_label.pack(anchor="w", padx=10, pady=(0, 5))

            if notes.strip():
                note_text = tk.Label(
                    card,
                    text=notes,
                    wraplength=500,
                    justify="left",
                    font=(self.font_family, 9),
                    bg=card_bg,
                    fg=fg_color
                )
                note_text.pack(anchor="w", padx=15, pady=(0, 5))
            else:
                no_notes = tk.Label(
                    card,
                    text="No notes provided.",
                    font=(self.font_family, 9),
                    bg=card_bg,
                    fg="#AAAAAA"
                )
                no_notes.pack(anchor="w", padx=15, pady=(0, 5))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        ttk.Button(review_window, text="Close", command=review_window.destroy).pack(pady=10)

    def apply_theme(self):
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass

        bg_color = self.bg_color           # "#1A3A2A"
        fg_color = self.fg_color           # "#FFFFFF"
        primary = self.primary_color       # "#1A3A2A"
        accent = self.accent_color         # "#4CAF50"
        card_bg = self.card_bg             # "#444444" ← THIS IS THE GREY WE WANT
        border = self.border_color         # "#1A3A2A"
        progress_bg = self.progress_bg     # "#444444"
        font = (self.font_family, 10)

        # --- CORE STYLING ---
        style.configure("TLabel", background=bg_color, foreground=fg_color, font=font)
        style.configure("TButton", background=primary, foreground="white", font=(self.font_family, 10, "bold"), padding=6)
        style.map("TButton", background=[('active', '#2E5D3E')], relief=[('pressed', 'sunken')])
        style.configure("TLabelframe", background="#2E5D3E", foreground="white", font=(self.font_family, 12, "bold"), borderwidth=2, relief="flat")
        style.configure("TLabelframe.Label", background="#2E5D3E", foreground="white", font=(self.font_family, 12, "bold"))

        # --- CRITICAL FIX FOR TCombobox ON CLAM THEME ---
        # Must set ALL properties that clam uses internally
        style.configure("TCombobox",
                        fieldbackground=card_bg,      # Text entry background
                        background=card_bg,           # Dropdown button background
                        foreground=fg_color,          # Text color
                        selectbackground=card_bg,     # Selected item background — KEY!
                        selectforeground=fg_color,    # Selected item text color — KEY!
                        arrowsize=14)                 # Arrow size

        # Also ensure dropdown menu matches (optional, improves consistency)
        style.map("TCombobox",
                  fieldbackground=[('readonly', card_bg)],
                  background=[('readonly', card_bg)],
                  foreground=[('readonly', fg_color)])

        # Ensure Entry widgets match
        style.configure("TEntry", fieldbackground=card_bg, background=card_bg, foreground=fg_color, insertcolor=fg_color)

        # --- Apply background to root and custom Tk widgets ---
        self.root.configure(bg=bg_color)

        tk_widgets = [
            self.participants_listbox,
            self.progress_canvas,
            self.program_listbox,
            self.advocacy_listbox
        ]
        for widget in tk_widgets:
            try:
                if isinstance(widget, tk.Listbox):
                    widget.configure(
                        bg=card_bg,
                        fg=fg_color,
                        selectbackground=primary,
                        selectforeground="white",
                        highlightbackground=border,
                        bd=0
                    )
                elif isinstance(widget, tk.Canvas):
                    widget.configure(bg=progress_bg, highlightbackground=border)
            except Exception as e:
                print(f"Error styling widget {widget}: {e}")

        self.draw_progress_bar()
        self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    splash = tk.Toplevel()
    splash.overrideredirect(True)
    splash.config(bg='white')
    splash_width, splash_height = 400, 400
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    splash.geometry(f"{splash_width}x{splash_height}+{screen_w//2 - 200}+{screen_h//2 - 200}")
    splash.resizable(False, False)

    try:
        from PIL import Image, ImageTk
        koru_path = r"c:\Day trading indicator bot\koru_outline.png"
        if not os.path.exists(koru_path):
            raise FileNotFoundError(f"Image not found: {koru_path}")

        pil_image = Image.open(koru_path)
        pil_image = pil_image.resize((300, 300), Image.Resampling.LANCZOS)
        photo_image = ImageTk.PhotoImage(pil_image)

        canvas = tk.Canvas(splash, width=300, height=300, bg='white', highlightthickness=0)
        canvas.pack(expand=True)
        canvas.create_image(150, 150, image=photo_image)
        splash.image = photo_image

        ttk.Label(splash, text="Loading Tu Pono Tracker...", font=("Segoe UI", 12)).pack(pady=10)
    except Exception as e:
        print(f"Splash screen error: {e}")
        ttk.Label(splash, text="Loading Tu Pono Tracker...", font=("Segoe UI", 16)).pack(expand=True, pady=100)

    def show_password_prompt():
        splash.destroy()
        password = simpledialog.askstring(
            "Password Required",
            "Enter password to access the Māori Support Program Tracker:\n(Case-sensitive)",
            show="*",
            parent=root
        )
        if password == "ElwynPakeha":
            root.deiconify()
            try:
                app = ProgramTrackerApp(root)
                root.mainloop()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start app: {str(e)}")
                root.destroy()
        else:
            messagebox.showerror("Access Denied", "Incorrect password. Closing application.")
            root.destroy()

    splash.after(2000, show_password_prompt)
    root.mainloop()