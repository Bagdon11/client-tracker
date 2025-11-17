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
ADVOCACY_TYPES = ["Family harm", "Sexual harm", "Mental health", "Oranga Tamariki"]
# Durations: Min 6 months (~26 weeks), Max 4 years (~208 weeks)
ADVOCACY_MIN_WEEKS = 26
ADVOCACY_MAX_WEEKS = 208

JSON_PATH = os.path.join(os.path.dirname(__file__), "participants.json")
print(f"JSON_PATH resolved to: {JSON_PATH}")
print(f"File exists: {os.path.exists(JSON_PATH)}")

# pyinstaller --onefile --windowed --add-data "koru_outline.png;." --name "TuPonoTracker" "TuPonoTracker_FinalCopy.py"

class Participant:
    def __init__(self, name, age, gender, location, iwi, hapu, signup_date, advocacy=None):
        self.name = name
        self.age = age
        self.gender = gender
        self.location = location
        self.iwi = iwi
        self.hapu = hapu
        self.advocacy = advocacy if isinstance(advocacy, list) else []  # Always a list
        self.signup_date = datetime.strptime(signup_date, "%Y-%m-%d").date()
        self.phase = "red"  # red, orange, green, completed
        self.weeks_completed = 0
        self.programs = []  # Now supports multiple programs
        self.weekly_progress = []  # For the 26-week program

        # === NEW: Advocacy Tracking Attributes ===
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

        # --- NEW: Update Long-Term Advocacy Progress (if applicable) ---
        if self.advocacy and self.advocacy != "None":
            self.advocacy_phase = "active"
            self.advocacy_weeks_completed = min(weeks_since_signup, ADVOCACY_MAX_WEEKS)

            # Build the advocacy progress bar (up to max duration)
            self.advocacy_weekly_progress = []
            for week in range(ADVOCACY_MAX_WEEKS):
                if week < weeks_since_signup:
                    self.advocacy_weekly_progress.append("advocacy_active")
                else:
                    self.advocacy_weekly_progress.append("")

            # Optionally, mark as 'completed' if they've been in for the max duration
            # if weeks_since_signup >= ADVOCACY_MAX_WEEKS:
            #     self.advocacy_phase = "completed"
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
            # === UPDATED: Store advocacy as list ===
            "advocacy": self.advocacy  # Now a list
        }

    @classmethod
    def from_dict(cls, data):
        try:
            # --- Pass advocacy to __init__ ---
            participant = cls(
                data["name"],
                data["age"],
                data.get("gender", "Not specified"),
                data["location"],
                data["iwi"],
                data["hapu"],
                data["signup_date"],
                data.get("advocacy", "None") # <-- Pass advocacy here
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

            # === NEW: Load advocacy tracking data ===
            participant.advocacy = data.get("advocacy", "None")
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
        self.card_bg = "#444444"            # White cards
        self.border_color = "#1A3A2A"       # Dark green borders
        self.progress_bg = "#444444"        # Light gray for progress bar bg
        self.font_family = "Segoe UI"
        print("Colors initialized...")
        
        print("Loading data...")
        self.load_data()
        print("Creating widgets...")
        self.create_widgets()
        print("Applying theme...")
        self.apply_theme()  # Apply theme after widgets are created
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

        # === Show "Please Wait" dialog ===
        wait_window = tk.Toplevel(self.root)
        wait_window.title("Generating Report")
        wait_window.geometry("300x100")
        wait_window.resizable(False, False)
        wait_window.transient(self.root)
        wait_window.grab_set()  # Block interaction
        wait_window.focus_set()

        label = ttk.Label(wait_window, text="Generating PDF...\nPlease wait", font=("Helvetica", 12))
        label.pack(expand=True)

        # Prevent window from being closed
        wait_window.protocol("WM_DELETE_WINDOW", lambda: None)

        self.root.update_idletasks()  # Force UI to show the dialog

        # === Run export in background ===
        def do_export():
            try:
                pdf = FPDF(orientation='P', unit='mm', format='A4')
                pdf.set_auto_page_break(auto=True, margin=15)

                # ===== 1. Cover Page =====
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 24)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 20, "Tu Pono IP - Full Report", 0, 1, "C")
                pdf.ln(10)
                pdf.set_font("Helvetica", "", 14)
                pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")
                pdf.ln(20)

               
                # ===== 2. Charts =====
                charts = self._generate_all_charts()
                for chart_name, fig in charts.items():
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
                # Close wait window after export
                try:
                    wait_window.destroy()
                except:
                    pass

        # Run export after a tiny delay to ensure window appears
        wait_window.after(100, do_export)
    
    def _generate_all_charts(self):
        """Generate all statistical charts as matplotlib figures (safe for PDF/UI)"""
        charts = {}
        programs = ["Ko wai au", "Mental Health and Well-being", "Anger Management", "Domestic Violence"]
        # Only include approved genders
        allowed_genders = ["Male", "Female", "Non-binary"]

        # === 1. Program Distribution ===
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

        # === 2. Gender Distribution ===
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

    # === 3. Iwi Affiliation ===
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

        # === 4. Program by Gender ===
        data_rows = []
        for p in self.participants:
            if p.gender in allowed_genders:  # ✅ Only include allowed genders
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
                pass  # Skip if error

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

        ttk.Label(self.input_frame, text="Name:").grid(row=0, column=0, sticky="w")
        self.name_entry = ttk.Entry(self.input_frame)
        self.name_entry.grid(row=0, column=1, pady=5, sticky="ew")
        
        

        ttk.Label(self.input_frame, text="Age:").grid(row=1, column=0, sticky="w")
        self.age_entry = ttk.Entry(self.input_frame)
        self.age_entry.grid(row=1, column=1, pady=5, sticky="ew")

    # Gender Dropdown
        ttk.Label(self.input_frame, text="Gender:").grid(row=2, column=0, sticky="w")
        self.gender_var = tk.StringVar()
        self.gender_dropdown = ttk.Combobox(self.input_frame, textvariable=self.gender_var,
                        values=["Male", "Female", "Non-binary"])
        self.gender_dropdown.grid(row=2, column=1, pady=5, sticky="ew")

        # === REPLACED: Advocacy Multi-Select Listbox ===
        ttk.Label(self.input_frame, text="Advocacy:").grid(row=3, column=0, sticky="w")
        self.advocacy_listbox = tk.Listbox(self.input_frame, height=4, selectmode="multiple")
        for a in ["Family harm", "Sexual harm", "Mental health", "Oranga Tamariki"]:
            self.advocacy_listbox.insert(tk.END, a)
        self.advocacy_listbox.grid(row=3, column=1, pady=5, sticky="ew")

        # Move "Location" and subsequent fields down by one row
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
        self.add_button.grid(row=8, column=0, columnspan=2, pady=10, sticky="ew")

        self.update_button = ttk.Button(self.input_frame, text="Update Participant", command=self.update_participant, state="disabled")
        self.update_button.grid(row=9, column=0, columnspan=2, pady=5, sticky="ew")

        self.status_label = ttk.Label(self.progress_frame, text="Status: Not selected", font=('Helvetica', 12))
        self.status_label.grid(row=0, column=0, columnspan=2, pady=5, sticky="w")

        self.program_label = ttk.Label(self.progress_frame, text="Program(s): Not selected", font=('Helvetica', 12))
        self.program_label.grid(row=1, column=0, columnspan=2, pady=5, sticky="w")

        ttk.Label(self.progress_frame, text="Weekly Progress:").grid(row=2, column=0, columnspan=2, pady=5, sticky="w")

        
        self.progress_canvas.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")

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

        self.participants_listbox = tk.Listbox(self.list_frame, height=10)
        self.participants_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.participants_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.participants_listbox.config(yscrollcommand=scrollbar.set)
        self.participants_listbox.bind("<<ListboxSelect>>", self.select_participant)

        self.delete_button = ttk.Button(self.list_frame, text="Delete Participant", command=self.delete_participant)
        self.delete_button.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        self.file_frame = ttk.Frame(self.root)
        self.file_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        ttk.Button(self.file_frame, text="New", command=self.new_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.file_frame, text="Load JSON", command=self.load_json_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.file_frame, text="Save As...", command=self.save_json_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.file_frame, text="Export PDF", command=self.export_to_pdf).pack(side=tk.LEFT, padx=5)
        
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
        # === NEW: Get multiple selected advocacy items ===
        selected_advocacy_indices = self.advocacy_listbox.curselection()
        selected_advocacy = [self.advocacy_listbox.get(i) for i in selected_advocacy_indices]
        location = self.location_entry.get()
        iwi = self.iwi_entry.get()
        hapu = self.hapu_entry.get()
        signup_date = self.date_entry.get()
        name = self.name_entry.get()
        age = self.age_entry.get()
        if not all([name, age, gender, location, iwi, hapu, signup_date]):
            messagebox.showerror("Error", "All fields are required")
            return
        try:
            datetime.strptime(signup_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
            return
        # --- Pass advocacy to Participant constructor ---
        participant = Participant(name, age, gender, location, iwi, hapu, signup_date, selected_advocacy)
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
        # === NEW: Get multiple selected advocacy items ===
        selected_advocacy_indices = self.advocacy_listbox.curselection()
        selected_advocacy = [self.advocacy_listbox.get(i) for i in selected_advocacy_indices]
        location = self.location_entry.get()
        iwi = self.iwi_entry.get()
        hapu = self.hapu_entry.get()
        signup_date = self.date_entry.get()
        name = self.name_entry.get()
        age = self.age_entry.get()
        if not all([name, age, gender, location, iwi, hapu, signup_date]):
            messagebox.showerror("Error", "All fields are required")
            return
        try:
            datetime.strptime(signup_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
            return

        for i, p in enumerate(self.participants):
            if p.name == self.current_participant.name and p.signup_date == self.current_participant.signup_date:
                # --- Pass advocacy to new Participant ---
                new_p = Participant(name, age, gender, location, iwi, hapu, signup_date, selected_advocacy)
                new_p.phase = self.current_participant.phase
                new_p.weeks_completed = self.current_participant.weeks_completed
                new_p.programs = self.current_participant.programs
                new_p.weekly_progress = self.current_participant.weekly_progress
                new_p.red_phase_assessments = self.current_participant.red_phase_assessments

                # --- Copy advocacy progress data ---
                new_p.advocacy_phase = self.current_participant.advocacy_phase
                new_p.advocacy_weeks_completed = self.current_participant.advocacy_weeks_completed
                new_p.advocacy_weekly_progress = self.current_participant.advocacy_weekly_progress

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
        self.current_participant = self.participants[index]
        self.current_participant.update_progress()  # Ensure data is fresh

        # --- CLEAR ALL DISPLAYS FIRST ---
        self.status_label.config(text="Status: Loading...")
        self.program_label.config(text="Program(s): Loading...")
        self.progress_canvas.delete("all")  # Force canvas clear

        # --- POPULATE INPUT FIELDS ---
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.current_participant.name)
        self.age_entry.delete(0, tk.END)
        self.age_entry.insert(0, self.current_participant.age)
        self.gender_var.set(self.current_participant.gender)

        # === NEW: Pre-select advocacy items in Listbox ===
        self.advocacy_listbox.selection_clear(0, tk.END)  # Clear all selections first
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

        # --- FULLY REFRESH PROGRESS DISPLAY ---
        self.update_progress_display()  # This will call draw_progress_bar()

        # --- ENABLE BUTTONS ---
        self.update_button.config(state="normal")
        self.select_program_button.config(state="normal")
        self.assessment_button.config(state="normal")
        self.review_assessment_button.config(state="normal")

    def set_programs(self):
        if not self.current_participant:
            messagebox.showinfo("Info", "No participant selected")
            return
    # Allow program selection in any phase
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

        ttk.Label(
            main_frame,
            text=questions[week],
            wraplength=450,
            font=(self.font_family, 10)
        ).pack(pady=(0, 15))

        ttk.Label(
            main_frame,
            text="Score (0–10):",
            font=(self.font_family, 10, "bold")
        ).pack(anchor="w", pady=(0, 5))

        score_var = tk.IntVar(value=assessment["score"])
        score_slider = ttk.Scale(
            main_frame,
            from_=0,
            to=10,
            variable=score_var,
            orient="horizontal",
            length=300
        )
        score_slider.pack(pady=5)

        tick_frame = ttk.Frame(main_frame)
        tick_frame.pack(pady=5)
        for i in range(11):
            ttk.Label(
                tick_frame,
                text=str(i),
                font=(self.font_family, 8),
                width=4,
                anchor="center"
            ).pack(side=tk.LEFT, expand=True, fill="x", padx=1)

        ttk.Label(
            main_frame,
            text="Notes:",
            font=(self.font_family, 10, "bold")
        ).pack(anchor="w", pady=(10, 5))

        notes_text = tk.Text(
            main_frame,
            height=5,
            width=50,
            font=(self.font_family, 10)
        )
        notes_text.insert("1.0", assessment["notes"])
        notes_text.pack(pady=5)

        def save_assessment():
            score = int(score_slider.get())
            notes = notes_text.get("1.0", tk.END).strip()
            self.current_participant.red_phase_assessments[week] = {"score": score, "notes": notes}
            print(f"Saved assessment for {self.current_participant.name}, Week {week}: {self.current_participant.red_phase_assessments[week]}")
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

        # --- NEW: Format Advocacy Duration Readably (for advocacy as a list) ---
        if self.current_participant.advocacy and len(self.current_participant.advocacy) > 0:
            weeks = self.current_participant.advocacy_weeks_completed
            # Format advocacy names
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
        self.draw_progress_bar()  # Redraw everything


    def draw_progress_bar(self):
        self.progress_canvas.delete("all")
        if not self.current_participant:
            return

        # === CONFIGURE SIZES ===
        total_weeks = 26
        cell_width = 520 / total_weeks
        bar_height = 25  # Reduced from 40 to fit two bars
        gap = 5          # Small gap between bars

        today = datetime.now().date()
        current_week = (today - self.current_participant.signup_date).days // 7

        # === DRAW STANDARD 26-WEEK BAR (TOP) ===
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

            # Show week number every 4 weeks for readability
            if (week + 1) % 4 == 0 or week == 0 or week == total_weeks - 1:
                self.progress_canvas.create_text(
                    x1 + cell_width / 2,
                    y1 + bar_height / 2,
                    text=str(week + 1),
                    font=("Segoe UI", 7, "bold"),
                    fill="white"
                )

        # === DRAW ADVOCACY BAR (BOTTOM) — GROUPED BY 4-MONTH BLOCKS ===
        if self.current_participant.advocacy and len(self.current_participant.advocacy) > 0:
            # Define 4-month blocks (approx 17 weeks each)
            # Total range: 6 months (26 wks) to 4 years (208 wks)
            # We'll create blocks: 0-4mo, 4-8mo, 8-12mo, 1yr-1.5yr, 1.5yr-2yr, 2yr-2.5yr, 2.5yr-3yr, 3yr-3.5yr, 3.5yr-4yr
            # But for simplicity and spacing, let's do 9 blocks of ~4 months (17 weeks) covering 0 to 153 weeks (~3.5 years)
            # Plus a final block for "3.5yr+" to cover up to 4 years (208 weeks)

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

            y_offset_bottom = y_offset_top + bar_height + gap  # Position below first bar
            block_width = 520 / len(blocks)

            weeks_in = self.current_participant.advocacy_weeks_completed

            for i, (start_wk, end_wk, label) in enumerate(blocks):
                x1 = i * block_width
                x2 = x1 + block_width
                y1 = y_offset_bottom
                y2 = y1 + bar_height

                # Check if this block is active (participant has reached this point)
                is_active = weeks_in >= start_wk
                is_current = start_wk <= weeks_in < end_wk  # Currently in this block

                if is_active:
                    fill = "#5D4037"  # Brown for advocacy
                    outline = "white" if is_current else "#8D6E63"
                    width = 3 if is_current else 1
                else:
                    fill = "#333"
                    outline = "#555"
                    width = 1

                self.progress_canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)
                self.progress_canvas.create_line(x1 + 2, y1 + 2, x2 - 2, y1 + 2, fill="white", width=1)

                # Draw label below the block
                self.progress_canvas.create_text(
                    x1 + block_width / 2,
                    y2 + 10,  # Below the bar
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

        # Create frames
        program_frame = ttk.Frame(notebook)
        gender_frame = ttk.Frame(notebook)
        gender_program_frame = ttk.Frame(notebook)
        iwi_frame = ttk.Frame(notebook)

        # Add tabs
        notebook.add(program_frame, text="Program Distribution")
        notebook.add(gender_frame, text="Gender Distribution")
        notebook.add(gender_program_frame, text="Program by Gender")
        notebook.add(iwi_frame, text="Iwi Distribution")

        programs = ["Ko wai au", "Mental Health and Well-being", "Anger Management", "Domestic Violence"]
        genders = ["Male", "Female", "Non-binary"]

        # ===== 1. Program Distribution =====
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

        # ===== 2. Gender Distribution =====
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

        # ===== 3. Program by Gender =====
        
                # ===== 3. Program by Gender =====
        allowed_genders = ["Male", "Female", "Non-binary"]
        data_rows = []
        for p in self.participants:
            if p.gender in allowed_genders:  # ✅ Filter out "Other" and "Prefer not to say"
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
                    label = ttk.Label(gender_program_frame, text="No program data to display", 
                                    font=("Helvetica", 12))
                    label.pack(pady=20)
            except Exception as e:
                print(f"Error generating Program by Gender chart in stats: {e}")
                label = ttk.Label(gender_program_frame, text="Error generating chart", 
                                font=("Helvetica", 12))
                label.pack(pady=20)
        else:
            label = ttk.Label(gender_program_frame, text="No data available", 
                            font=("Helvetica", 12))
            label.pack(pady=20)
        

        # ===== 4. Iwi Distribution =====
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

        self.statistics_window.protocol("WM_DELETE_WINDOW", lambda: self.on_stats_window_close())

    def on_stats_window_close(self):
        if self.statistics_window:
            self.statistics_window.destroy()
        self.statistics_window = None

    def update_participants_list(self):
        self.participants_listbox.delete(0, tk.END)
        for p in sorted(self.participants, key=lambda x: x.signup_date):
            status = f"{p.name} ({p.age}, {p.gender}) - {p.phase.upper()}"
            if p.phase == "orange" and p.programs:
                status += f" - {', '.join(p.programs)}"
            self.participants_listbox.insert(tk.END, status)

    def clear_inputs(self):
        self.name_entry.delete(0, tk.END)
        self.age_entry.delete(0, tk.END)
        self.gender_var.set("")
    # === NEW: Clear advocacy selection ===
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

        # Use app's theme colors
        bg_color = self.bg_color
        fg_color = self.fg_color
        card_bg = self.card_bg  # #252525 (dark) or #FFFFFF (light)
        accent_color = self.accent_color

        # === Scrollable Canvas ===
        canvas = tk.Canvas(review_window, bg=bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(review_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Title
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

            # === Clean Card Container (No Border) ===
            card = tk.Frame(scrollable_frame, bg=card_bg, relief="flat", bd=0)
            card.pack(fill="x", padx=20, pady=8)

            # Week Header
            week_label = tk.Label(
                card,
                text=f"Week {week_num}",
                font=(self.font_family, 12, "bold"),
                bg=card_bg,
                fg=accent_color
            )
            week_label.pack(anchor="w", padx=10, pady=(5, 2))

            # Question
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

            # Score
            score_label = tk.Label(
                card,
                text=f"Score: {score}/10",
                font=(self.font_family, 10, "bold"),
                bg=card_bg,
                fg=fg_color
            )
            score_label.pack(anchor="w", padx=10, pady=(0, 5))

            # Notes
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
                    fg="#AAAAAA"  # Softer grey
                )
                no_notes.pack(anchor="w", padx=15, pady=(0, 5))

        # Pack scrollable UI
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Close button
        ttk.Button(review_window, text="Close", command=review_window.destroy).pack(pady=10)

    def apply_theme(self):
        """Apply Tu Pono brand theme with forced color support"""
        style = ttk.Style()

        # === Force ttk to allow custom colors ===
        # Use 'clam' theme as base (supports color overriding)
        try:
            style.theme_use('clam')
        except:
            pass  # Fallback if theme not available

        # === Define brand colors ===
        bg_color = self.bg_color           # "#1A3A2A"
        fg_color = self.fg_color           # "#FFFFFF"
        primary = self.primary_color       # "#1A3A2A"
        accent = self.accent_color         # "#4CAF50"
        card_bg = self.card_bg             # "#444444"
        border = self.border_color         # "#1A3A2A"
        progress_bg = self.progress_bg     # "#444444"
        font = (self.font_family, 10)

        # === Style ttk widgets ===
        style.configure(
            "TLabel",
            background=bg_color,
            foreground=fg_color,
            font=font
        )
        style.configure(
            "TButton",
            background=primary,
            foreground="white",
            font=(self.font_family, 10, "bold"),
            padding=6
        )
        style.map(
            "TButton",
            background=[('active', '#2E5D3E')],
            relief=[('pressed', 'sunken')]
        )
        style.configure(
            "TLabelframe",
            background="#2E5D3E",           # Light green header
            foreground="white",             # White text
            font=(self.font_family, 12, "bold"),
            borderwidth=2,
            relief="flat"
        )
        style.configure(
            "TLabelframe.Label",
            background="#2E5D3E",
            foreground="white",
            font=(self.font_family, 12, "bold")
        )
        style.configure(
            "TCombobox",
            fieldbackground=card_bg,
            background=card_bg,
            foreground=fg_color
        )
        style.configure(
            "TEntry",
            fieldbackground=card_bg,
            background=card_bg,
            foreground=fg_color,
            insertcolor=fg_color
        )

        # === Apply colors to tk widgets (they support bg/fg) ===
        # First configure the root window
        self.root.configure(bg=bg_color)
        
        # Handle tk widgets that support direct bg/fg configuration
        tk_widgets = [
            self.status_label,      # ttk.Label - styled via ttk.Style
            self.program_label,     # ttk.Label - styled via ttk.Style  
            self.participants_listbox,  # tk.Listbox - can style directly
            self.progress_canvas,   # tk.Canvas - can style directly
            self.program_listbox    # tk.Listbox - can style directly (from create_widgets)
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
                # ttk widgets are already styled above, skip them here
            except Exception as e:
                print(f"Error styling widget {widget}: {e}")
                continue

        # === Update progress bar colors now that theme is applied ===
        self.draw_progress_bar()

        # === Refresh UI ===
        self.root.update_idletasks()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window initially

    # === Create Splash Window ===
    splash = tk.Toplevel()
    splash.overrideredirect(True)  # Remove window borders/title bar
    splash.config(bg='white')
    splash_width, splash_height = 400, 400
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    splash.geometry(f"{splash_width}x{splash_height}+{screen_w//2 - 200}+{screen_h//2 - 200}")
    splash.resizable(False, False)

    try:
        from PIL import Image, ImageTk

        # 🔗 Use raw string for Windows path
        koru_path = r"c:\Day trading indicator bot\koru_outline.png"

        if not os.path.exists(koru_path):
            raise FileNotFoundError(f"Image not found: {koru_path}")

        # Open and resize image
        pil_image = Image.open(koru_path)
        pil_image = pil_image.resize((300, 300), Image.Resampling.LANCZOS)
        photo_image = ImageTk.PhotoImage(pil_image)

        # Create canvas and display image
        canvas = tk.Canvas(splash, width=300, height=300, bg='white', highlightthickness=0)
        canvas.pack(expand=True)
        canvas.create_image(150, 150, image=photo_image)  # Center image

        # Keep reference to prevent garbage collection!
        splash.image = photo_image

        # Add loading text
        ttk.Label(splash, text="Loading Tu Pono Tracker...", font=("Segoe UI", 12)).pack(pady=10)

    except Exception as e:
        print(f"Splash screen error: {e}")
        # Fallback: just show text
        ttk.Label(splash, text="Loading Tu Pono Tracker...", font=("Segoe UI", 16)).pack(expand=True, pady=100)

    # =============================================
    # ✅ CHAINED FLOW: Splash → Password → App or Exit
    # =============================================

    def show_password_prompt():
        # Destroy splash first
        splash.destroy()

        # Show password dialog
        password = simpledialog.askstring(
            "Password Required",
            "Enter password to access the Māori Support Program Tracker:\n"
            "(Case-sensitive)",
            show="*",
            parent=root
        )

        if password == "ElwynPakeha":  # ← Change this!
            root.deiconify()  # Show main window
            try:
                app = ProgramTrackerApp(root)
                root.mainloop()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start app: {str(e)}")
                root.destroy()
        else:
            messagebox.showerror("Access Denied", "Incorrect password. Closing application.")
            root.destroy()  # Ensure app closes completely

    # Start the chain after 2 seconds (or when ready)
    splash.after(2000, show_password_prompt)

    # Start Tkinter mainloop (required for .after() to work)
    root.mainloop()