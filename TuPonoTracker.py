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

JSON_PATH = os.path.join(os.path.dirname(__file__), "participants.json")
print(f"JSON_PATH resolved to: {JSON_PATH}")
print(f"File exists: {os.path.exists(JSON_PATH)}")


class Participant:
    def __init__(self, name, age, gender, location, iwi, hapu, signup_date):
        self.name = name
        self.age = age
        self.gender = gender
        self.location = location
        self.iwi = iwi
        self.hapu = hapu
        self.signup_date = datetime.strptime(signup_date, "%Y-%m-%d").date()
        self.phase = "red"  # red, orange, green, completed
        self.weeks_completed = 0
        self.programs = []  # Now supports multiple programs
        self.weekly_progress = []
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
            "red_phase_assessments": self.red_phase_assessments
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
                data["signup_date"]
            )
            participant.phase = data.get("phase", "red")
            participant.weeks_completed = data.get("weeks_completed", 0)
            participant.programs = data.get("programs", [])
            participant.weekly_progress = data.get("weekly_progress", [])
            participant.red_phase_assessments = data.get("red_phase_assessments", {
                1: {"score": 0, "notes": ""},
                2: {"score": 0, "notes": ""},
                3: {"score": 0, "notes": ""},
                4: {"score": 0, "notes": ""},
                5: {"score": 0, "notes": ""},
                6: {"score": 0, "notes": ""}
            })
            return participant
        except Exception as e:
            print(f"FAILED to create Participant: {e}")
            raise


class ProgramTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Māori Support Program Tracker")
        self.participants = []
        self.current_participant = None
        self.statistics_window = None
        self.load_data()
        self.create_widgets()

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

        try:
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.set_auto_page_break(auto=True, margin=15)

            # ===== 1. Cover Page =====
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 24)
            pdf.cell(0, 20, "Tu Pono IP - Full Report", 0, 1, "C")
            pdf.ln(10)
            pdf.set_font("Helvetica", "", 14)
            pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")
            pdf.ln(20)

            # ===== 2. Participant Table =====
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "Participant Overview", 0, 1)
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(40, 8, "Name", 1)
            pdf.cell(25, 8, "Phase", 1)
            pdf.cell(40, 8, "Program(s)", 1)
            pdf.cell(20, 8, "Weeks", 1)
            pdf.cell(30, 8, "Iwi", 1)
            pdf.cell(30, 8, "Location", 1)
            pdf.ln()
            pdf.set_font("Helvetica", "", 9)
            for p in self.participants:
                pdf.cell(40, 8, p.name[:30], 1)
                pdf.cell(25, 8, p.phase.capitalize(), 1)
                prog = ", ".join(p.programs) if p.programs else "N/A"
                pdf.cell(40, 8, prog[:25], 1)
                pdf.cell(20, 8, str(p.weeks_completed), 1)
                pdf.cell(30, 8, p.iwi[:20] if p.iwi else "N/A", 1)
                pdf.cell(30, 8, p.location[:20], 1)
                pdf.ln()

            # ===== 3. Progress Timeline =====
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "Progress Timeline", 0, 1)
            pdf.ln(5)

            fig, ax = plt.subplots(figsize=(10, len(self.participants) * 0.8 + 1))
            for i, p in enumerate(self.participants):
                ax.text(-1, i, p.name, ha='right', va='center', fontsize=10)
                for week in range(26):
                    color = 'white'
                    if week < len(p.weekly_progress):
                        c = p.weekly_progress[week]
                        if c == "red": color = "#ff6b6b"
                        elif c == "orange": color = "#ffb347"
                        elif c == "green": color = "#4CAF50"
                    rect = plt.Rectangle((week, i - 0.4), 1, 0.8, facecolor=color, edgecolor='black', linewidth=0.5)
                    ax.add_patch(rect)
                    # Highlight current week
                    current_week = (datetime.now().date() - p.signup_date).days // 7
                    if week == current_week and color != 'white':
                        rect.set_edgecolor('darkblue')
                        rect.set_linewidth(2)
                # Add programs
                if p.programs:
                    ax.text(27, i, ", ".join(p.programs), ha='left', va='center', fontsize=9, color='gray')

            ax.set_xlim(-2, 30)
            ax.set_ylim(-0.5, len(self.participants) + 0.5)
            ax.set_yticks([])
            ax.set_xticks(range(0, 27, 2))
            ax.set_xlabel("Week")
            ax.grid(False)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)

            temp_img = os.path.join(tempfile.gettempdir(), "timeline.png")
            fig.savefig(temp_img, dpi=150, bbox_inches='tight')
            plt.close(fig)
            pdf.image(temp_img, x=10, w=180)
            os.remove(temp_img)

            # ===== 4. Charts =====
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

    def _generate_all_charts(self):
        """Generate all statistical charts as matplotlib figures (safe for PDF/UI)"""
        charts = {}
        programs = ["Ko wai au", "Mental Health and Well-being", "Anger Management", "Domestic Violence"]
        genders = ["Male", "Female", "Non-binary", "Other", "Prefer not to say"]

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
        gender_counts = {g: sum(1 for part in self.participants if part.gender == g) for g in genders}
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
            except:
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

        ttk.Label(self.input_frame, text="Gender:").grid(row=2, column=0, sticky="w")
        self.gender_var = tk.StringVar()
        self.gender_dropdown = ttk.Combobox(self.input_frame, textvariable=self.gender_var,
                                          values=["Male", "Female", "Non-binary", "Other", "Prefer not to say"])
        self.gender_dropdown.grid(row=2, column=1, pady=5, sticky="ew")

        ttk.Label(self.input_frame, text="Location:").grid(row=3, column=0, sticky="w")
        self.location_entry = ttk.Entry(self.input_frame)
        self.location_entry.grid(row=3, column=1, pady=5, sticky="ew")

        ttk.Label(self.input_frame, text="Iwi:").grid(row=4, column=0, sticky="w")
        self.iwi_entry = ttk.Entry(self.input_frame)
        self.iwi_entry.grid(row=4, column=1, pady=5, sticky="ew")

        ttk.Label(self.input_frame, text="Hapū:").grid(row=5, column=0, sticky="w")
        self.hapu_entry = ttk.Entry(self.input_frame)
        self.hapu_entry.grid(row=5, column=1, pady=5, sticky="ew")

        ttk.Label(self.input_frame, text="Signup Date (YYYY-MM-DD):").grid(row=6, column=0, sticky="w")
        self.date_entry = ttk.Entry(self.input_frame)
        self.date_entry.grid(row=6, column=1, pady=5, sticky="ew")

        self.add_button = ttk.Button(self.input_frame, text="Add Participant", command=self.add_participant)
        self.add_button.grid(row=7, column=0, columnspan=2, pady=10, sticky="ew")

        self.update_button = ttk.Button(self.input_frame, text="Update Participant", command=self.update_participant, state="disabled")
        self.update_button.grid(row=8, column=0, columnspan=2, pady=5, sticky="ew")

        self.status_label = ttk.Label(self.progress_frame, text="Status: Not selected", font=('Helvetica', 12))
        self.status_label.grid(row=0, column=0, columnspan=2, pady=5, sticky="w")

        self.program_label = ttk.Label(self.progress_frame, text="Program(s): Not selected", font=('Helvetica', 12))
        self.program_label.grid(row=1, column=0, columnspan=2, pady=5, sticky="w")

        ttk.Label(self.progress_frame, text="Weekly Progress:").grid(row=2, column=0, columnspan=2, pady=5, sticky="w")

        self.progress_canvas = tk.Canvas(self.progress_frame, width=520, height=50, bg="white")
        self.progress_canvas.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")

        ttk.Label(self.progress_frame, text="Select Programs:").grid(row=4, column=0, pady=5, sticky="w")
        self.program_listbox = tk.Listbox(self.progress_frame, height=4, selectmode="multiple")
        for p in ["Ko wai au", "Mental Health and Well-being", "Anger Management", "Domestic Violence"]:
            self.program_listbox.insert(tk.END, p)
        self.program_listbox.grid(row=4, column=1, pady=5, sticky="ew")

        self.select_program_button = ttk.Button(self.progress_frame, text="Set Programs", command=self.set_programs, state="disabled")
        self.select_program_button.grid(row=5, column=0, columnspan=2, pady=5, sticky="ew")

        self.assessment_button = ttk.Button(self.progress_frame, text="Weekly Assessment", command=self.show_assessment, state="disabled")
        self.assessment_button.grid(row=6, column=0, columnspan=2, pady=5, sticky="ew")

        self.stats_button = ttk.Button(self.progress_frame, text="View Statistics", command=self.show_statistics)
        self.stats_button.grid(row=7, column=0, columnspan=2, pady=5, sticky="ew")

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
        ttk.Button(self.file_frame, text="Toggle Dark Mode", command=self.toggle_dark_mode).pack(side=tk.LEFT, padx=5)
        
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
        location = self.location_entry.get()
        iwi = self.iwi_entry.get()
        hapu = self.hapu_entry.get()
        signup_date = self.date_entry.get()
        if not all([name, age, gender, location, iwi, hapu, signup_date]):
            messagebox.showerror("Error", "All fields are required")
            return
        try:
            datetime.strptime(signup_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
            return
        participant = Participant(name, age, gender, location, iwi, hapu, signup_date)
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
        location = self.location_entry.get()
        iwi = self.iwi_entry.get()
        hapu = self.hapu_entry.get()
        signup_date = self.date_entry.get()
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
                new_p = Participant(name, age, gender, location, iwi, hapu, signup_date)
                new_p.phase = self.current_participant.phase
                new_p.weeks_completed = self.current_participant.weeks_completed
                new_p.programs = self.current_participant.programs
                new_p.weekly_progress = self.current_participant.weekly_progress
                new_p.red_phase_assessments = self.current_participant.red_phase_assessments
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
        self.current_participant.update_progress()
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.current_participant.name)
        self.age_entry.delete(0, tk.END)
        self.age_entry.insert(0, self.current_participant.age)
        self.gender_var.set(self.current_participant.gender)
        self.location_entry.delete(0, tk.END)
        self.location_entry.insert(0, self.current_participant.location)
        self.iwi_entry.delete(0, tk.END)
        self.iwi_entry.insert(0, self.current_participant.iwi)
        self.hapu_entry.delete(0, tk.END)
        self.hapu_entry.insert(0, self.current_participant.hapu)
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, self.current_participant.signup_date.strftime("%Y-%m-%d"))
        self.update_progress_display()
        self.update_button.config(state="normal")
        self.select_program_button.config(state="normal")
        self.assessment_button.config(state="normal")

    def set_programs(self):
        if not self.current_participant or self.current_participant.phase != "orange":
            messagebox.showinfo("Info", "Programs can only be selected in the Orange phase")
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
        questions = {
            1: "How well did you do to create a safe space for your whaiora?",
            2: "How did you do to allow your whaiora to express their māmae?",
            3: "How well did you prepare a pathway of purpose for your whaiora?",
            4: "How well have you identified what barriers your whaiora is facing?",
            5: "How confident are you in assuring you whaiora is ready to proceed with their pathway forward?"
        }
        assessment = self.current_participant.red_phase_assessments.get(week, {"score": 0, "notes": ""})
        ttk.Label(assessment_window, text=questions[week], wraplength=400).pack(pady=10)
        ttk.Label(assessment_window, text="Score (0-10):").pack()
        score_var = tk.IntVar(value=assessment["score"])
        score_slider = ttk.Scale(assessment_window, from_=0, to=10, variable=score_var, orient="horizontal")
        score_slider.pack(fill="x", padx=20, pady=5)
        ttk.Label(assessment_window, text="Notes:").pack()
        notes_text = tk.Text(assessment_window, height=5, width=50)
        notes_text.pack(padx=10, pady=5)
        notes_text.insert("1.0", assessment["notes"])
        def save_assessment():
            self.current_participant.red_phase_assessments[week] = {
                "score": score_var.get(),
                "notes": notes_text.get("1.0", "end-1c")
            }
            for i, p in enumerate(self.participants):
                if p.name == self.current_participant.name and p.signup_date == self.current_participant.signup_date:
                    self.participants[i].red_phase_assessments[week] = self.current_participant.red_phase_assessments[week]
                    break
            self.save_data()
            assessment_window.destroy()
        ttk.Button(assessment_window, text="Save", command=save_assessment).pack(pady=10)

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
        cell_height = 40
        today = datetime.now().date()
        current_week = (today - self.current_participant.signup_date).days // 7
        for week in range(total_weeks):
            x1 = week * cell_width
            x2 = x1 + cell_width
            y1 = 5
            y2 = y1 + cell_height
            color = self.current_participant.weekly_progress[week] if week < len(self.current_participant.weekly_progress) else ""
            if color == "red":
                fill = "#ff6b6b"
            elif color == "orange":
                fill = "#ffb347"
            elif color == "green":
                fill = "#4CAF50"
            else:
                fill = "white"
            outline = "darkblue" if week == current_week and color else "black"
            width = 3 if week == current_week and color else 1
            self.progress_canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)
            self.progress_canvas.create_text(x1 + cell_width/2, y1 + cell_height/2, text=str(week+1), font=("Helvetica", 8))

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
        genders = ["Male", "Female", "Non-binary", "Other", "Prefer not to say"]

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
        data_rows = []
        for p in self.participants:
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
            except:
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
            
    def toggle_dark_mode(self):
        """Toggle between dark and light mode"""
        if hasattr(self, 'dark_mode') and self.dark_mode:
            # Switch to Light Mode
            self.dark_mode = False
            self.bg_color = "#f8f9fa"
            self.fg_color = "#333333"
            self.primary_color = "#3498db"
            self.card_bg = "white"
            self.border_color = "#ddd"
            self.progress_bg = "white"
        else:
            # Switch to Dark Mode
            self.dark_mode = True
            self.bg_color = "#1a1a1a"
            self.fg_color = "#e0e0e0"
            self.primary_color = "#00a8ff"
            self.card_bg = "#2d2d2d"
            self.border_color = "#555"
            self.progress_bg = "#252525"

        # Apply the theme
        self.apply_theme()
        # Save preference
        self.save_mode_preference() 
    def apply_theme(self):
        """Apply current theme to all widgets"""
        style = ttk.Style()

        # Configure root and frames
        self.root.configure(bg=self.bg_color)
        for frame in [self.input_frame, self.progress_frame, self.list_frame]:
            frame.configure(borderwidth=1, relief="solid")
            for child in frame.winfo_children():
                child.configure(bg=self.bg_color, fg=self.fg_color)

        # Update canvas background
        self.progress_canvas.config(bg=self.progress_bg)

        # Update listbox
        self.participants_listbox.config(
            bg=self.card_bg,
            fg=self.fg_color,
            highlightbackground=self.border_color,
            bd=0
        )

        # Update text widgets (if any)
        for widget in [self.name_entry, self.age_entry, self.location_entry,
                       self.iwi_entry, self.hapu_entry, self.date_entry]:
            widget.config(
                bg=self.card_bg,
                fg=self.fg_color,
                insertbackground=self.fg_color,
                highlightbackground=self.border_color
            )

        # Update labels
        self.status_label.config(bg=self.bg_color, fg=self.fg_color)
        self.program_label.config(bg=self.bg_color, fg=self.fg_color)

        # Reconfigure style
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        style.configure("TLabelframe", background=self.bg_color, foreground=self.fg_color)
        style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.primary_color, font=(self.font_family, 12, "bold"))
        style.configure("TButton", background=self.primary_color, foreground="white", font=(self.font_family, 10))
        style.map("TButton", background=[('active', '#008fd5')])

        # Refresh UI
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    child.update()


if __name__ == "__main__":
    root = tk.Tk()
    app = ProgramTrackerApp(root)
    root.mainloop()