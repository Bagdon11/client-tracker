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
        self.phase = "red"  # red, orange, green
        self.weeks_completed = 0
        self.programs = []  # Now a list
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
                self.program = "Not selected"
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

        # === Update weekly_progress for full 26-week journey ===
        total_weeks = 26  # 6 red + 8 orange + 12 green
        self.weekly_progress = []
        for week in range(total_weeks):
            if week < weeks_since_signup:
                if week < 6:
                    self.weekly_progress.append("red")
                elif week < 14:  # 6 + 8
                    self.weekly_progress.append("orange")
                else:
                    self.weekly_progress.append("green")
            else:
                self.weekly_progress.append("")  # future week

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
            "program": self.program,
            "weekly_progress": self.weekly_progress,
            "red_phase_assessments": self.red_phase_assessments
        }

    @classmethod
    def from_dict(cls, data):
        try:
            print(f"Attempting to create Participant from: {data}")  # Debug raw input
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
            participant.program = data.get("program", None)
            participant.weekly_progress = data.get("weekly_progress", [])
            participant.red_phase_assessments = data.get("red_phase_assessments", {
                1: {"score": 0, "notes": ""},
                2: {"score": 0, "notes": ""},
                3: {"score": 0, "notes": ""},
                4: {"score": 0, "notes": ""},
                5: {"score": 0, "notes": ""},
                6: {"score": 0, "notes": ""}
            })
            print("Participant created successfully!")  # Debug success
            return participant
        except Exception as e:
            print(f"FAILED to create Participant: {e}")  # Debug failure
            raise  # Re-raise the error to see it in the consoleclass Participant:
   
    def __init__(self, name, age, gender, location, iwi, hapu, signup_date):
        self.name = name
        self.age = age
        self.gender = gender
        self.location = location
        self.iwi = iwi
        self.hapu = hapu
        self.signup_date = datetime.strptime(signup_date, "%Y-%m-%d").date()
        self.phase = "red"  # red, orange, green
        self.weeks_completed = 0
        self.program = None
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
                    self.program = "Not selected"
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
    
            # === Update weekly_progress for full 26-week journey ===
            total_weeks = 26  # 6 red + 8 orange + 12 green
            self.weekly_progress = []
            for week in range(total_weeks):
                if week < weeks_since_signup:
                    if week < 6:
                        self.weekly_progress.append("red")
                    elif week < 14:  # 6 + 8
                        self.weekly_progress.append("orange")
                    else:
                        self.weekly_progress.append("green")
                else:
                    self.weekly_progress.append("")  # future week
                
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
            print(f"Attempting to create Participant from: {data}")  # Debug raw input
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
            print("Participant created successfully!")  # Debug success
            return participant
        except Exception as e:
            print(f"FAILED to create Participant: {e}")  # Debug failure
            raise  # Re-raise the error to see it in the console
class ProgramTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Māori Support Program Tracker")
        self.participants = []
        self.current_participant = None
        self.statistics_window = None
        print(f"Participants in memory: {len(self.participants)}")  # Check count
        if self.participants:
            print(f"First participant: {self.participants[0].name}")  # Verify data
        else:
            print("No participants loaded!")

        # Create UI
        self.create_widgets()

    def new_file(self):
        """Create a new empty participant list"""
        if self.participants:
            if not messagebox.askyesno("Confirm", "This will clear all current data. Continue?"):
                return
        self.participants = []
        self.update_participants_list()
        self.clear_inputs()
        messagebox.showinfo("New File", "Created new empty participant list")

    def load_json_dialog(self):
        """Open file dialog to load JSON data"""
        filepath = filedialog.askopenfilename(
            title="Open Participant Data",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            self.load_json(filepath)

    def load_json(self, filepath):
        """Load participant data from specified JSON file"""
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            self.participants = [Participant.from_dict(item) for item in data]
            self.update_participants_list()
            messagebox.showinfo("Success", f"Loaded {len(self.participants)} participants")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")

    def save_json_dialog(self):
        """Open file dialog to save JSON data"""
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
        """Save participant data to specified JSON file"""
        try:
            data = [p.to_dict() for p in self.participants]
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Success", f"Saved {len(self.participants)} participants to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
    
    def export_to_pdf(self, filename=None):
        """Export participant data AND statistics to PDF"""
        if not self.participants:
            messagebox.showwarning("No Data", "No participants to export")
            return

        # Ask for save location
        if not filename:
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                title="Save Full Report"
            )
            if not filename:
                return

        try:
            # Create PDF with larger page size for charts
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
            
            # Table Header
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(40, 8, "Name", 1)
            pdf.cell(25, 8, "Phase", 1)
            pdf.cell(40, 8, "Program", 1)
            pdf.cell(20, 8, "Weeks", 1)
            pdf.cell(30, 8, "Iwi", 1)
            pdf.cell(30, 8, "Location", 1)
            pdf.ln()
            
            # Table Rows
            pdf.set_font("Helvetica", "", 9)
            for p in self.participants:
                pdf.cell(40, 8, p.name[:30], 1)
                pdf.cell(25, 8, p.phase.capitalize(), 1)
                pdf.cell(40, 8, (p.program or "N/A")[:25], 1)
                pdf.cell(20, 8, str(p.weeks_completed), 1)
                pdf.cell(30, 8, p.iwi[:20] if p.iwi else "N/A", 1)
                pdf.cell(30, 8, p.location[:20], 1)
                pdf.ln()
            
            # ===== 3. Statistical Charts =====
            # Generate all charts first
            charts = self._generate_all_charts()
            
            # Add each chart to PDF
            for chart_name, fig in charts.items():
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(0, 10, chart_name, 0, 1)
                
                # Save chart to temp file
                temp_img = os.path.join(tempfile.gettempdir(), f"{chart_name}.png")
                fig.savefig(temp_img, dpi=300, bbox_inches='tight')
                plt.close(fig)
                
                # Add to PDF (centered, 160mm width)
                pdf.image(temp_img, x=pdf.w / 2 - 80, w=160)
                os.remove(temp_img)  # Clean up
            
            pdf.output(filename)
            messagebox.showinfo("Success", f"Full report saved to:\n{filename}")
            self._open_file(filename)
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to create PDF:\n{str(e)}")

    def _generate_all_charts(self):
        """Generate all statistical charts as matplotlib figures"""
        charts = {}
        
        # 1. Program Distribution
        programs = ["Ko wai au", "Mental Health and Well-being", "Anger Management", "Domestic Violence"]
        program_counts = {p: sum(1 for part in self.participants if part.program == p) for p in programs}
        fig1, ax1 = plt.subplots(figsize=(8, 6))
        ax1.pie(program_counts.values(), labels=program_counts.keys(), autopct='%1.1f%%')
        ax1.set_title("Program Distribution")
        charts["Program Distribution"] = fig1
        
        # 2. Gender Distribution
        genders = ["Male", "Female", "Non-binary", "Other", "Prefer not to say"]
        gender_counts = {g: sum(1 for part in self.participants if part.gender == g) for g in genders}
        fig2, ax2 = plt.subplots(figsize=(8, 6))
        ax2.pie(gender_counts.values(), labels=gender_counts.keys(), autopct='%1.1f%%')
        ax2.set_title("Gender Distribution")
        charts["Gender Distribution"] = fig2
        
        # 3. Iwi Distribution (with grouping)
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
        
        fig3, ax3 = plt.subplots(figsize=(8, 6))
        ax3.pie(iwi_counts.values(), labels=iwi_counts.keys(), autopct='%1.1f%%')
        ax3.set_title("Iwi Affiliation")
        charts["Iwi Affiliation"] = fig3
        
        # 4. Program by Gender
        gender_program_data = pd.crosstab(
            [p.gender for p in self.participants],
            [p.program for p in self.participants]
        ).reindex(index=genders, columns=programs, fill_value=0)
        
        fig4, ax4 = plt.subplots(figsize=(10, 6))
        gender_program_data.plot(kind='bar', stacked=True, ax=ax4)
        ax4.set_title("Program Participation by Gender")
        ax4.set_ylabel("Count")
        ax4.legend(title="Program")
        charts["Program by Gender"] = fig4
        
        return charts

    def _open_file(self, path):
        """Open file with default application"""
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])       
        
    def create_widgets(self):
        # Main frames
        self.input_frame = ttk.LabelFrame(self.root, text="Participant Information", padding=10)
        self.input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.progress_frame = ttk.LabelFrame(self.root, text="Progress Tracking", padding=10)
        self.progress_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        self.list_frame = ttk.LabelFrame(self.root, text="Participants List", padding=10)
        self.list_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        # Input fields
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
        
        
        
        # Buttons
        self.add_button = ttk.Button(self.input_frame, text="Add Participant", command=self.add_participant)
        self.add_button.grid(row=7, column=0, columnspan=2, pady=10, sticky="ew")
        
        self.update_button = ttk.Button(self.input_frame, text="Update Participant", command=self.update_participant, state="disabled")
        self.update_button.grid(row=8, column=0, columnspan=2, pady=5, sticky="ew")
        
        # Progress display
        self.status_label = ttk.Label(self.progress_frame, text="Status: Not selected", font=('Helvetica', 12))
        self.status_label.grid(row=0, column=0, columnspan=2, pady=5, sticky="w")
        
        self.program_label = ttk.Label(self.progress_frame, text="Program: Not selected", font=('Helvetica', 12))
        self.program_label.grid(row=1, column=0, columnspan=2, pady=5, sticky="w")
        
        ttk.Label(self.progress_frame, text="Weekly Progress:").grid(row=2, column=0, columnspan=2, pady=5, sticky="w")
        
        # Progress bar (calendar-like)
        self.progress_canvas = tk.Canvas(self.progress_frame, width=400, height=50, bg="white")
        self.progress_canvas.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        
        # Program selection (for orange phase)
        ttk.Label(self.progress_frame, text="Select Programs:").grid(row=4, column=0, pady=5, sticky="w")
        self.program_listbox = tk.Listbox(self.progress_frame, height=4, selectmode="multiple")
        programs = ["Ko wai au", "Mental Health and Well-being", "Anger Management", "Domestic Violence"]
        for p in programs:
            self.program_listbox.insert(tk.END, p)
        self.program_listbox.grid(row=4, column=1, pady=5, sticky="ew")

        # Change set_programs to set_program here:
        self.select_program_button = ttk.Button(self.progress_frame, text="Set Programs", 
                                      command=self.set_program, state="disabled")
        self.select_program_button.grid(row=5, column=0, columnspan=2, pady=5, sticky="ew")
        
        # Red phase assessment button
        self.assessment_button = ttk.Button(self.progress_frame, text="Weekly Assessment", 
                                          command=self.show_assessment, state="disabled")
        self.assessment_button.grid(row=6, column=0, columnspan=2, pady=5, sticky="ew")
        
        # Statistics button
        self.stats_button = ttk.Button(self.progress_frame, text="View Statistics", 
                                     command=self.show_statistics)
        self.stats_button.grid(row=7, column=0, columnspan=2, pady=5, sticky="ew")
        
        # Participants list
        self.participants_listbox = tk.Listbox(self.list_frame, height=10)
        self.participants_listbox.grid(row=0, column=0, sticky="nsew")
        self.participants_listbox.bind("<<ListboxSelect>>", self.select_participant)
        
        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.participants_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.participants_listbox.config(yscrollcommand=scrollbar.set)
        
        self.delete_button = ttk.Button(self.list_frame, text="Delete Participant", command=self.delete_participant)
        self.delete_button.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")
        
        self.file_frame = ttk.Frame(self.root)
        self.file_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
    
        ttk.Button(self.file_frame, text="New", command=self.new_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.file_frame, text="Load JSON", command=self.load_json_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.file_frame, text="Save As...", command=self.save_json_dialog).pack(side=tk.LEFT, padx=5)
        
        # Add to your file controls frame (where Load/Save buttons are)
        ttk.Button(self.file_frame, text="Export PDF", 
          command=self.export_to_pdf).pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)
        
        self.input_frame.columnconfigure(1, weight=1)
        self.progress_frame.columnconfigure(1, weight=1)
        self.list_frame.columnconfigure(0, weight=1)
        self.list_frame.rowconfigure(0, weight=1)
        
        # Update list
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
            
        # Find and update the participant
        for i, p in enumerate(self.participants):
            if p.name == self.current_participant.name and p.signup_date == self.current_participant.signup_date:
                self.participants[i] = Participant(name, age, gender, location, iwi, hapu, signup_date)
                self.participants[i].phase = self.current_participant.phase
                self.participants[i].weeks_completed = self.current_participant.weeks_completed
                self.participants[i].program = self.current_participant.program
                self.participants[i].weekly_progress = self.current_participant.weekly_progress
                self.participants[i].red_phase_assessments = self.current_participant.red_phase_assessments
                self.participants[i].update_progress()
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
        
        # Update input fields
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
        
        # Update progress display
        self.update_progress_display()
        
        # Enable buttons
        self.update_button.config(state="normal")
        self.select_program_button.config(state="normal")
        self.assessment_button.config(state="normal")
        
    def set_program(self):
        if not self.current_participant:
            return
        if self.current_participant.phase != "orange":
            messagebox.showinfo("Info", "Programs can only be selected in the Orange phase")
            return

        selected_indices = self.program_listbox.curselection()
        selected_programs = [self.program_listbox.get(i) for i in selected_indices]

        if not selected_programs:
            messagebox.showerror("Error", "Please select at least one program")
            return

        # Update in memory
        self.current_participant.programs = selected_programs

        # Update main list
        for p in self.participants:
            if p.name == self.current_participant.name and p.signup_date == self.current_participant.signup_date:
                p.programs = selected_programs
                break

        self.save_data()
        self.update_progress_display()
        
    def show_assessment(self):
        if not self.current_participant or self.current_participant.phase != "red":
            return
            
        week = self.current_participant.weeks_completed + 1
        if week > 6:  # Only 6 weeks in red phase
            return
            
        assessment_window = tk.Toplevel(self.root)
        assessment_window.title(f"Week {week} Assessment")
        
        questions = {
            1: "How well did you do to create a safe space for your whaiora?",
            2: "How did you do to allow your whaiora to express their māmae?",
            3: "How well did you prepare a pathway of purpose for your whaiora?",
            4: "How well have you identified what barriers your whaiora is facing?",
            5: "How confident are you in assuring you whaiora is ready to proceed with their pathway forward?"
        }
        
        # Get the assessment for this week
        assessment = self.current_participant.red_phase_assessments.get(week, {"score": 0, "notes": ""})
        
        # Question label
        ttk.Label(assessment_window, text=questions[week], wraplength=400).pack(pady=10)
        
        # Score
        ttk.Label(assessment_window, text="Score (0-10):").pack()
        score_var = tk.IntVar(value=assessment["score"])
        score_slider = ttk.Scale(assessment_window, from_=0, to=10, variable=score_var, orient="horizontal")
        score_slider.pack(fill="x", padx=20, pady=5)
        
        # Notes
        ttk.Label(assessment_window, text="Notes:").pack()
        notes_text = tk.Text(assessment_window, height=5, width=50)
        notes_text.pack(padx=10, pady=5)
        notes_text.insert("1.0", assessment["notes"])
        
        def save_assessment():
            self.current_participant.red_phase_assessments[week] = {
                "score": score_var.get(),
                "notes": notes_text.get("1.0", "end-1c")
            }
            assessment_window.destroy()
            
        ttk.Button(assessment_window, text="Save", command=save_assessment).pack(pady=10)
        
    def update_progress_display(self):
        if not self.current_participant:
            return
            
        # Update status label
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
        
        # Update program label
        if self.current_participant.programs:
            program_names = ", ".join(self.current_participant.programs)
            program_text = f"Program(s): {program_names}"
        else:
            program_text = "Program(s): Not selected"
        self.program_label.config(text=program_text)
        
        # Update program dropdown
        if self.current_participant.program:
            self.program_dropdown.set(self.current_participant.program)
        else:
            self.program_dropdown.set("Not selected")
            
        # Draw progress bar
        self.draw_progress_bar()
        
    def draw_progress_bar(self):
        self.progress_canvas.delete("all")
        if not self.current_participant:
            return

        total_weeks = 26  # Updated from 14 to 26
        cell_width = 400 / total_weeks  # Adjust width dynamically
        cell_height = 40

        for week in range(total_weeks):
            x1 = week * cell_width
            x2 = x1 + cell_width
            y1 = 5
            y2 = y1 + cell_height

            color = ""
            if week < len(self.current_participant.weekly_progress):
                color = self.current_participant.weekly_progress[week]

            if color == "red":
                fill = "#ff6b6b"
            elif color == "orange":
                fill = "#ffb347"
            elif color == "green":
                fill = "#4CAF50"
            else:
                fill = "white"

            # Draw cell
            self.progress_canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="black")
            # Add week number
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

        # Create notebook first
        notebook = ttk.Notebook(self.statistics_window)
        notebook.pack(fill="both", expand=True)

        # Create all frames
        program_frame = ttk.Frame(notebook)
        gender_frame = ttk.Frame(notebook)
        gender_program_frame = ttk.Frame(notebook)
        iwi_frame = ttk.Frame(notebook)

        # Add tabs to notebook
        notebook.add(program_frame, text="Program Distribution")
        notebook.add(gender_frame, text="Gender Distribution")
        notebook.add(gender_program_frame, text="Program by Gender")
        notebook.add(iwi_frame, text="Iwi Distribution")

        # Common data
        programs = ["Ko wai au", "Mental Health and Well-being",
                   "Anger Management", "Domestic Violence"]
        genders = ["Male", "Female", "Non-binary", "Other", "Prefer not to say"]

        # ===== 1. Program Distribution Pie Chart =====
        program_counts = {p: 0 for p in programs}
        for p in self.participants:
            if p.program and p.program in programs:
                program_counts[p.program] += 1

        fig1, ax1 = plt.subplots(figsize=(5, 4))
        ax1.pie(program_counts.values(), labels=program_counts.keys(),
               autopct='%1.1f%%', startangle=90)
        ax1.axis('equal')
        canvas1 = FigureCanvasTkAgg(fig1, master=program_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True)

        # ===== 2. Gender Distribution Pie Chart =====
        gender_counts = {g: 0 for g in genders}
        for p in self.participants:
            if p.gender in gender_counts:
                gender_counts[p.gender] += 1

        fig2, ax2 = plt.subplots(figsize=(5, 4))
        ax2.pie(gender_counts.values(), labels=gender_counts.keys(),
               autopct='%1.1f%%', startangle=90)
        ax2.axis('equal')
        canvas2 = FigureCanvasTkAgg(fig2, master=gender_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True)

        # ===== 3. Program by Gender Bar Chart =====
        gender_program_data = {}
        for gender in genders:
            gender_program_data[gender] = {p: 0 for p in programs}

        for p in self.participants:
            if p.gender in genders and p.program in programs:
                gender_program_data[p.gender][p.program] += 1

        fig3, ax3 = plt.subplots(figsize=(8, 6))
        bottom = None
        for program in programs:
            counts = [gender_program_data[gender][program] for gender in genders]
            ax3.bar(genders, counts, label=program, bottom=bottom)
            bottom = counts if bottom is None else [bottom[i] + counts[i] for i in range(len(counts))]

        ax3.set_ylabel("Number of Participants")
        ax3.set_title("Program Participation by Gender")
        ax3.legend()
        canvas3 = FigureCanvasTkAgg(fig3, master=gender_program_frame)
        canvas3.draw()
        canvas3.get_tk_widget().pack(fill="both", expand=True)

        # ===== 4. Iwi Distribution Pie Chart =====
        iwi_counts = {}
        for p in self.participants:
            iwi = p.iwi if p.iwi else "Not specified"
            iwi_counts[iwi] = iwi_counts.get(iwi, 0) + 1

        # Group small iwi into "Other" if needed
        if len(iwi_counts) > 8:
            total = sum(iwi_counts.values())
            threshold = total * 0.05
            grouped_iwi = {}
            other_count = 0

            for iwi, count in iwi_counts.items():
                if count >= threshold:
                    grouped_iwi[iwi] = count
                else:
                    other_count += count

            if other_count > 0:
                grouped_iwi["Other"] = other_count
            iwi_counts = grouped_iwi

        # Sort and create chart
        sorted_iwi = sorted(iwi_counts.items(), key=lambda x: x[1], reverse=True)
        labels = [iwi[0] for iwi in sorted_iwi]
        sizes = [iwi[1] for iwi in sorted_iwi]

        fig4, ax4 = plt.subplots(figsize=(8, 6))
        ax4.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax4.axis('equal')
        ax4.set_title("Participants by Iwi Affiliation")

        canvas4 = FigureCanvasTkAgg(fig4, master=iwi_frame)
        canvas4.draw()
        canvas4.get_tk_widget().pack(fill="both", expand=True)

        # Window close handler
        self.statistics_window.protocol("WM_DELETE_WINDOW",
                                     lambda: self.on_stats_window_close())
        
    def update_participants_list(self):
        self.participants_listbox.delete(0, tk.END)
        for p in sorted(self.participants, key=lambda x: x.signup_date):
            status = f"{p.name} ({p.age}, {p.gender}) - {p.phase.upper()}"
            if p.phase == "orange" and p.program:
                status += f" - {p.program}"
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
                    # THIS IS THE CRITICAL LINE - YOU NEED TO ASSIGN TO self.participants
                    self.participants = [Participant.from_dict(item) for item in data]
                    print(f"Successfully loaded {len(self.participants)} participants")  # Debug
            else:
                self.participants = []  # Initialize if file doesn't exist
        except Exception as e:
            print(f"Error loading data: {e}")
            self.participants = []  # Fallback to empty list


    def save_data(self):
        data = [p.to_dict() for p in self.participants]
        with open("participants.json", "w") as f:
            json.dump(data, f, indent=2)

if __name__ == "__main__":
    root = tk.Tk()
    app = ProgramTrackerApp(root)
    root.mainloop()