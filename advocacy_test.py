import tkinter as tk
from tkinter import ttk

ADVOCACY_TYPES = ["Family harm", "Sexual harm", "Mental health", "Oranga Tamariki", "MSD", "Housing"]

class SimpleAdvocacyTest:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Advocacy Test")
        self.root.geometry("400x300")
        
        # Colors
        self.card_bg = "#FFFFFF"
        self.secondary_bg = "#E9ECEF"
        self.accent_color = "#28A745"
        self.fg_color = "#212529"
        
        self.advocacy_vars = {}
        self.advocacy_buttons = {}
        
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg=self.card_bg, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        tk.Label(main_frame, text="Test Advocacy Selection", font=("Arial", 14, "bold")).pack(pady=(0, 20))
        
        # Create buttons for each advocacy type
        for advocacy_type in ADVOCACY_TYPES:
            var = tk.BooleanVar()
            self.advocacy_vars[advocacy_type] = var
            
            btn = tk.Button(
                main_frame,
                text=f"○ {advocacy_type}",
                font=("Arial", 10),
                bg="#F0F0F0",
                command=lambda at=advocacy_type: self.toggle_selection(at),
                relief="raised",
                bd=2,
                padx=10,
                pady=5
            )
            btn.pack(fill="x", pady=2)
            self.advocacy_buttons[advocacy_type] = btn
            
        # Show selections button
        tk.Button(
            main_frame,
            text="Show Selected",
            command=self.show_selected,
            bg="#007BFF",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=8
        ).pack(pady=(20, 0))
        
    def toggle_selection(self, advocacy_type):
        print(f"Clicked: {advocacy_type}")
        current = self.advocacy_vars[advocacy_type].get()
        new_value = not current
        self.advocacy_vars[advocacy_type].set(new_value)
        
        # Update button appearance
        btn = self.advocacy_buttons[advocacy_type]
        if new_value:
            btn.configure(text=f"✅ {advocacy_type}", bg="#28A745", fg="white")
        else:
            btn.configure(text=f"○ {advocacy_type}", bg="#F0F0F0", fg="black")
        
        print(f"Set {advocacy_type} to {new_value}")
        
    def show_selected(self):
        selected = [a for a, v in self.advocacy_vars.items() if v.get()]
        print(f"Selected: {selected}")
        if selected:
            tk.messagebox.showinfo("Selected", f"Selected: {', '.join(selected)}")
        else:
            tk.messagebox.showinfo("Selected", "No advocacy types selected")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    import tkinter.messagebox
    app = SimpleAdvocacyTest()
    app.run()