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
        self.root.title("TuPono IP - Māori Support Program Tracker")
        
        # Configure window
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        self.root.state('zoomed')  # Maximize on Windows
        
        # Center window if not maximized
        self.center_window()
        
        self.participants = []
        self.current_participant = None
        self.statistics_window = None
        print("Basic attributes set...")

        # === Modern Tu Pono Brand Colours ===
        self.bg_color = "#F0F8FF"           # Alice Blue - Vibrant Light Background
        self.sidebar_bg = "#2E8B57"         # Sea Green - Brighter Tu Pono Green
        self.fg_color = "#000000"           # Pure black for maximum contrast
        self.primary_color = "#2E8B57"      # Sea Green - Vibrant Tu Pono Green
        self.accent_color = "#32CD32"       # Lime Green - Bright Success
        self.card_bg = "#FAFFFE"            # Off-White with hint of blue
        self.border_color = "#87CEEB"       # Sky Blue Borders
        self.progress_bg = "#E6F3FF"        # Light Blue Progress Background  
        self.secondary_bg = "#D6EAF8"       # Light Blue Secondary
        self.danger_color = "#FF4757"       # Bright Red for warnings
        self.warning_color = "#FFA502"      # Bright Orange for warnings
        self.info_color = "#3742FA"         # Electric Blue for info
        self.font_family = "Segoe UI"
        self.header_font = ("Segoe UI", 14, "bold")
        self.body_font = ("Segoe UI", 10)
        self.small_font = ("Segoe UI", 9)
        print("Colors initialized...")

        print("Loading data...")
        self.load_data()
        print("Creating widgets...")
        self.create_widgets()
        print("Updating participants list...")
        self.update_participants_list()  # Ensure list is populated after widget creation
        print("Applying theme...")
        self.apply_theme()
        
        # Setup window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Handle application closing with confirmation"""
        if messagebox.askyesno("Exit TuPono Tracker", "Are you sure you want to exit?"):
            # Save any pending changes
            try:
                self.save_data()
            except:
                pass  # Don't block closing if save fails
            
            # Close any open windows
            if hasattr(self, 'statistics_window') and self.statistics_window:
                try:
                    self.statistics_window.destroy()
                except:
                    pass
            
            self.root.destroy()
        # Add keyboard shortcuts and accessibility
        self.setup_keyboard_shortcuts()
        print("App initialization complete!")

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for better accessibility"""
        # Global shortcuts
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.load_json_dialog())
        self.root.bind("<Control-s>", lambda e: self.save_json_dialog())
        self.root.bind("<Control-e>", lambda e: self.export_to_pdf())
        self.root.bind("<F1>", lambda e: self.show_help())
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        
        # Add participant shortcut
        self.root.bind("<Control-Return>", lambda e: self.add_participant())
        
        # Statistics shortcut
        self.root.bind("<F5>", lambda e: self.show_statistics())

    def show_help(self):
        """Show help dialog with keyboard shortcuts and usage tips"""
        help_window = tk.Toplevel(self.root)
        help_window.title("TuPono Tracker - Help")
        help_window.geometry("600x500")
        help_window.configure(bg=self.bg_color)
        help_window.transient(self.root)
        
        main_container = tk.Frame(help_window, bg=self.bg_color)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_card = tk.Frame(main_container, bg=self.primary_color, height=60)
        header_card.pack(fill="x", pady=(0, 20))
        header_card.pack_propagate(False)
        
        tk.Label(
            header_card,
            text="📖 TuPono Tracker Help",
            font=("Segoe UI", 16, "bold"),
            bg=self.primary_color,
            fg="white"
        ).pack(expand=True)
        
        # Content
        content_frame = tk.Frame(main_container, bg=self.card_bg)
        content_frame.pack(fill="both", expand=True)
        
        content_inner = tk.Frame(content_frame, bg=self.card_bg)
        content_inner.pack(fill="both", expand=True, padx=30, pady=30)
        
        help_text = """
🚀 GETTING STARTED:
• Fill in all participant information fields
• Select appropriate advocacy types if applicable
• Assign a Kaimahi to each participant
• Use the progress tracking to monitor weekly development

⌨️ KEYBOARD SHORTCUTS:
• Ctrl+N: New file
• Ctrl+O: Open file
• Ctrl+S: Save file
• Ctrl+E: Export to PDF
• Ctrl+Enter: Add participant
• F5: Show statistics
• F1: Show this help
• Ctrl+Q: Quit application

📊 PROGRESS TRACKING:
• Red Phase: Weeks 1-6 (Whitiwhiti Kōrero)
• Orange Phase: Weeks 7-14 (Program Implementation)
• Green Phase: Weeks 15-26 (Whānau Integration)
• Advocacy: Long-term support (up to 4 years)

💡 TIPS:
• Use the search function to quickly find participants
• Regular weekly assessments help track progress
• Export reports for stakeholder meetings
• Data is automatically saved when changes are made

🔍 SEARCH FUNCTIONALITY:
• Search by name, iwi, location, or phase
• Use partial matches for quick filtering
• Clear search to see all participants
        """
        
        help_label = tk.Label(
            content_inner,
            text=help_text,
            font=("Segoe UI", 10),
            bg=self.card_bg,
            fg=self.fg_color,
            justify="left",
            anchor="nw"
        )
        help_label.pack(fill="both", expand=True)
        
        # Close button
        tk.Button(
            main_container,
            text="✅ Close Help",
            font=("Segoe UI", 11, "bold"),
            bg=self.primary_color,
            fg="white",
            relief="flat",
            bd=0,
            padx=25,
            pady=10,
            cursor="hand2",
            command=help_window.destroy
        ).pack(pady=(15, 0))
        
        help_window.bind("<Escape>", lambda e: help_window.destroy())
        help_window.focus_force()

    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        pos_x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        pos_y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

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
        # Create main container with padding
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create header section
        self.create_header(main_container)
        
        # Create tabbed interface for better organization
        self.create_tabbed_interface(main_container)

        # Bottom Panel - Action Buttons
        self.create_action_panel(main_container)

    def create_tabbed_interface(self, parent):
        """Create a professional tabbed interface for better organization"""
        # Main content area for tabs
        content_frame = tk.Frame(parent, bg=self.bg_color)
        content_frame.pack(fill="both", expand=True, pady=(20, 0))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Tab 1: Participant Management
        self.create_participant_management_tab()
        
        # Tab 2: Progress & Tracking
        self.create_progress_tracking_tab()
        
        # Tab 3: Reports & Statistics
        self.create_reports_statistics_tab()
        
        # Tab 4: Data Management
        self.create_data_management_tab()
        
    def create_participant_management_tab(self):
        """Tab 1: Participant Management - Add, Edit, View participants"""
        tab1 = ttk.Frame(self.notebook)
        self.notebook.add(tab1, text="👤 Participants")
        
        # Two-panel layout: Form + List
        main_paned = tk.PanedWindow(tab1, orient=tk.HORIZONTAL, bg=self.bg_color, sashrelief=tk.FLAT, sashwidth=5)
        main_paned.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left: Participant Form
        form_container = tk.Frame(main_paned, bg=self.bg_color, width=500)
        main_paned.add(form_container, minsize=450, width=500)
        self.create_input_panel_fixed(form_container)
        
        # Right: Participants List
        list_container = tk.Frame(main_paned, bg=self.bg_color, width=450)
        main_paned.add(list_container, minsize=400, width=450)
        self.create_participants_panel_fixed(list_container)
        
    def create_progress_tracking_tab(self):
        """Tab 2: Progress Tracking - View detailed progress, assessments"""
        tab2 = ttk.Frame(self.notebook)
        self.notebook.add(tab2, text="📊 Progress")
        
        # Create scrollable frame for progress content
        canvas = tk.Canvas(tab2, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab2, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollbar and canvas
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Main progress content (now in scrollable frame)
        progress_content = tk.Frame(scrollable_frame, bg=self.bg_color)
        progress_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Participant selector at top
        selector_frame = tk.Frame(progress_content, bg=self.card_bg, relief="solid", bd=1)
        selector_frame.pack(fill="x", pady=(0, 20))
        
        selector_inner = tk.Frame(selector_frame, bg=self.card_bg)
        selector_inner.pack(fill="x", padx=20, pady=15)
        
        tk.Label(
            selector_inner,
            text="📋 Select Participant for Progress Review:",
            font=self.header_font,
            bg=self.card_bg,
            fg=self.primary_color
        ).pack(side="left")
        
        # Participant dropdown for progress view
        self.progress_participant_var = tk.StringVar()
        self.progress_participant_dropdown = ttk.Combobox(
            selector_inner,
            textvariable=self.progress_participant_var,
            state="readonly",
            font=self.body_font,
            width=40
        )
        self.progress_participant_dropdown.pack(side="right", padx=(20, 0))
        self.progress_participant_dropdown.bind("<<ComboboxSelected>>", self.on_progress_participant_change)
        
        # Progress details container - enhanced for dedicated tab
        self.create_enhanced_progress_display(progress_content)
        
    def create_reports_statistics_tab(self):
        """Tab 3: Reports & Statistics - Analytics, charts, reports"""
        tab3 = ttk.Frame(self.notebook)
        self.notebook.add(tab3, text="📈 Reports")
        
        reports_content = tk.Frame(tab3, bg=self.bg_color)
        reports_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_card = tk.Frame(reports_content, bg=self.card_bg, relief="solid", bd=1)
        header_card.pack(fill="x", pady=(0, 20))
        
        header_inner = tk.Frame(header_card, bg=self.card_bg)
        header_inner.pack(fill="x", padx=20, pady=15)
        
        tk.Label(
            header_inner,
            text="📊 Reports & Analytics Dashboard",
            font=("Segoe UI", 16, "bold"),
            bg=self.card_bg,
            fg=self.primary_color
        ).pack(side="left")
        
        # Quick stats display
        stats_frame = tk.Frame(reports_content, bg=self.bg_color)
        stats_frame.pack(fill="x", pady=(0, 20))
        
        self.create_quick_stats_cards(stats_frame)
        
        # Reports buttons
        reports_grid = tk.Frame(reports_content, bg=self.bg_color)
        reports_grid.pack(fill="both", expand=True)
        
        self.create_reports_buttons(reports_grid)
        
    def create_data_management_tab(self):
        """Tab 4: Data Management - Import, Export, Settings"""
        tab4 = ttk.Frame(self.notebook)
        self.notebook.add(tab4, text="⚙️ Data")
        
        data_content = tk.Frame(tab4, bg=self.bg_color)
        data_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # File Operations Section
        file_section = tk.LabelFrame(
            data_content,
            text="📁 File Operations",
            font=self.header_font,
            bg=self.card_bg,
            fg=self.primary_color,
            bd=2,
            relief="solid"
        )
        file_section.pack(fill="x", pady=(0, 20))
        
        file_inner = tk.Frame(file_section, bg=self.card_bg)
        file_inner.pack(fill="x", padx=20, pady=15)
        
        # File operation buttons
        file_buttons = [
            ("🆕 New Database", self.new_file, "Create a new empty participant database"),
            ("📂 Import Data", self.load_json_dialog, "Load participant data from JSON file"),
            ("💾 Export Data", self.save_json_dialog, "Save current data to JSON file"),
            ("📄 Generate PDF Report", self.export_to_pdf, "Export comprehensive PDF report")
        ]
        
        for i, (text, command, description) in enumerate(file_buttons):
            btn_frame = tk.Frame(file_inner, bg=self.card_bg)
            btn_frame.pack(fill="x", pady=5)
            
            btn = tk.Button(
                btn_frame,
                text=text,
                font=("Segoe UI", 11, "bold"),
                bg=self.accent_color,
                fg="white",
                relief="flat",
                bd=0,
                padx=20,
                pady=10,
                cursor="hand2",
                command=command,
                width=25
            )
            btn.pack(side="left")
            
            tk.Label(
                btn_frame,
                text=f"  {description}",
                font=("Segoe UI", 10),
                bg=self.card_bg,
                fg=self.fg_color
            ).pack(side="left", padx=(15, 0))
        
        # Application Settings Section
        settings_section = tk.LabelFrame(
            data_content,
            text="⚙️ Application Settings",
            font=self.header_font,
            bg=self.card_bg,
            fg=self.primary_color,
            bd=2,
            relief="solid"
        )
        settings_section.pack(fill="both", expand=True)
        
        settings_inner = tk.Frame(settings_section, bg=self.card_bg)
        settings_inner.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Help and about information
        help_text = '''
🔧 APPLICATION INFORMATION

Version: TuPono Tracker v3.0 Professional
Author: TuPono IP Team
Last Updated: October 2024

📘 KEYBOARD SHORTCUTS:
• Ctrl+N: New database
• Ctrl+O: Open/Import data
• Ctrl+S: Save/Export data
• Ctrl+E: Export PDF report
• F1: Show help
• F5: Refresh statistics

📊 DATA MANAGEMENT:
• All data is automatically saved
• Export regular backups using "Export Data"
• PDF reports include all charts and statistics
• Search functionality available in Participants tab

🎯 PROGRAM PHASES:
• Red Phase: Weeks 1-6 (Whitiwhiti Kōrero)
• Orange Phase: Weeks 7-14 (Program Implementation) 
• Green Phase: Weeks 15-26 (Whānau Integration)
• Advocacy: Long-term support (up to 4 years)
        '''
        
        help_label = tk.Label(
            settings_inner,
            text=help_text,
            font=("Segoe UI", 10),
            bg=self.card_bg,
            fg=self.fg_color,
            justify="left",
            anchor="nw"
        )
        help_label.pack(fill="both", expand=True)
    
    # Compatibility methods for any remaining references
    def create_input_panel(self, parent):
        return self.create_input_panel_fixed(parent)
    
    def create_progress_panel(self, parent):
        return self.create_progress_panel_fixed(parent)
        
    def create_participants_panel(self, parent):
        return self.create_participants_panel_fixed(parent)        # Configure main window grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.update_participants_list()

    def on_progress_participant_change(self, event=None):
        """Handle selection change in progress tab participant dropdown"""
        selected = self.progress_participant_var.get()
        if selected and " - " in selected:
            participant_name = selected.split(" - ")[0]
            # Find and select the participant
            for participant in self.participants:
                if participant.name == participant_name:
                    self.current_participant = participant
                    self.current_participant.update_progress()
                    self.update_progress_display()
                    break

    def create_quick_stats_cards(self, parent):
        """Create quick statistics cards for reports tab"""
        stats_container = tk.Frame(parent, bg=self.bg_color)
        stats_container.pack(fill="x")
        
        # Calculate basic statistics
        total_participants = len(self.participants)
        completed_count = sum(1 for p in self.participants if p.phase == "completed")
        advocacy_count = sum(1 for p in self.participants if p.advocacy and len(p.advocacy) > 0)
        
        stats_data = [
            ("👥 Total Participants", str(total_participants), self.accent_color),
            ("✅ Completed Program", str(completed_count), self.accent_color),
            ("🎯 With Advocacy", str(advocacy_count), self.info_color),
            ("📊 Completion Rate", f"{(completed_count/total_participants*100):.1f}%" if total_participants > 0 else "0%", self.warning_color)
        ]
        
        for i, (title, value, color) in enumerate(stats_data):
            card = tk.Frame(stats_container, bg=color, relief="solid", bd=1)
            card.pack(side="left", fill="both", expand=True, padx=5)
            
            card_inner = tk.Frame(card, bg=color)
            card_inner.pack(fill="both", expand=True, padx=15, pady=10)
            
            tk.Label(
                card_inner,
                text=value,
                font=("Segoe UI", 18, "bold"),
                bg=color,
                fg="white"
            ).pack()
            
            tk.Label(
                card_inner,
                text=title,
                font=("Segoe UI", 10),
                bg=color,
                fg="white"
            ).pack()

    def create_reports_buttons(self, parent):
        """Create report generation buttons - only functional ones"""
        reports_frame = tk.Frame(parent, bg=self.bg_color)
        reports_frame.pack(fill="both", expand=True)
        
        # Center container for the single button
        center_container = tk.Frame(reports_frame, bg=self.bg_color)
        center_container.pack(expand=True)
        
        # Single functional report card - Program Statistics
        card = tk.Frame(center_container, bg=self.card_bg, relief="solid", bd=1)
        card.pack(pady=50)
        
        card_inner = tk.Frame(card, bg=self.card_bg)
        card_inner.pack(fill="both", expand=True, padx=40, pady=30)
        
        tk.Label(
            card_inner,
            text="📊 Program Statistics",
            font=("Segoe UI", 18, "bold"),
            bg=self.card_bg,
            fg=self.primary_color
        ).pack(pady=(0, 15))
        
        tk.Label(
            card_inner,
            text="View comprehensive program statistics and charts\nincluding participant progress, phase distribution,\nand advocacy tracking analytics",
            font=("Segoe UI", 12),
            bg=self.card_bg,
            fg=self.fg_color,
            justify="center"
        ).pack(pady=(0, 20))
        
        tk.Button(
            card_inner,
            text="📈 Generate Statistics Report",
            font=("Segoe UI", 12, "bold"),
            bg=self.accent_color,
            fg="white",
            relief="flat",
            bd=0,
            padx=30,
            pady=12,
            cursor="hand2",
            command=self.show_statistics
        ).pack()



    def update_progress_participant_dropdown(self):
        """Update the participant dropdown in progress tab"""
        if hasattr(self, 'progress_participant_dropdown'):
            participant_list = [f"{p.name} - {p.phase.upper()}" for p in self.sorted_participants]
            self.progress_participant_dropdown['values'] = participant_list
            if participant_list:
                self.progress_participant_dropdown.set("Select participant...")

    def create_enhanced_progress_display(self, parent):
        """Create enhanced progress display for the dedicated Progress tab"""
        # Main progress container
        progress_main = tk.Frame(parent, bg=self.bg_color)
        progress_main.pack(fill="both", expand=True)
        
        # Status and info section
        status_card = tk.Frame(progress_main, bg=self.card_bg, relief="solid", bd=1)
        status_card.pack(fill="x", pady=(0, 20))
        
        status_inner = tk.Frame(status_card, bg=self.card_bg)
        status_inner.pack(fill="x", padx=20, pady=15)
        
        # Status display
        self.progress_status_label = tk.Label(
            status_inner,
            text="Status: Select a participant above",
            font=("Segoe UI", 14, "bold"),
            bg=self.card_bg,
            fg=self.fg_color
        )
        self.progress_status_label.pack(anchor="w", pady=(0, 5))
        
        self.progress_program_label = tk.Label(
            status_inner,
            text="Programs: Not selected",
            font=("Segoe UI", 12),
            bg=self.card_bg,
            fg=self.fg_color
        )
        self.progress_program_label.pack(anchor="w")
        
        # Progress visualization section
        viz_card = tk.Frame(progress_main, bg=self.card_bg, relief="solid", bd=1)
        viz_card.pack(fill="both", expand=True, pady=(0, 20))
        
        viz_inner = tk.Frame(viz_card, bg=self.card_bg)
        viz_inner.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Progress bars title
        tk.Label(
            viz_inner,
            text="📊 Progress Visualization",
            font=("Segoe UI", 16, "bold"),
            bg=self.card_bg,
            fg=self.primary_color
        ).pack(anchor="w", pady=(0, 15))
        
        # Progress canvas container with scrollable support
        canvas_container = tk.Frame(viz_inner, bg=self.secondary_bg, relief="solid", bd=1)
        canvas_container.pack(fill="both", expand=True, pady=(0, 20))
        
        # Enhanced progress canvas - wider for weekly tick marks
        self.enhanced_progress_canvas = tk.Canvas(
            canvas_container,
            width=1200,
            height=200,
            bg=self.progress_bg,
            highlightthickness=0
        )
        self.enhanced_progress_canvas.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        
        # Add horizontal scrollbar for wide progress bars
        h_scrollbar = tk.Scrollbar(canvas_container, orient="horizontal", command=self.enhanced_progress_canvas.xview)
        self.enhanced_progress_canvas.configure(xscrollcommand=h_scrollbar.set, scrollregion=(0, 0, 1200, 200))
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Progress legend
        legend_frame = tk.Frame(viz_inner, bg=self.card_bg)
        legend_frame.pack(fill="x", pady=(30, 20))
        
        tk.Label(
            legend_frame,
            text="📋 Phase Legend:",
            font=("Segoe UI", 12, "bold"),
            bg=self.card_bg,
            fg=self.fg_color
        ).pack(side="left", padx=(0, 20))
        
        # Legend items
        legend_items = [
            ("RED (Weeks 1-6)", "#FF4757", "Whitiwhiti Kōrero"),
            ("ORANGE (Weeks 7-14)", "#FFA502", "Program Implementation"),
            ("GREEN (Weeks 15-26)", "#2ED573", "Whānau Integration"),
            ("ADVOCACY", "#3742FA", "Long-term Support")
        ]
        
        for phase, color, description in legend_items:
            legend_item = tk.Frame(legend_frame, bg=self.card_bg)
            legend_item.pack(side="left", padx=10)
            
            color_box = tk.Frame(legend_item, bg=color, width=20, height=20)
            color_box.pack(side="left", padx=(0, 5))
            color_box.pack_propagate(False)
            
            tk.Label(
                legend_item,
                text=f"{phase}\n{description}",
                font=("Segoe UI", 9),
                bg=self.card_bg,
                fg=self.fg_color,
                justify="left"
            ).pack(side="left")
        
        # Action buttons section
        action_card = tk.Frame(progress_main, bg=self.card_bg, relief="solid", bd=1)
        action_card.pack(fill="x")
        
        action_inner = tk.Frame(action_card, bg=self.card_bg)
        action_inner.pack(fill="x", padx=20, pady=15)
        
        tk.Label(
            action_inner,
            text="🛠️ Progress Actions",
            font=("Segoe UI", 14, "bold"),
            bg=self.card_bg,
            fg=self.primary_color
        ).pack(anchor="w", pady=(0, 15))
        
        # Action buttons
        buttons_frame = tk.Frame(action_inner, bg=self.card_bg)
        buttons_frame.pack(fill="x")
        
        button_style = {
            "font": ("Segoe UI", 11, "bold"),
            "relief": "flat",
            "bd": 0,
            "padx": 20,
            "pady": 12,
            "cursor": "hand2"
        }
        
        # Program management
        self.progress_set_programs_btn = tk.Button(
            buttons_frame,
            text="📚 Set Programs",
            bg=self.accent_color,
            fg="white",
            disabledforeground="white",
            state="disabled",
            command=self.set_programs,
            **button_style
        )
        self.progress_set_programs_btn.pack(side="left", padx=(0, 10))
        
        # Assessment buttons
        self.progress_assessment_btn = tk.Button(
            buttons_frame,
            text="📝 Weekly Assessment",
            bg=self.warning_color,
            fg="black",
            disabledforeground="white",
            state="disabled",
            command=self.show_assessment,
            **button_style
        )
        self.progress_assessment_btn.pack(side="left", padx=10)
        
        self.progress_review_btn = tk.Button(
            buttons_frame,
            text="📊 Review Assessments",
            bg=self.info_color,
            fg="white",
            disabledforeground="white",
            state="disabled",
            command=self.review_assessments,
            **button_style
        )
        self.progress_review_btn.pack(side="left", padx=10)
        
        # Add program selection listbox (initially hidden)
        self.create_program_selection_area(action_inner)

    def create_program_selection_area(self, parent):
        """Create program selection area for progress tab"""
        # Program selection section (initially hidden)
        self.program_selection_frame = tk.Frame(parent, bg=self.card_bg)
        
        tk.Label(
            self.program_selection_frame,
            text="📚 Available Programs:",
            font=("Segoe UI", 12, "bold"),
            bg=self.card_bg,
            fg=self.fg_color
        ).pack(anchor="w", pady=(20, 10))
        
        # Program listbox
        listbox_container = tk.Frame(self.program_selection_frame, bg=self.border_color, bd=1)
        listbox_container.pack(fill="x")
        
        self.progress_program_listbox = tk.Listbox(
            listbox_container,
            height=4,
            selectmode="multiple",
            font=self.body_font,
            bg=self.card_bg,
            fg=self.fg_color,
            selectbackground=self.accent_color,
            selectforeground="white",
            bd=0,
            highlightthickness=0
        )
        
        programs = ["Ko wai au", "Mental Health and Well-being", "Anger Management", "Domestic Violence"]
        for program in programs:
            self.progress_program_listbox.insert(tk.END, program)
        
        self.progress_program_listbox.pack(fill="x", padx=1, pady=1)

    def draw_enhanced_progress_bar(self):
        """Draw enhanced progress bars in the dedicated progress tab"""
        if not hasattr(self, 'enhanced_progress_canvas'):
            return
            
        self.enhanced_progress_canvas.delete("all")
        
        if not self.current_participant:
            # Draw placeholder with instructions
            self.enhanced_progress_canvas.create_text(
                400, 75,
                text="Select a participant above to view detailed progress visualization",
                font=("Segoe UI", 14),
                fill="#888888",
                justify="center"
            )
            return

        # Get canvas dimensions
        canvas_width = 800
        canvas_height = 150
        
        # Calculate layout
        total_weeks = 26
        cell_width = (canvas_width - 60) / total_weeks  # Leave margins
        bar_height = 35
        margin = 30
        
        today = datetime.now().date()
        current_week = (today - self.current_participant.signup_date).days // 7

        # Modern color scheme
        PROGRESS_COLORS = {
            "red": {"fill": "#FF4757", "outline": "#FF3838", "text": "white"},
            "orange": {"fill": "#FFA502", "outline": "#FF8C00", "text": "black"},
            "green": {"fill": "#2ED573", "outline": "#2BC152", "text": "white"},
            "advocacy_active": {"fill": "#3742FA", "outline": "#2F2ED3", "text": "white"}
        }

        # Draw title
        self.enhanced_progress_canvas.create_text(
            canvas_width / 2, 20,
            text=f"26-Week Program Progress: {self.current_participant.name}",
            font=("Segoe UI", 14, "bold"),
            fill=self.fg_color
        )

        # Draw main 26-week progress bar
        y_offset = 45
        for week in range(total_weeks):
            x1 = margin + week * cell_width
            x2 = x1 + cell_width - 1
            y1 = y_offset
            y2 = y1 + bar_height

            # Determine color based on progress
            if week < len(self.current_participant.weekly_progress):
                color_key = self.current_participant.weekly_progress[week]
            else:
                color_key = ""
                
            is_current = week == current_week
            
            if color_key in PROGRESS_COLORS:
                colors = PROGRESS_COLORS[color_key]
                fill = colors["fill"]
                outline = colors["outline"]
                text_color = colors["text"]
            else:
                fill = "#E0E0E0"
                outline = "#BDBDBD"
                text_color = "#757575"

            # Add glow effect for current week
            if is_current:
                self.enhanced_progress_canvas.create_rectangle(
                    x1 - 2, y1 - 2, x2 + 2, y2 + 2,
                    fill="", outline="#FFD700", width=3
                )

            # Main rectangle
            self.enhanced_progress_canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=fill, outline=outline, width=2 if is_current else 1
            )
            
            # Add highlight
            self.enhanced_progress_canvas.create_line(
                x1 + 1, y1 + 1, x2 - 1, y1 + 1,
                fill="white", width=1
            )

            # Week number labels (every week now that we have space)
            self.enhanced_progress_canvas.create_text(
                x1 + cell_width / 2,
                y1 + bar_height / 2,
                text=str(week + 1),
                font=("Segoe UI", 8, "bold"),
                fill=text_color
            )
            
            # Weekly tick marks below the bar
            tick_x = x1 + cell_width / 2
            tick_start_y = y2 + 2
            tick_end_y = tick_start_y + 8
            
            # Different tick heights for different intervals
            if (week + 1) % 5 == 0:  # Every 5 weeks - longer tick
                tick_end_y = tick_start_y + 12
                tick_color = "#333333"
                tick_width = 2
            elif (week + 1) % 2 == 0:  # Every 2 weeks - medium tick  
                tick_end_y = tick_start_y + 10
                tick_color = "#666666"
                tick_width = 1
            else:  # Every week - small tick
                tick_color = "#999999"
                tick_width = 1
            
            self.enhanced_progress_canvas.create_line(
                tick_x, tick_start_y, tick_x, tick_end_y,
                fill=tick_color, width=tick_width
            )

        # Phase boundary lines and labels
        phase_boundaries = [6, 14]  # Red->Orange, Orange->Green
        phase_y = y_offset + bar_height + 15
        
        for boundary in phase_boundaries:
            x_pos = margin + boundary * cell_width
            self.enhanced_progress_canvas.create_line(
                x_pos, y_offset, x_pos, y_offset + bar_height,
                fill="#333333", width=2, dash=(3, 3)
            )

        # Phase labels
        phase_labels = [
            (margin + 3 * cell_width, "RED PHASE", "#FF6B6B"),
            (margin + 10 * cell_width, "ORANGE PHASE", "#FFB74D"),
            (margin + 20 * cell_width, "GREEN PHASE", "#66BB6A")
        ]
        
        for x_pos, label, color in phase_labels:
            self.enhanced_progress_canvas.create_text(
                x_pos, phase_y,
                text=label,
                font=("Segoe UI", 10, "bold"),
                fill=color
            )

        # Draw advocacy bar if applicable
        if (hasattr(self.current_participant, 'advocacy') and 
            self.current_participant.advocacy and 
            len(self.current_participant.advocacy) > 0):
            
            self.draw_advocacy_progress_bar(canvas_width, y_offset + bar_height + 60)

    def draw_advocacy_progress_bar(self, canvas_width, y_start):
        """Draw the enhanced advocacy progress bar with tick marks every 3 months"""
        advocacy_height = 30
        margin = 30
        
        # Title
        self.enhanced_progress_canvas.create_text(
            canvas_width / 2, y_start - 15,
            text=f"Advocacy Progress: {', '.join(self.current_participant.advocacy)}",
            font=("Segoe UI", 12, "bold"),
            fill=self.fg_color
        )
        
        # Extended time blocks for advocacy (6 years total)
        blocks = [
            (0, 52, "Year 1"),
            (52, 104, "Year 2"),
            (104, 156, "Year 3"),
            (156, 208, "Year 4"),
            (208, 260, "Year 5"),
            (260, 312, "Year 6")
        ]
        
        block_width = (canvas_width - 2 * margin) / len(blocks)
        weeks_completed = getattr(self.current_participant, 'advocacy_weeks_completed', 0)
        
        for i, (start_week, end_week, label) in enumerate(blocks):
            x1 = margin + i * block_width
            x2 = x1 + block_width - 2
            y1 = y_start
            y2 = y1 + advocacy_height
            
            is_active = weeks_completed >= start_week
            is_current = start_week <= weeks_completed < end_week
            
            if is_active:
                fill = "#335DAB"
                outline = "#FFD700" if is_current else "#1976D2"
                width = 3 if is_current else 1
            else:
                fill = "#E0E0E0"
                outline = "#BDBDBD"
                width = 1
            
            self.enhanced_progress_canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=fill, outline=outline, width=width
            )
            
            # Label
            self.enhanced_progress_canvas.create_text(
                x1 + block_width / 2,
                y1 + advocacy_height / 2,
                text=label,
                font=("Segoe UI", 9, "bold"),
                fill="white" if is_active else "#666666"
            )
        
        # Add tick marks every 3 months (13 weeks)
        total_bar_width = canvas_width - 2 * margin
        total_weeks = 312  # 6 years
        
        for months in range(0, 73, 3):  # 0 to 72 months (6 years) in 3-month intervals
            week_position = months * 4.33  # Approximate weeks per month
            if week_position <= total_weeks:
                x_pos = margin + (week_position / total_weeks) * total_bar_width
                
                # Draw tick mark
                tick_height = 8
                self.enhanced_progress_canvas.create_line(
                    x_pos, y_start + advocacy_height,
                    x_pos, y_start + advocacy_height + tick_height,
                    fill="#333333", width=2
                )
                
                # Add month label every 6 months for clarity
                if months % 6 == 0 and months > 0:
                    years = months // 12
                    remaining_months = months % 12
                    if remaining_months == 0:
                        label_text = f"{years}y"
                    else:
                        label_text = f"{years}y{remaining_months}m"
                    
                    self.enhanced_progress_canvas.create_text(
                        x_pos, y_start + advocacy_height + tick_height + 12,
                        text=label_text,
                        font=("Segoe UI", 8),
                        fill="#666666"
                    )

    def create_header(self, parent):
        """Create the application header with title and branding"""
        header_frame = tk.Frame(parent, bg=self.primary_color, height=80)
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="TuPono IP - Māori Support Program Tracker",
            font=("Segoe UI", 20, "bold"),
            bg=self.primary_color,
            fg="white"
        )
        title_label.pack(side="left", padx=30, pady=20)
        
        # Status indicator
        self.header_status = tk.Label(
            header_frame,
            text=f"Participants: {len(self.participants)}",
            font=self.body_font,
            bg=self.primary_color,
            fg="white"
        )
        self.header_status.pack(side="right", padx=30, pady=20)

    def create_input_panel_fixed(self, parent):
        """Create the participant information input panel with fixed sizing"""
        # Main input container
        input_container = tk.Frame(parent, bg=self.bg_color)
        input_container.pack(fill="both", expand=True, padx=(0, 5))
        
        # Card frame with shadow effect
        input_card = tk.Frame(input_container, bg=self.card_bg, relief="flat", bd=0)
        input_card.pack(fill="both", expand=True)
        
        # Add subtle border
        border_frame = tk.Frame(input_card, bg=self.border_color, height=2)
        border_frame.pack(fill="x")
        
        # Header (fixed at top)
        header_frame = tk.Frame(input_card, bg=self.card_bg)
        header_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        tk.Label(
            header_frame,
            text="👤 Participant Information",
            font=self.header_font,
            bg=self.card_bg,
            fg=self.primary_color
        ).pack(side="left")
        
        # Scrollable content area
        scroll_container = tk.Frame(input_card, bg=self.card_bg)
        scroll_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Create canvas and scrollbar for scrolling
        self.input_canvas = tk.Canvas(
            scroll_container, 
            bg=self.card_bg, 
            highlightthickness=0,
            bd=0
        )
        
        input_scrollbar = ttk.Scrollbar(
            scroll_container, 
            orient="vertical", 
            command=self.input_canvas.yview
        )
        
        self.scrollable_input_frame = tk.Frame(self.input_canvas, bg=self.card_bg)
        
        # Configure scrolling
        self.scrollable_input_frame.bind(
            "<Configure>",
            lambda e: self.input_canvas.configure(scrollregion=self.input_canvas.bbox("all"))
        )
        
        self.input_canvas.create_window((0, 0), window=self.scrollable_input_frame, anchor="nw")
        self.input_canvas.configure(yscrollcommand=input_scrollbar.set)
        
        # Pack canvas and scrollbar
        self.input_canvas.pack(side="left", fill="both", expand=True)
        input_scrollbar.pack(side="right", fill="y")
        
        # Add mouse wheel scrolling with better sensitivity
        def _on_mousewheel(event):
            self.input_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mouse wheel to canvas and all child widgets
        def bind_to_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                bind_to_mousewheel(child)
        
        bind_to_mousewheel(self.scrollable_input_frame)
        self.input_canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Add keyboard scrolling
        def on_key_scroll(event):
            if event.keysym == "Up":
                self.input_canvas.yview_scroll(-1, "units")
            elif event.keysym == "Down":
                self.input_canvas.yview_scroll(1, "units")
            elif event.keysym == "Prior":  # Page Up
                self.input_canvas.yview_scroll(-5, "units")
            elif event.keysym == "Next":   # Page Down
                self.input_canvas.yview_scroll(5, "units")
        
        self.input_canvas.bind("<Up>", on_key_scroll)
        self.input_canvas.bind("<Down>", on_key_scroll)
        self.input_canvas.bind("<Prior>", on_key_scroll)
        self.input_canvas.bind("<Next>", on_key_scroll)
        self.input_canvas.focus_set()
        
        # Input fields with modern styling (now in scrollable frame)
        self.create_form_fields(self.scrollable_input_frame)
        
        # Update scroll region after creating widgets
        self.input_canvas.update_idletasks()
        self.input_canvas.configure(scrollregion=self.input_canvas.bbox("all"))

    def create_form_fields(self, parent):
        """Create styled form fields"""
        fields = [
            ("Full Name", "name_entry"),
            ("Age", "age_entry"),
            ("Gender", "gender_dropdown"),
            ("Location", "location_entry"),
            ("Iwi Affiliation", "iwi_entry"),
            ("Hapū Affiliation", "hapu_entry"),
            ("Start Date (YYYY-MM-DD)", "date_entry"),
            ("Assigned Kaimahi", "kaimahi_dropdown")
        ]
        
        for i, (label_text, widget_name) in enumerate(fields):
            # Field container
            field_frame = tk.Frame(parent, bg=self.card_bg)
            field_frame.pack(fill="x", pady=(0, 15))
            
            # Label
            label = tk.Label(
                field_frame,
                text=label_text,
                font=("Segoe UI", 10, "bold"),
                bg=self.card_bg,
                fg="black"
            )
            label.pack(anchor="w", pady=(0, 5))
            
            # Widget
            if "dropdown" in widget_name:
                if "gender" in widget_name:
                    self.gender_var = tk.StringVar()
                    widget = ttk.Combobox(
                        field_frame,
                        textvariable=self.gender_var,
                        values=["Male", "Female", "Non-binary"],
                        state="readonly",
                        font=self.body_font
                    )
                elif "kaimahi" in widget_name:
                    self.kaimahi_var = tk.StringVar()
                    widget = ttk.Combobox(
                        field_frame,
                        textvariable=self.kaimahi_var,
                        values=KAIMAHI_LIST,
                        state="readonly",
                        font=self.body_font
                    )
            else:
                widget = ttk.Entry(field_frame, font=self.body_font)
            
            widget.pack(fill="x")
            setattr(self, widget_name, widget)
        
        # Advocacy section - Dropdown style like gender
        advocacy_frame = tk.Frame(parent, bg=self.card_bg)
        advocacy_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            advocacy_frame,
            text="Advocacy Support",
            font=("Segoe UI", 10, "bold"),
            bg=self.card_bg,
            fg="black"
        ).pack(anchor="w", pady=(0, 5))
        
        # Create advocacy dropdown to match gender dropdown styling
        self.advocacy_var = tk.StringVar()
        self.advocacy_dropdown = ttk.Combobox(
            advocacy_frame,
            textvariable=self.advocacy_var,
            values=["Click to select advocacy types..."] + ADVOCACY_TYPES + ["Multiple selections..."],
            state="readonly",
            font=self.body_font
        )
        self.advocacy_dropdown.pack(fill="x")
        self.advocacy_dropdown.set("Click to select advocacy types...")
        
        # Bind the dropdown to open selection dialog
        self.advocacy_dropdown.bind("<<ComboboxSelected>>", self.on_advocacy_dropdown_change)
        
        # Track selected advocacy types (hidden from user)
        self.selected_advocacy_types = []
        
        # Action buttons
        button_frame = tk.Frame(parent, bg=self.card_bg)
        button_frame.pack(fill="x", pady=(20, 0))
        
        self.add_button = tk.Button(
            button_frame,
            text="➕ Add Participant",
            font=("Segoe UI", 11, "bold"),
            bg=self.accent_color,
            fg="white",
            disabledforeground="white",
            relief="flat",
            bd=0,
            padx=20,
            pady=12,
            cursor="hand2",
            command=self.add_participant
        )
        self.add_button.pack(fill="x", pady=(0, 10))
        
        self.update_button = tk.Button(
            button_frame,
            text="✏️ Update Participant",
            font=("Segoe UI", 11, "bold"),
            bg=self.info_color,
            fg="white",
            disabledforeground="white",
            relief="flat",
            bd=0,
            padx=20,
            pady=12,
            cursor="hand2",
            state="disabled",
            command=self.update_participant
        )
        self.update_button.pack(fill="x")
        
        # Add some bottom padding for better scrolling
        bottom_padding = tk.Frame(parent, bg=self.card_bg, height=30)
        bottom_padding.pack(fill="x")

    def on_advocacy_dropdown_change(self, event=None):
        """Handle advocacy dropdown selection"""
        selected = self.advocacy_dropdown.get()
        
        if selected == "Click to select advocacy types...":
            return
            
        if selected in ADVOCACY_TYPES:
            # Single advocacy type selected - toggle it
            if selected in self.selected_advocacy_types:
                self.selected_advocacy_types.remove(selected)
            else:
                self.selected_advocacy_types.append(selected)
            self.update_advocacy_dropdown_display()
        elif selected == "Multiple selections...":
            # Open multi-select dialog
            self.show_advocacy_selection_dialog()
    
    def show_advocacy_selection_dialog(self):
        """Show a dialog for selecting multiple advocacy types"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Advocacy Types")
        dialog.geometry("350x280")
        dialog.configure(bg=self.bg_color)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (350 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (280 // 2)
        dialog.geometry(f"350x280+{x}+{y}")
        
        # Header
        header_frame = tk.Frame(dialog, bg=self.primary_color, height=50)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text="Select Advocacy Types",
            font=("Segoe UI", 14, "bold"),
            bg=self.primary_color,
            fg="white"
        ).pack(expand=True)
        
        # Content
        content_frame = tk.Frame(dialog, bg=self.card_bg)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        tk.Label(
            content_frame,
            text="Check all advocacy types that apply:",
            font=("Segoe UI", 10),
            bg=self.card_bg,
            fg=self.fg_color
        ).pack(anchor="w", pady=(0, 10))
        
        # Checkboxes
        temp_vars = {}
        for advocacy_type in ADVOCACY_TYPES:
            var = tk.BooleanVar()
            var.set(advocacy_type in self.selected_advocacy_types)
            temp_vars[advocacy_type] = var
            
            checkbox = tk.Checkbutton(
                content_frame,
                text=advocacy_type,
                variable=var,
                font=("Segoe UI", 10),
                bg=self.card_bg,
                fg=self.fg_color,
                selectcolor=self.accent_color,
                activebackground=self.secondary_bg,
                bd=0,
                padx=5,
                pady=3,
                anchor="w"
            )
            checkbox.pack(fill="x", pady=2)
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=self.card_bg)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        def apply_selection():
            self.selected_advocacy_types = [
                advocacy for advocacy, var in temp_vars.items() if var.get()
            ]
            self.update_advocacy_dropdown_display()
            dialog.destroy()
        
        def cancel_selection():
            dialog.destroy()
        
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            font=("Segoe UI", 9, "bold"),
            bg=self.danger_color,
            fg="white",
            relief="flat",
            bd=0,
            padx=15,
            pady=6,
            cursor="hand2",
            command=cancel_selection
        )
        cancel_btn.pack(side="right", padx=(10, 0))
        
        apply_btn = tk.Button(
            button_frame,
            text="✓ Apply",
            font=("Segoe UI", 9, "bold"),
            bg=self.accent_color,
            fg="white",
            relief="flat",
            bd=0,
            padx=15,
            pady=6,
            cursor="hand2",
            command=apply_selection
        )
        apply_btn.pack(side="right")
        
        # Keyboard shortcuts
        dialog.bind("<Return>", lambda e: apply_selection())
        dialog.bind("<Escape>", lambda e: cancel_selection())
        dialog.focus_force()
    
    def update_advocacy_dropdown_display(self):
        """Update the dropdown display text based on selections"""
        if not self.selected_advocacy_types:
            self.advocacy_dropdown.set("Click to select advocacy types...")
        elif len(self.selected_advocacy_types) == 1:
            self.advocacy_dropdown.set(self.selected_advocacy_types[0])
        else:
            self.advocacy_dropdown.set(f"{len(self.selected_advocacy_types)} advocacy types selected")

    def get_selected_advocacy(self):
        """Get list of selected advocacy types"""
        return self.selected_advocacy_types.copy()
    
    def set_selected_advocacy(self, selected_advocacy):
        """Set the selected advocacy types"""
        self.selected_advocacy_types = selected_advocacy.copy() if selected_advocacy else []
        self.update_advocacy_dropdown_display()

    def create_progress_panel_fixed(self, parent):
        """Create the progress tracking panel with controlled sizing"""
        progress_container = tk.Frame(parent, bg=self.bg_color)
        progress_container.pack(fill="both", expand=True, padx=(5, 5))
        
        # Progress card
        progress_card = tk.Frame(progress_container, bg=self.card_bg, relief="flat", bd=0)
        progress_card.pack(fill="both", expand=True)
        
        # Add border
        border_frame = tk.Frame(progress_card, bg=self.border_color, height=2)
        border_frame.pack(fill="x")
        
        # Header
        header_frame = tk.Frame(progress_card, bg=self.card_bg)
        header_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        tk.Label(
            header_frame,
            text="📈 Progress Tracking",
            font=self.header_font,
            bg=self.card_bg,
            fg=self.primary_color
        ).pack(side="left")
        
        # Content
        content_frame = tk.Frame(progress_card, bg=self.card_bg)
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Status display
        self.status_label = tk.Label(
            content_frame,
            text="Status: No participant selected",
            font=("Segoe UI", 12, "bold"),
            bg=self.card_bg,
            fg=self.fg_color
        )
        self.status_label.pack(anchor="w", pady=(0, 10))
        
        self.program_label = tk.Label(
            content_frame,
            text="Programs: Not selected",
            font=self.body_font,
            bg=self.card_bg,
            fg=self.fg_color
        )
        self.program_label.pack(anchor="w", pady=(0, 15))
        
        # Progress visualization
        progress_viz_frame = tk.Frame(content_frame, bg=self.card_bg)
        progress_viz_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            progress_viz_frame,
            text="Weekly Progress Overview",
            font=("Segoe UI", 11, "bold"),
            bg=self.card_bg,
            fg=self.fg_color
        ).pack(anchor="w", pady=(0, 8))
        
        canvas_frame = tk.Frame(progress_viz_frame, bg=self.border_color, bd=1)
        canvas_frame.pack(fill="x")
        
        self.progress_canvas = tk.Canvas(
            canvas_frame,
            width=400,
            height=120,
            bg=self.progress_bg,
            highlightthickness=0
        )
        self.progress_canvas.pack(padx=2, pady=2)
        # Prevent canvas from expanding beyond set dimensions
        canvas_frame.pack_propagate(False)
        
        # Program management
        program_mgmt_frame = tk.Frame(content_frame, bg=self.card_bg)
        program_mgmt_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            program_mgmt_frame,
            text="Assign Programs",
            font=("Segoe UI", 11, "bold"),
            bg=self.card_bg,
            fg=self.fg_color
        ).pack(anchor="w", pady=(0, 8))
        
        listbox_frame = tk.Frame(program_mgmt_frame, bg=self.border_color, bd=1)
        listbox_frame.pack(fill="x")
        
        self.program_listbox = tk.Listbox(
            listbox_frame,
            height=4,
            selectmode="multiple",
            font=self.body_font,
            bg=self.card_bg,
            fg=self.fg_color,
            selectbackground=self.accent_color,
            selectforeground="white",
            bd=0,
            highlightthickness=0
        )
        
        programs = ["Ko wai au", "Mental Health and Well-being", "Anger Management", "Domestic Violence"]
        for program in programs:
            self.program_listbox.insert(tk.END, program)
        self.program_listbox.pack(fill="both", expand=True, padx=1, pady=1)
        
        # Action buttons for progress
        action_frame = tk.Frame(content_frame, bg=self.card_bg)
        action_frame.pack(fill="x")
        
        button_style = {
            "font": ("Segoe UI", 10, "bold"),
            "relief": "flat",
            "bd": 0,
            "padx": 15,
            "pady": 10,
            "cursor": "hand2"
        }
        
        self.select_program_button = tk.Button(
            action_frame,
            text="✅ Set Programs",
            bg=self.accent_color,
            fg="white",
            state="disabled",
            command=self.set_programs,
            **button_style
        )
        self.select_program_button.pack(fill="x", pady=(0, 8))
        
        self.assessment_button = tk.Button(
            action_frame,
            text="📝 Weekly Assessment",
            bg=self.warning_color,
            fg="black",
            state="disabled",
            command=self.show_assessment,
            **button_style
        )
        self.assessment_button.pack(fill="x", pady=(0, 8))
        
        self.review_assessment_button = tk.Button(
            action_frame,
            text="📊 Review Assessments",
            bg=self.info_color,
            fg="white",
            state="disabled",
            command=self.review_assessments,
            **button_style
        )
        self.review_assessment_button.pack(fill="x", pady=(0, 8))
        
        self.stats_button = tk.Button(
            action_frame,
            text="📈 View Statistics",
            bg=self.primary_color,
            fg="white",
            command=self.show_statistics,
            **button_style
        )
        self.stats_button.pack(fill="x")

    def create_participants_panel_fixed(self, parent):
        """Create the participants list panel with guaranteed minimum size"""
        list_container = tk.Frame(parent, bg=self.bg_color)
        list_container.pack(fill="both", expand=True, padx=(5, 0))
        
        # List card
        list_card = tk.Frame(list_container, bg=self.card_bg, relief="flat", bd=0)
        list_card.pack(fill="both", expand=True)
        
        # Add border
        border_frame = tk.Frame(list_card, bg=self.border_color, height=2)
        border_frame.pack(fill="x")
        
        # Header with search
        header_frame = tk.Frame(list_card, bg=self.card_bg)
        header_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        tk.Label(
            header_frame,
            text="👥 Participants List",
            font=self.header_font,
            bg=self.card_bg,
            fg=self.primary_color
        ).pack(side="left")
        
        # Search functionality
        search_frame = tk.Frame(list_card, bg=self.card_bg)
        search_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        tk.Label(
            search_frame,
            text="🔍 Search:",
            font=self.body_font,
            bg=self.card_bg,
            fg=self.fg_color
        ).pack(side="left", padx=(0, 10))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=self.body_font
        )
        search_entry.pack(side="left", fill="x", expand=True)
        self.search_var.trace("w", self.filter_participants)
        
        # List with scrollbar
        list_frame = tk.Frame(list_card, bg=self.card_bg)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        listbox_container = tk.Frame(list_frame, bg=self.border_color, bd=1)
        listbox_container.pack(fill="both", expand=True)
        
        self.participants_listbox = tk.Listbox(
            listbox_container,
            font=self.body_font,
            bg=self.card_bg,
            fg=self.fg_color,
            selectbackground=self.primary_color,
            selectforeground="white",
            bd=0,
            highlightthickness=0
        )
        
        scrollbar = ttk.Scrollbar(listbox_container, orient="vertical")
        self.participants_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.participants_listbox.yview)
        
        self.participants_listbox.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        scrollbar.pack(side="right", fill="y")
        
        self.participants_listbox.bind("<<ListboxSelect>>", self.select_participant)
        
        # Delete button
        delete_frame = tk.Frame(list_card, bg=self.card_bg)
        delete_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.delete_button = tk.Button(
            delete_frame,
            text="🗑️ Delete Participant",
            font=("Segoe UI", 10, "bold"),
            bg=self.danger_color,
            fg="white",
            relief="flat",
            bd=0,
            padx=15,
            pady=10,
            cursor="hand2",
            command=self.delete_participant
        )
        self.delete_button.pack(fill="x")

    def create_action_panel(self, parent):
        """Create the bottom action panel for file operations"""
        action_panel = tk.Frame(parent, bg=self.secondary_bg, height=60)
        action_panel.pack(fill="x", pady=(20, 0))
        action_panel.pack_propagate(False)
        
        # File operations
        file_frame = tk.Frame(action_panel, bg=self.secondary_bg)
        file_frame.pack(side="left", padx=20, pady=15)
        
        button_style = {
            "font": ("Segoe UI", 9, "bold"),
            "relief": "flat",
            "bd": 0,
            "padx": 20,
            "pady": 8,
            "cursor": "hand2"
        }
        
        buttons = [
            ("📄 New", self.new_file, self.secondary_bg),
            ("📂 Load", self.load_json_dialog, self.info_color),
            ("💾 Save As", self.save_json_dialog, self.accent_color),
            ("📊 Export PDF", self.export_to_pdf, self.warning_color)
        ]
        
        for text, command, color in buttons:
            btn = tk.Button(
                file_frame,
                text=text,
                bg=color,
                fg="white" if color != self.warning_color else "black",
                command=command,
                **button_style
            )
            btn.pack(side="left", padx=(0, 10))
        
        # Version info
        # Version and help info
        info_frame = tk.Frame(action_panel, bg=self.secondary_bg)
        info_frame.pack(side="right", padx=20, pady=15)
        
        help_btn = tk.Button(
            info_frame,
            text="❓ Help (F1)",
            font=("Segoe UI", 9),
            bg=self.secondary_bg,
            fg=self.primary_color,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.show_help
        )
        help_btn.pack(side="right", padx=(0, 15))
        
        version_label = tk.Label(
            info_frame,
            text="TuPono Tracker v3.0 Professional | © 2024",
            font=("Segoe UI", 9),
            bg=self.secondary_bg,
            fg=self.fg_color
        )
        version_label.pack(side="right")

    def filter_participants(self, *args):
        """Filter participants list based on search term"""
        search_term = self.search_var.get().lower()
        self.participants_listbox.delete(0, tk.END)
        
        filtered_participants = []
        for p in self.sorted_participants:
            if (search_term in p.name.lower() or 
                search_term in p.iwi.lower() or 
                search_term in p.location.lower() or
                search_term in p.phase.lower()):
                filtered_participants.append(p)
                status = f"{p.name} ({p.age}, {p.gender}) - {p.phase.upper()}"
                if p.phase == "orange" and p.programs:
                    status += f" - {', '.join(p.programs)}"
                self.participants_listbox.insert(tk.END, status)
        
        self.filtered_participants = filtered_participants

    def add_participant(self):
        """Add a new participant with comprehensive validation"""
        # Get form data
        name = self.name_entry.get().strip()
        age = self.age_entry.get().strip()
        gender = self.gender_var.get()
        selected_advocacy = self.get_selected_advocacy()
        location = self.location_entry.get().strip()
        iwi = self.iwi_entry.get().strip()
        hapu = self.hapu_entry.get().strip()
        signup_date = self.date_entry.get().strip()
        kaimahi = self.kaimahi_var.get()

        # Validation with specific error messages
        validation_errors = []
        
        if not name:
            validation_errors.append("• Name is required")
        elif len(name) < 2:
            validation_errors.append("• Name must be at least 2 characters long")
        
        if not age:
            validation_errors.append("• Age is required")
        else:
            try:
                age_int = int(age)
                if age_int < 0 or age_int > 120:
                    validation_errors.append("• Age must be between 0 and 120")
            except ValueError:
                validation_errors.append("• Age must be a valid number")
        
        if not gender:
            validation_errors.append("• Gender selection is required")
        
        if not location:
            validation_errors.append("• Location is required")
        
        if not iwi:
            validation_errors.append("• Iwi affiliation is required")
        
        if not hapu:
            validation_errors.append("• Hapū affiliation is required")
        
        if not signup_date:
            validation_errors.append("• Signup date is required")
        else:
            try:
                date_obj = datetime.strptime(signup_date, "%Y-%m-%d")
                # Check if date is not too far in the future
                if date_obj.date() > datetime.now().date() + timedelta(days=30):
                    validation_errors.append("• Signup date cannot be more than 30 days in the future")
            except ValueError:
                validation_errors.append("• Invalid date format. Use YYYY-MM-DD (e.g., 2024-03-15)")
        
        if not kaimahi:
            validation_errors.append("• Kaimahi assignment is required")
        
        # Check for duplicate names (case-insensitive)
        existing_names = [p.name.lower() for p in self.participants]
        if name.lower() in existing_names:
            validation_errors.append("• A participant with this name already exists")
        
        if validation_errors:
            error_message = "Please correct the following errors:\n\n" + "\n".join(validation_errors)
            messagebox.showerror("Validation Error", error_message)
            return

        try:
            # Create and add participant
            participant = Participant(name, age, gender, location, iwi, hapu, signup_date, selected_advocacy, kaimahi)
            participant.update_progress()
            self.participants.append(participant)
            
            # Save and update UI
            self.save_data()
            self.update_participants_list()
            self.clear_inputs()
            
            # Success feedback
            self.show_notification(f"Successfully added {name} to the program", "success")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add participant:\n{str(e)}")
            print(f"Add participant error: {e}")

    def update_participant(self):
        if not self.current_participant:
            return

        name = self.name_entry.get()
        age = self.age_entry.get()
        gender = self.gender_var.get()
        selected_advocacy = self.get_selected_advocacy()
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
        self.disable_participant_buttons()

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
        self.disable_participant_buttons()

    def select_participant(self, event):
        selection = self.participants_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        
        # Use filtered participants if search is active, otherwise sorted participants
        if hasattr(self, 'filtered_participants') and self.search_var.get().strip():
            if index < len(self.filtered_participants):
                self.current_participant = self.filtered_participants[index]
        elif hasattr(self, 'sorted_participants') and index < len(self.sorted_participants):
            self.current_participant = self.sorted_participants[index]
        else:
            self.current_participant = self.participants[index]
            
        self.current_participant.update_progress()

        # Clear displays first (if they exist)
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.config(text="Status: Loading...")
        if hasattr(self, 'program_label') and self.program_label:
            self.program_label.config(text="Program(s): Loading...")
        if hasattr(self, 'progress_canvas') and self.progress_canvas:
            self.progress_canvas.delete("all")

        # Populate input fields
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.current_participant.name)
        self.age_entry.delete(0, tk.END)
        self.age_entry.insert(0, self.current_participant.age)
        self.gender_var.set(self.current_participant.gender)

        # Set advocacy selections
        self.set_selected_advocacy(self.current_participant.advocacy or [])

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

        # Enable buttons with visual feedback
        self.enable_participant_buttons()

    def enable_participant_buttons(self):
        """Enable and style participant-related buttons"""
        # Old buttons (in Participants tab)
        old_buttons = [
            (getattr(self, 'update_button', None), self.info_color),
            (getattr(self, 'select_program_button', None), self.accent_color),
            (getattr(self, 'assessment_button', None), self.warning_color),
            (getattr(self, 'review_assessment_button', None), self.info_color)
        ]
        
        # New buttons (in Progress tab)
        new_buttons = [
            (getattr(self, 'progress_set_programs_btn', None), self.accent_color),
            (getattr(self, 'progress_assessment_btn', None), self.warning_color)
        ]
        
        # Enable all existing buttons
        for button, color in old_buttons + new_buttons:
            if button is not None:
                button.config(state="normal", bg=color)

    def disable_participant_buttons(self):
        """Disable and gray out participant-related buttons"""
        # Old buttons (in Participants tab)
        old_buttons = [
            getattr(self, 'update_button', None),
            getattr(self, 'select_program_button', None),
            getattr(self, 'assessment_button', None),
            getattr(self, 'review_assessment_button', None)
        ]
        
        # New buttons (in Progress tab)
        new_buttons = [
            getattr(self, 'progress_set_programs_btn', None),
            getattr(self, 'progress_assessment_btn', None)
        ]
        
        # Disable all existing buttons
        for button in old_buttons + new_buttons:
            if button is not None:
                button.config(state="disabled", bg="#CCCCCC", fg="white")

    def set_programs(self):
        if not self.current_participant:
            messagebox.showinfo("Info", "No participant selected")
            return

        # Check if we're in progress tab or participants tab
        if hasattr(self, 'progress_program_listbox'):
            # Show program selection frame in progress tab
            if not self.program_selection_frame.winfo_viewable():
                self.program_selection_frame.pack(fill="x", pady=(10, 0))
                
                # Pre-select current programs
                self.progress_program_listbox.selection_clear(0, tk.END)
                for i in range(self.progress_program_listbox.size()):
                    if self.progress_program_listbox.get(i) in self.current_participant.programs:
                        self.progress_program_listbox.selection_set(i)
                
                # Update button text
                self.progress_set_programs_btn.config(text="💾 Save Programs", command=self.save_programs_from_progress_tab)
            else:
                self.program_selection_frame.pack_forget()
                self.progress_set_programs_btn.config(text="📚 Set Programs", command=self.set_programs)
        else:
            # Original participants tab functionality
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

    def save_programs_from_progress_tab(self):
        """Save programs selected in progress tab"""
        selected_indices = self.progress_program_listbox.curselection()
        selected_programs = [self.progress_program_listbox.get(i) for i in selected_indices]
        
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
        
        # Hide selection frame and reset button
        self.program_selection_frame.pack_forget()
        self.progress_set_programs_btn.config(text="📚 Set Programs", command=self.set_programs)
        
        messagebox.showinfo("Success", f"Programs updated: {', '.join(selected_programs)}")

    def show_assessment(self):
        if not self.current_participant or self.current_participant.phase != "red":
            messagebox.showinfo("Assessment Unavailable", 
                              "Weekly assessments are only available during the Red phase (weeks 1-6)")
            return

        week = min(self.current_participant.weeks_completed + 1, 6)
        assessment_window = tk.Toplevel(self.root)
        assessment_window.title(f"Week {week} Assessment - {self.current_participant.name}")
        assessment_window.geometry("600x500")
        assessment_window.resizable(True, True)
        assessment_window.configure(bg=self.bg_color)
        
        # Center the window
        assessment_window.transient(self.root)
        assessment_window.grab_set()
        
        # Icon and styling
        try:
            assessment_window.iconbitmap(default="")
        except:
            pass

        questions = {
            1: "How well did you create a safe space for your whaiora?",
            2: "How effectively did you allow your whaiora to express their māmae?",
            3: "How well did you prepare a pathway of purpose for your whaiora?",
            4: "How thoroughly did you identify barriers your whaiora is facing?",
            5: "How confident are you that your whaiora is ready to proceed?",
            6: "General reflection on progress and learnings this week"
        }

        assessment = self.current_participant.red_phase_assessments.get(week, {"score": 0, "notes": ""})

        # Main container with modern card design
        main_container = tk.Frame(assessment_window, bg=self.bg_color)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header card
        header_card = tk.Frame(main_container, bg=self.primary_color, height=80)
        header_card.pack(fill="x", pady=(0, 20))
        header_card.pack_propagate(False)
        
        header_content = tk.Frame(header_card, bg=self.primary_color)
        header_content.pack(fill="both", expand=True, padx=20, pady=15)
        
        tk.Label(
            header_content,
            text=f"📝 Week {week} Assessment",
            font=("Segoe UI", 16, "bold"),
            bg=self.primary_color,
            fg="white"
        ).pack(side="left")
        
        tk.Label(
            header_content,
            text=f"{self.current_participant.name}",
            font=("Segoe UI", 12),
            bg=self.primary_color,
            fg="white"
        ).pack(side="right")
        
        # Content card
        content_card = tk.Frame(main_container, bg=self.card_bg)
        content_card.pack(fill="both", expand=True)
        
        content_frame = tk.Frame(content_card, bg=self.card_bg)
        content_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Question section
        question_frame = tk.Frame(content_frame, bg=self.secondary_bg, relief="flat", bd=0)
        question_frame.pack(fill="x", pady=(0, 25))
        
        tk.Label(
            question_frame,
            text="Assessment Question:",
            font=("Segoe UI", 11, "bold"),
            bg=self.secondary_bg,
            fg=self.primary_color
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        tk.Label(
            question_frame,
            text=questions[week],
            wraplength=500,
            justify="left",
            font=("Segoe UI", 12),
            bg=self.secondary_bg,
            fg=self.fg_color
        ).pack(anchor="w", padx=20, pady=(0, 15))
        
        # Score section
        score_frame = tk.Frame(content_frame, bg=self.card_bg)
        score_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            score_frame,
            text="Score (0 = Poor, 10 = Excellent):",
            font=("Segoe UI", 11, "bold"),
            bg=self.card_bg,
            fg=self.fg_color
        ).pack(anchor="w", pady=(0, 10))
        
        # Score slider with visual feedback
        score_var = tk.IntVar(value=assessment["score"])
        
        slider_frame = tk.Frame(score_frame, bg=self.card_bg)
        slider_frame.pack(fill="x", pady=(0, 10))
        
        score_slider = ttk.Scale(
            slider_frame,
            from_=0,
            to=10,
            variable=score_var,
            orient="horizontal",
            length=400
        )
        score_slider.pack(pady=5)
        
        # Current score display
        self.current_score_label = tk.Label(
            slider_frame,
            text=f"Current Score: {assessment['score']}/10",
            font=("Segoe UI", 12, "bold"),
            bg=self.card_bg,
            fg=self.accent_color
        )
        self.current_score_label.pack(pady=(5, 0))
        
        def update_score_display(*args):
            score = int(score_var.get())
            self.current_score_label.config(text=f"Current Score: {score}/10")
            # Color coding
            if score <= 3:
                color = self.danger_color
            elif score <= 6:
                color = self.warning_color
            else:
                color = self.accent_color
            self.current_score_label.config(fg=color)
        
        score_var.trace("w", update_score_display)
        update_score_display()
        
        # Score scale indicators
        scale_frame = tk.Frame(score_frame, bg=self.card_bg)
        scale_frame.pack(fill="x", pady=5)
        
        indicators = [("0-3", "Needs Improvement", self.danger_color),
                     ("4-6", "Satisfactory", self.warning_color),
                     ("7-10", "Excellent", self.accent_color)]
        
        for score_range, description, color in indicators:
            indicator = tk.Frame(scale_frame, bg=self.card_bg)
            indicator.pack(side="left", expand=True, fill="x", padx=5)
            
            tk.Label(
                indicator,
                text=f"{score_range}: {description}",
                font=("Segoe UI", 9),
                bg=self.card_bg,
                fg=color
            ).pack()
        
        # Notes section
        notes_frame = tk.Frame(content_frame, bg=self.card_bg)
        notes_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        tk.Label(
            notes_frame,
            text="Detailed Notes and Observations:",
            font=("Segoe UI", 11, "bold"),
            bg=self.card_bg,
            fg=self.fg_color
        ).pack(anchor="w", pady=(0, 10))
        
        text_container = tk.Frame(notes_frame, bg=self.border_color, bd=1)
        text_container.pack(fill="both", expand=True)
        
        notes_text = tk.Text(
            text_container,
            height=6,
            font=("Segoe UI", 10),
            bg=self.card_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            wrap=tk.WORD,
            bd=0,
            padx=10,
            pady=10
        )
        notes_text.insert("1.0", assessment["notes"])
        
        # Add scrollbar for notes
        notes_scrollbar = ttk.Scrollbar(text_container, orient="vertical")
        notes_text.config(yscrollcommand=notes_scrollbar.set)
        notes_scrollbar.config(command=notes_text.yview)
        
        notes_text.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        notes_scrollbar.pack(side="right", fill="y")

        # Action buttons
        button_frame = tk.Frame(main_container, bg=self.bg_color)
        button_frame.pack(fill="x", pady=(20, 0))
        
        def save_assessment():
            score = int(score_var.get())
            notes = notes_text.get("1.0", tk.END).strip()
            
            # Validation
            if not notes.strip():
                if not messagebox.askyesno(
                    "Incomplete Assessment",
                    "No notes have been provided. Save assessment anyway?"
                ):
                    return
            
            self.current_participant.red_phase_assessments[week] = {
                "score": score, 
                "notes": notes,
                "date_completed": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            
            # Update in main participants list
            for i, p in enumerate(self.participants):
                if (p.name == self.current_participant.name and 
                    p.signup_date == self.current_participant.signup_date):
                    p.red_phase_assessments[week] = self.current_participant.red_phase_assessments[week]
                    break
            
            self.save_data()
            messagebox.showinfo(
                "Assessment Saved",
                f"Week {week} assessment has been successfully saved."
            )
            assessment_window.destroy()
        
        def cancel_assessment():
            if messagebox.askyesno(
                "Cancel Assessment",
                "Are you sure you want to cancel? Any unsaved changes will be lost."
            ):
                assessment_window.destroy()
        
        # Modern button styling
        button_style = {
            "font": ("Segoe UI", 11, "bold"),
            "relief": "flat",
            "bd": 0,
            "padx": 30,
            "pady": 12,
            "cursor": "hand2"
        }
        
        cancel_btn = tk.Button(
            button_frame,
            text="❌ Cancel",
            bg=self.danger_color,
            fg="white",
            command=cancel_assessment,
            **button_style
        )
        cancel_btn.pack(side="left", padx=(0, 10))
        
        save_btn = tk.Button(
            button_frame,
            text="💾 Save Assessment",
            bg=self.accent_color,
            fg="white",
            command=save_assessment,
            **button_style
        )
        save_btn.pack(side="left")
        
        # Focus on the notes text area
        assessment_window.focus_force()
        notes_text.focus_set()
        
        # Add keyboard shortcuts
        assessment_window.bind("<Control-s>", lambda e: save_assessment())
        assessment_window.bind("<Escape>", lambda e: cancel_assessment())

    def update_progress_display(self):
        if not self.current_participant:
            return

        status_text = "Status: "
        if self.current_participant.phase == "red":
            status_text += f"Red Phase (Whitiwhiti Kōrero) - Week {self.current_participant.weeks_completed + 1}/6"
        elif self.current_participant.phase == "orange":
            status_text += f"Orange Phase (Program Implementation) - Week {self.current_participant.weeks_completed + 1}/8"
        elif self.current_participant.phase == "green":
            status_text += f"Green Phase (Whānau Integration) - Week {self.current_participant.weeks_completed + 1}/12"
        elif self.current_participant.phase == "completed":
            status_text += "Program Completed 🎉"
        else:
            status_text += "Unknown Phase"

        # Add Advocacy status if applicable
        if hasattr(self.current_participant, 'advocacy') and self.current_participant.advocacy and len(self.current_participant.advocacy) > 0:
            weeks = getattr(self.current_participant, 'advocacy_weeks_completed', 0)
            advocacy_names = ", ".join(self.current_participant.advocacy)
            if weeks < 52:
                months = int(weeks / 4.3)
                status_text += f" | Advocacy: {advocacy_names} ({months} months)"
            else:
                years = int(weeks / 52)
                remaining_months = int((weeks % 52) / 4.3)
                if remaining_months > 0:
                    status_text += f" | Advocacy: {advocacy_names} ({years}y {remaining_months}m)"
                else:
                    status_text += f" | Advocacy: {advocacy_names} ({years} years)"

        program_text = f"Programs: {', '.join(self.current_participant.programs)}" if self.current_participant.programs else "Programs: None assigned"

        # Update both regular display (Participants tab) and progress tab display
        if hasattr(self, 'status_label'):
            self.status_label.config(text=status_text)
        if hasattr(self, 'program_label'):
            self.program_label.config(text=program_text)
        if hasattr(self, 'progress_status_label'):
            self.progress_status_label.config(text=status_text)
        if hasattr(self, 'progress_program_label'):
            self.progress_program_label.config(text=program_text)
            
        # Update progress bars
        self.draw_progress_bar()
        self.draw_enhanced_progress_bar()
        
        # Enable/disable progress tab buttons
        if hasattr(self, 'progress_set_programs_btn'):
            self.progress_set_programs_btn.config(state="normal", bg=self.accent_color)
        if hasattr(self, 'progress_assessment_btn'):
            if self.current_participant.phase == "red":
                self.progress_assessment_btn.config(state="normal", bg=self.warning_color)
            else:
                self.progress_assessment_btn.config(state="disabled", bg="#CCCCCC", fg="white")
        if hasattr(self, 'progress_review_btn'):
            self.progress_review_btn.config(state="normal", bg=self.info_color)

    def draw_progress_bar(self):
        # Legacy method - no longer needed with tabbed interface
        # The enhanced progress display is used instead
        return

        total_weeks = 26
        canvas_width = self.progress_canvas.winfo_width() or 520
        cell_width = (canvas_width - 40) / total_weeks  # Leave margins
        bar_height = 30
        gap = 8
        margin = 20
        today = datetime.now().date()
        current_week = (today - self.current_participant.signup_date).days // 7

        # Modern color scheme
        MODERN_COLORS = {
            "red": {"fill": "#FF4757", "outline": "#FF3838", "text": "white"},
            "orange": {"fill": "#FFA502", "outline": "#FF8C00", "text": "black"},
            "green": {"fill": "#2ED573", "outline": "#2BC152", "text": "white"}
        }

        # Draw title
        self.progress_canvas.create_text(
            canvas_width / 2, 15,
            text="26-Week Program Progress",
            font=("Segoe UI", 11, "bold"),
            fill=self.fg_color
        )

        # Draw Standard 26-Week Bar
        y_offset_top = 35
        for week in range(total_weeks):
            x1 = margin + week * cell_width
            x2 = x1 + cell_width - 1
            y1 = y_offset_top
            y2 = y1 + bar_height

            color_key = self.current_participant.weekly_progress[week] if week < len(self.current_participant.weekly_progress) else ""
            is_current = week == current_week
            
            if color_key in MODERN_COLORS:
                colors = MODERN_COLORS[color_key]
                fill = colors["fill"]
                outline = colors["outline"]
                text_color = colors["text"]
            else:
                fill = "#E0E0E0"
                outline = "#BDBDBD"
                text_color = "#757575"

            # Add glow effect for current week
            if is_current:
                # Glow effect
                self.progress_canvas.create_rectangle(
                    x1 - 2, y1 - 2, x2 + 2, y2 + 2,
                    fill="", outline=self.primary_color, width=3
                )

            # Main rectangle with rounded corners effect
            self.progress_canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=fill, outline=outline, width=2 if is_current else 1
            )
            
            # Add subtle gradient effect
            self.progress_canvas.create_line(
                x1 + 1, y1 + 1, x2 - 1, y1 + 1,
                fill="white", width=1
            )

            # Week labels every 2 weeks for better readability
            if (week + 1) % 2 == 0 or week == 0 or week == total_weeks - 1:
                self.progress_canvas.create_text(
                    x1 + cell_width / 2,
                    y1 + bar_height / 2,
                    text=str(week + 1),
                    font=("Segoe UI", 8, "bold"),
                    fill=text_color
                )

        # Phase labels
        phase_y = y_offset_top + bar_height + 15
        phase_positions = [
            (margin + 3 * cell_width, "RED\nPhase", "#FF6B6B"),
            (margin + 10 * cell_width, "ORANGE\nPhase", "#FFB74D"),
            (margin + 20 * cell_width, "GREEN\nPhase", "#66BB6A")
        ]
        
        for x_pos, label, color in phase_positions:
            self.progress_canvas.create_text(
                x_pos, phase_y,
                text=label,
                font=("Segoe UI", 9, "bold"),
                fill=color,
                justify="center"
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
        print(f"Updating participants list with {len(self.participants)} participants")
        
        # Store sorted list for correct selection mapping
        self.sorted_participants = sorted(self.participants, key=lambda x: x.signup_date)
        self.filtered_participants = self.sorted_participants.copy()
        print(f"Sorted participants: {[p.name for p in self.sorted_participants]}")
        
        # Update header count
        if hasattr(self, 'header_status'):
            self.header_status.config(text=f"Participants: {len(self.participants)}")
        
        # Clear search and repopulate
        if hasattr(self, 'search_var'):
            self.search_var.set("")
            
        if hasattr(self, 'participants_listbox'):
            self.participants_listbox.delete(0, tk.END)
            
            for p in self.sorted_participants:
                status = f"{p.name} ({p.age}, {p.gender}) - {p.phase.upper()}"
                if p.phase == "orange" and p.programs:
                    status += f" - {', '.join(p.programs)}"
                self.participants_listbox.insert(tk.END, status)
                print(f"Added to list: {status}")
                
            print(f"Final listbox size: {self.participants_listbox.size()}")
            
            # Also update progress tab dropdown if it exists
            self.update_progress_participant_dropdown()
        else:
            print("participants_listbox not yet created")

    def clear_inputs(self):
        """Clear all input fields and reset form"""
        self.name_entry.delete(0, tk.END)
        self.age_entry.delete(0, tk.END)
        self.gender_var.set("")
        self.kaimahi_var.set("")
        self.set_selected_advocacy([])
        self.location_entry.delete(0, tk.END)
        self.iwi_entry.delete(0, tk.END)
        self.hapu_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.disable_participant_buttons()

    def load_data(self):
        try:
            print(f"Attempting to load data from: {JSON_PATH}")
            print(f"File exists: {os.path.exists(JSON_PATH)}")
            
            if os.path.exists(JSON_PATH):
                with open(JSON_PATH, "r") as f:
                    data = json.load(f)
                print(f"Raw data loaded, found {len(data)} items")
                
                self.participants = []
                for i, item in enumerate(data):
                    try:
                        participant = Participant.from_dict(item)
                        self.participants.append(participant)
                    except Exception as e:
                        print(f"Error loading participant {i}: {e}")
                        
                print(f"Successfully loaded {len(self.participants)} participants")
                
                # Make sure to update the list after loading
                if hasattr(self, 'participants_listbox'):
                    self.update_participants_list()
                    
            else:
                print("JSON file does not exist, starting with empty list")
                self.participants = []
        except Exception as e:
            print(f"Error loading data: {e}")
            import traceback
            traceback.print_exc()
            self.participants = []

    def save_data(self):
        """Save participant data with error handling"""
        try:
            data = [p.to_dict() for p in self.participants]
            with open("participants.json", "w") as f:
                json.dump(data, f, indent=2)
            self.show_notification("Data saved successfully", "success")
        except Exception as e:
            self.show_notification(f"Failed to save data: {str(e)}", "error")
            print(f"Save error: {e}")

    def show_notification(self, message, type="info"):
        """Show a temporary notification to the user"""
        # Create notification frame fresh each time
        notification_frame = tk.Frame(self.root)
        notification_frame.place(x=20, y=20)
        
        # Color scheme based on type
        colors = {
            "success": {"bg": "#28A745", "fg": "white"},
            "error": {"bg": "#DC3545", "fg": "white"},
            "warning": {"bg": "#FFC107", "fg": "black"},
            "info": {"bg": "#17A2B8", "fg": "white"}
        }
        
        color = colors.get(type, colors["info"])
        
        notification = tk.Label(
            notification_frame,
            text=f"ℹ️ {message}",
            font=("Segoe UI", 10),
            bg=color["bg"],
            fg=color["fg"],
            padx=15,
            pady=8,
            relief="solid",
            bd=1
        )
        notification.pack()
        
        # Auto-hide after 3 seconds - destroy the entire frame
        def hide_notification():
            if notification_frame.winfo_exists():
                notification_frame.destroy()
        
        self.root.after(3000, hide_notification)

    def review_assessments(self):
        if not self.current_participant:
            messagebox.showinfo("Selection Required", "Please select a participant to review assessments")
            return

        review_window = tk.Toplevel(self.root)
        review_window.title(f"Assessment Review - {self.current_participant.name}")
        review_window.geometry("800x700")
        review_window.configure(bg=self.bg_color)
        review_window.transient(self.root)
        
        # Main container
        main_container = tk.Frame(review_window, bg=self.bg_color)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_card = tk.Frame(main_container, bg=self.primary_color, height=80)
        header_card.pack(fill="x", pady=(0, 20))
        header_card.pack_propagate(False)
        
        header_content = tk.Frame(header_card, bg=self.primary_color)
        header_content.pack(fill="both", expand=True, padx=25, pady=15)
        
        tk.Label(
            header_content,
            text="📊 Weekly Assessment Review",
            font=("Segoe UI", 18, "bold"),
            bg=self.primary_color,
            fg="white"
        ).pack(side="left")
        
        tk.Label(
            header_content,
            text=f"Participant: {self.current_participant.name}",
            font=("Segoe UI", 12),
            bg=self.primary_color,
            fg="white"
        ).pack(side="right")
        
        # Content area with scrolling
        content_container = tk.Frame(main_container, bg=self.card_bg)
        content_container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(content_container, bg=self.card_bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.card_bg)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Summary card
        summary_card = tk.Frame(scrollable_frame, bg=self.secondary_bg, relief="flat", bd=0)
        summary_card.pack(fill="x", padx=20, pady=(20, 15))
        
        summary_content = tk.Frame(summary_card, bg=self.secondary_bg)
        summary_content.pack(fill="x", padx=20, pady=15)
        
        tk.Label(
            summary_content,
            text="📈 Assessment Summary",
            font=("Segoe UI", 14, "bold"),
            bg=self.secondary_bg,
            fg=self.primary_color
        ).pack(anchor="w", pady=(0, 10))
        
        # Calculate summary statistics
        completed_assessments = sum(1 for week in range(1, 7) 
                                  if self.current_participant.red_phase_assessments[week]["score"] > 0)
        avg_score = sum(self.current_participant.red_phase_assessments[week]["score"] 
                       for week in range(1, 7)) / 6
        
        summary_stats = tk.Frame(summary_content, bg=self.secondary_bg)
        summary_stats.pack(fill="x")
        
        stats = [
            ("Completed Assessments:", f"{completed_assessments}/6"),
            ("Average Score:", f"{avg_score:.1f}/10"),
            ("Current Phase:", self.current_participant.phase.upper())
        ]
        
        for i, (label, value) in enumerate(stats):
            stat_frame = tk.Frame(summary_stats, bg=self.secondary_bg)
            stat_frame.pack(side="left", expand=True, fill="x")
            
            tk.Label(
                stat_frame,
                text=label,
                font=("Segoe UI", 10),
                bg=self.secondary_bg,
                fg=self.fg_color
            ).pack()
            
            tk.Label(
                stat_frame,
                text=value,
                font=("Segoe UI", 12, "bold"),
                bg=self.secondary_bg,
                fg=self.accent_color
            ).pack()

        questions = {
            1: "How well did you create a safe space for your whaiora?",
            2: "How effectively did you allow your whaiora to express their māmae?",
            3: "How well did you prepare a pathway of purpose for your whaiora?",
            4: "How thoroughly did you identify barriers your whaiora is facing?",
            5: "How confident are you that your whaiora is ready to proceed?",
            6: "General reflection on progress and learnings this week"
        }

        # Assessment cards
        for week_num in range(1, 7):
            assessment = self.current_participant.red_phase_assessments[week_num]
            score = assessment["score"]
            notes = assessment["notes"]
            completed_date = assessment.get("date_completed", "Not completed")

            # Individual assessment card
            card = tk.Frame(scrollable_frame, bg=self.card_bg, relief="solid", bd=1)
            card.pack(fill="x", padx=20, pady=10)

            # Card header
            header = tk.Frame(card, bg=self.primary_color, height=50)
            header.pack(fill="x")
            header.pack_propagate(False)
            
            header_content = tk.Frame(header, bg=self.primary_color)
            header_content.pack(fill="both", expand=True, padx=15, pady=10)
            
            tk.Label(
                header_content,
                text=f"📅 Week {week_num}",
                font=("Segoe UI", 13, "bold"),
                bg=self.primary_color,
                fg="white"
            ).pack(side="left")
            
            # Score badge
            if score > 0:
                score_color = (self.accent_color if score >= 7 else 
                             self.warning_color if score >= 4 else self.danger_color)
                score_text_color = "black" if score >= 4 and score < 7 else "white"
            else:
                score_color = "#CCCCCC"
                score_text_color = "black"
            
            score_badge = tk.Label(
                header_content,
                text=f"{score}/10" if score > 0 else "Not Assessed",
                font=("Segoe UI", 11, "bold"),
                bg=score_color,
                fg=score_text_color,
                padx=10,
                pady=2
            )
            score_badge.pack(side="right")

            # Card body
            body = tk.Frame(card, bg=self.card_bg)
            body.pack(fill="both", expand=True, padx=20, pady=15)
            
            # Question
            question_frame = tk.Frame(body, bg=self.secondary_bg)
            question_frame.pack(fill="x", pady=(0, 10))
            
            tk.Label(
                question_frame,
                text="Assessment Question:",
                font=("Segoe UI", 9, "bold"),
                bg=self.secondary_bg,
                fg=self.primary_color
            ).pack(anchor="w", padx=10, pady=(8, 2))
            
            tk.Label(
                question_frame,
                text=questions[week_num],
                wraplength=650,
                justify="left",
                font=("Segoe UI", 10),
                bg=self.secondary_bg,
                fg=self.fg_color
            ).pack(anchor="w", padx=10, pady=(0, 8))

            # Notes section
            if notes.strip():
                notes_frame = tk.Frame(body, bg=self.card_bg)
                notes_frame.pack(fill="x", pady=(5, 0))
                
                tk.Label(
                    notes_frame,
                    text="📝 Notes:",
                    font=("Segoe UI", 10, "bold"),
                    bg=self.card_bg,
                    fg=self.fg_color
                ).pack(anchor="w", pady=(0, 5))
                
                notes_display = tk.Text(
                    notes_frame,
                    height=3,
                    wrap=tk.WORD,
                    font=("Segoe UI", 9),
                    bg=self.secondary_bg,
                    fg=self.fg_color,
                    bd=0,
                    padx=10,
                    pady=8,
                    state=tk.DISABLED
                )
                notes_display.pack(fill="x")
                
                notes_display.config(state=tk.NORMAL)
                notes_display.insert("1.0", notes)
                notes_display.config(state=tk.DISABLED)
            else:
                tk.Label(
                    body,
                    text="📝 No notes provided for this assessment",
                    font=("Segoe UI", 9, "italic"),
                    bg=self.card_bg,
                    fg="white"
                ).pack(anchor="w", pady=(5, 0))
            
            # Completion date
            if completed_date != "Not completed":
                tk.Label(
                    body,
                    text=f"Completed: {completed_date}",
                    font=("Segoe UI", 8),
                    bg=self.card_bg,
                    fg="white"
                ).pack(anchor="e", pady=(10, 0))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Close button
        close_frame = tk.Frame(main_container, bg=self.bg_color)
        close_frame.pack(fill="x", pady=(15, 0))
        
        close_btn = tk.Button(
            close_frame,
            text="✅ Close Review",
            font=("Segoe UI", 11, "bold"),
            bg=self.primary_color,
            fg="white",
            relief="flat",
            bd=0,
            padx=25,
            pady=10,
            cursor="hand2",
            command=review_window.destroy
        )
        close_btn.pack(side="right")
        
        # Add keyboard shortcut
        review_window.bind("<Escape>", lambda e: review_window.destroy())
        review_window.focus_force()

    def apply_theme(self):
        """Apply modern theme with professional styling"""
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass

        # Configure ttk styles for modern look with explicit colors
        style.configure("TLabel", 
                       background="#FAFFFE", 
                       foreground="#000000", 
                       font=self.body_font)
        
        style.configure("TEntry", 
                       fieldbackground="#FFFFFF",
                       background="#FFFFFF",
                       foreground="#000000",
                       insertcolor="#000000",
                       borderwidth=1,
                       relief="solid")
        
        style.configure("TCombobox",
                       fieldbackground="#FFFFFF",
                       background="#FFFFFF",
                       foreground="#000000",
                       selectbackground="#2E8B57",
                       selectforeground="#FFFFFF",
                       borderwidth=1,
                       relief="solid")
        
        style.map("TCombobox",
                  fieldbackground=[('readonly', self.card_bg)],
                  selectbackground=[('readonly', self.primary_color)])
        
        # Configure root window
        self.root.configure(bg=self.bg_color)
        
        # Add hover effects to custom buttons
        self.setup_button_hover_effects()
        
        self.draw_progress_bar()
        self.root.update_idletasks()

    def setup_button_hover_effects(self):
        """Add hover effects to custom buttons"""
        def create_hover_effect(button, hover_color, original_color):
            def on_enter(e):
                button.configure(bg=hover_color)
            def on_leave(e):
                button.configure(bg=original_color)
            button.bind("<Enter>", on_enter)
            button.bind("<Leave>", on_leave)
        
        # Apply hover effects to buttons that exist
        potential_buttons = [
            (getattr(self, 'add_button', None), "#2BC152", self.accent_color),
            (getattr(self, 'update_button', None), "#2F2ED3", self.info_color),
            (getattr(self, 'delete_button', None), "#FF3838", self.danger_color),
            (getattr(self, 'select_program_button', None), "#2BC152", self.accent_color),
            (getattr(self, 'assessment_button', None), "#FF8C00", self.warning_color),
            (getattr(self, 'review_assessment_button', None), "#2F2ED3", self.info_color),
            (getattr(self, 'stats_button', None), "#228B22", self.primary_color),
            (getattr(self, 'progress_set_programs_btn', None), "#2BC152", self.accent_color),
            (getattr(self, 'progress_assessment_btn', None), "#FF8C00", self.warning_color)
        ]
        
        buttons_with_hover = [(btn, hover, orig) for btn, hover, orig in potential_buttons if btn is not None]
        
        for button, hover_color, original_color in buttons_with_hover:
            if hasattr(self, button.winfo_name()) or button.winfo_exists():
                create_hover_effect(button, hover_color, original_color)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    # Clean branded splash screen with box
    splash = tk.Toplevel()
    splash.overrideredirect(True)
    splash.attributes('-topmost', True)
    
    # Professional styling
    splash.configure(bg='#F0F8FF')  # Alice Blue background
    
    # Window size and positioning
    splash_width, splash_height = 400, 500
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x_pos = screen_w // 2 - splash_width // 2
    y_pos = screen_h // 2 - splash_height // 2
    
    splash.geometry(f"{splash_width}x{splash_height}+{x_pos}+{y_pos}")
    splash.resizable(False, False)
    
    # Main container frame with border
    main_frame = tk.Frame(splash, bg='white', relief='raised', bd=3)
    main_frame.pack(fill='both', expand=True, padx=20, pady=20)
    
    # Tu Pono branding header
    title_label = tk.Label(main_frame, text="TU PONO", 
                          font=('Arial', 28, 'bold'),
                          bg='white', fg='#2E8B57',  # Sea Green
                          pady=15)
    title_label.pack()
    
    # Subtitle
    subtitle_label = tk.Label(main_frame, text="Tracker Application", 
                             font=('Arial', 14),
                             bg='white', fg='#555555')
    subtitle_label.pack(pady=(0, 20))
    
    # Load and display logo in the box
    try:
        from PIL import Image, ImageTk
        import sys
        
        # Handle both development and executable environments
        if getattr(sys, 'frozen', False):
            # Running as executable - logo is embedded
            logo_path = os.path.join(sys._MEIPASS, "Tu_pono_logo.png")
        else:
            # Running as script - use local file
            logo_path = r"c:\Day trading indicator bot\Tu_pono_logo.png"
            
        if os.path.exists(logo_path):
            # Load and resize logo for splash
            pil_image = Image.open(logo_path)
            pil_image = pil_image.resize((250, 250), Image.Resampling.LANCZOS)
            
            photo_image = ImageTk.PhotoImage(pil_image)

            # Display logo in the center
            image_label = tk.Label(
                main_frame,
                image=photo_image,
                bg='white',
                bd=0,
                highlightthickness=0
            )
            image_label.pack(pady=10)
            splash.image = photo_image  # Keep reference
        else:
            # Fallback if logo not found
            fallback_label = tk.Label(main_frame, text="🏢", 
                                    font=('Arial', 80),
                                    bg='white', fg='#2E8B57')
            fallback_label.pack(pady=30)
    
    except Exception as e:
        # Error fallback
        error_label = tk.Label(main_frame, text="TU PONO\nTRACKER", 
                              font=('Arial', 20, 'bold'),
                              bg='white', fg='#2E8B57',
                              justify='center')
        error_label.pack(pady=30)
    
    # Loading message
    loading_label = tk.Label(main_frame, text="Loading...", 
                            font=('Arial', 12),
                            bg='white', fg='#666666')
    loading_label.pack(side='bottom', pady=20)
    
    # Simple fade-in animation for the whole splash
    def animate_splash():
        import math, time
        start_time = time.time()
        
        def fade_step():
            if splash.winfo_exists():
                elapsed = time.time() - start_time
                if elapsed < 1.0:  # 1 second fade-in
                    alpha = min(0.95, elapsed)
                    splash.attributes('-alpha', alpha)
                    splash.after(50, fade_step)
                else:
                    splash.attributes('-alpha', 0.95)
        
        fade_step()
    
    # Start fade-in animation
    animate_splash()
    
    # Define password prompt function first
    def show_password_prompt():
        try:
            splash.destroy()
        except:
            pass  # Splash might already be destroyed
        
        # Custom password dialog
        password_window = tk.Toplevel(root)
        password_window.title("TuPono IP - Authentication")
        password_window.geometry("400x250")
        password_window.configure(bg="#1A3A2A")
        password_window.resizable(False, False)
        
        # Make sure it appears on top and gets focus
        password_window.lift()
        password_window.attributes('-topmost', True)
        password_window.focus_force()
        password_window.after_idle(password_window.attributes, '-topmost', False)
        
        # Center the window
        password_window.update_idletasks()
        x = (password_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (password_window.winfo_screenheight() // 2) - (250 // 2)
        password_window.geometry(f"400x250+{x}+{y}")
        
        main_frame = tk.Frame(password_window, bg="#1A3A2A")
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Header
        tk.Label(
            main_frame,
            text="🔐 Authentication Required",
            font=("Segoe UI", 16, "bold"),
            bg="#1A3A2A",
            fg="white"
        ).pack(pady=(0, 20))
        
        tk.Label(
            main_frame,
            text="Enter password to access TuPono Tracker:",
            font=("Segoe UI", 11),
            bg="#1A3A2A",
            fg="white"
        ).pack(pady=(0, 15))
        
        # Password entry
        password_var = tk.StringVar()
        password_entry = tk.Entry(
            main_frame,
            textvariable=password_var,
            show="*",
            font=("Segoe UI", 12),
            bg="white",
            fg="black",
            relief="flat",
            bd=5,
            width=25
        )
        password_entry.pack(pady=(0, 20))
        
        # Ensure the entry gets focus
        password_window.after(100, lambda: password_entry.focus_force())
        
        # Error label (initially hidden)
        error_label = tk.Label(
            main_frame,
            text="",
            font=("Segoe UI", 10),
            bg="#1A3A2A",
            fg="#FF6B6B"
        )
        error_label.pack()
        
        def validate_password():
            password = password_var.get()
            if password == "ElwynPakeha":
                password_window.destroy()
                root.deiconify()
                try:
                    app = ProgramTrackerApp(root)
                    # Don't call mainloop here as it's already running
                except Exception as e:
                    messagebox.showerror(
                        "Application Error", 
                        f"Failed to start application:\n{str(e)}"
                    )
                    root.destroy()
            else:
                error_label.config(text="❌ Incorrect password. Please try again.")
                password_entry.delete(0, tk.END)
                password_entry.focus_set()
                # Shake effect
                for i in range(5):
                    password_window.after(i*50, lambda i=i: password_window.geometry(f"400x250+{x+(-5 if i%2 else 5)}+{y}"))
                password_window.after(250, lambda: password_window.geometry(f"400x250+{x}+{y}"))
        
        def cancel_login():
            password_window.destroy()
            root.destroy()
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg="#1A3A2A")
        button_frame.pack(side="bottom", pady=(20, 0))
        
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            font=("Segoe UI", 10, "bold"),
            bg="#DC3545",
            fg="white",
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=cancel_login
        )
        cancel_btn.pack(side="left", padx=(0, 10))
        
        login_btn = tk.Button(
            button_frame,
            text="Login",
            font=("Segoe UI", 10, "bold"),
            bg="#28A745",
            fg="white",
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=validate_password
        )
        login_btn.pack(side="left")
        
        # Bind Enter key and flash window to get attention
        password_entry.bind("<Return>", lambda e: validate_password())
        password_window.bind("<Escape>", lambda e: cancel_login())
        
        # Flash the window to get user's attention
        def flash_window(count=0):
            if count < 3:
                password_window.attributes('-topmost', True)
                password_window.after(200, lambda: password_window.attributes('-topmost', False))
                password_window.after(400, lambda: flash_window(count + 1))
        
        password_window.after(200, flash_window)


    
    # Schedule the password prompt after splash screen
    splash.after(2500, show_password_prompt)
    root.mainloop()