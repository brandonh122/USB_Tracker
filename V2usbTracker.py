import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import os
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import threading   

class USBTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("USB Inventory Tracker")
        
        self.usb_listbox = tk.Listbox(root, width=100, selectmode=tk.MULTIPLE)
        self.usb_listbox.pack(pady=20, fill="both", expand=True)
        
        self.check_in_button = tk.Button(root, text="Check In", command=self.check_in_usb)
        self.check_in_button.pack(side=tk.TOP, fill="both", expand=True, padx=250, pady=10)
        
        self.check_out_button = tk.Button(root, text="Check Out", command=self.check_out_usb)
        self.check_out_button.pack(side=tk.TOP, fill="both", expand=True, padx=250, pady=10)
        
        self.add_usb_button = tk.Button(root, text="Add USB", command=self.add_usb)
        self.add_usb_button.pack(side=tk.TOP, fill="both", expand=True, padx=250, pady=10)
        
        self.png_image = tk.PhotoImage(file="<logo>")
        self.image_label = tk.Label(root, image=self.png_image)
        self.image_label.pack(side=tk.BOTTOM, fill="both", expand=True, padx =10)
        
        self.status_label = tk.Label(root, text="")
        self.status_label.pack(fill="both", expand=True, pady=10)
        
        self.load_usb_list()
        self.initialize_database()

        self.setup_email_schedule()
        threading.Thread(target=self.run_schedule, daemon=True).start()

    #creates and adds users and pins to the database.    
    def initialize_database(self):
        self.conn = sqlite3.connect('usb_tracker.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                pin TEXT NOT NULL
            )
        ''')
        self.conn.commit()
        
        # Insert users with PINs if they do not exist
        #users = [("User1", "1234"), ("User2", "4321"), ("User3", "5941")]
        users= []
        for user in users:
            self.cursor.execute('SELECT * FROM users WHERE name = ?', (user[0],))
            if not self.cursor.fetchone():
                self.cursor.execute('INSERT INTO users (name, pin) VALUES (?, ?)', user)
        self.conn.commit()
    #Creates and loads the list of usbs    
    def load_usb_list(self):
        self.usb_listbox.delete(0, tk.END)
        if not os.path.exists("usb_inventory.txt"):
            with open("usb_inventory.txt", "w") as f:
                pass
        
        with open("usb_inventory.txt", "r") as f:
            for line in f:
                item = line.strip()
                self.usb_listbox.insert(tk.END, item)
                if "(Available)" in item:
                    self.usb_listbox.itemconfig(tk.END, {'bg': 'green'})
                elif "(Checked Out)" in item:
                    self.usb_listbox.itemconfig(tk.END, {'bg': 'red'})
        
        self.status_label.config(text=f"Total USB Drives: {self.usb_listbox.size()}")
    #function to check in usb  
    def check_in_usb(self):
        selected = self.usb_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "No USB drive selected")
            return
        
        self.pin_window = tk.Toplevel(self.root)
        self.pin_window.title("Enter PIN")
        
        tk.Label(self.pin_window, text="Enter 4-digit PIN:").pack(pady=10)
        self.pin_entry = tk.Entry(self.pin_window, show="*")
        self.pin_entry.focus()
        self.pin_entry.pack(pady=10)
        tk.Button(self.pin_window, text="Submit", command=lambda: self.verify_pin("check_in", selected)).pack(pady=10)
    #function for checking out usb    
    def check_out_usb(self):
        selected = self.usb_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "No USB drive selected")
            return
        
        self.check_out_window = tk.Toplevel(self.root)
        self.check_out_window.title("Check Out USB")

        tk.Label(self.check_out_window, text="Select person checking out the USB:").pack(pady=10)

        self.person_combobox = ttk.Combobox(self.check_out_window, values=["Bob", "Peter", "Andrew", "Phoebe"])
        self.person_combobox.pack(pady=10)

        tk.Button(self.check_out_window, text="Proceed", command=lambda: self.verify_person(selected)).pack(pady=10)
    #Function to ensure a name is selected when checking out    
    def verify_person(self, selected):
        person = self.person_combobox.get()
        if person:
            self.person = person
            self.check_out_window.destroy()
            self.pin_window = tk.Toplevel(self.root)
            self.pin_window.title("Enter PIN")
            
            tk.Label(self.pin_window, text="Enter 4-digit PIN:").pack(pady=10)
            self.pin_entry = tk.Entry(self.pin_window, show="*")
            self.pin_entry.focus()
            self.pin_entry.pack(pady=10)
            tk.Button(self.pin_window, text="Submit", command=lambda: self.verify_pin("check_out", selected)).pack(pady=10)
        else:
            messagebox.showwarning("Warning", "Please select a person")
    #Function to verify the pin matches the selected user    
    def verify_pin(self, action, selected):
        pin = self.pin_entry.get()
        if action == "check_out":
            self.cursor.execute('SELECT * FROM users WHERE name = ? AND pin = ?', (self.person, pin))
            if self.cursor.fetchone():
                self.finalize_check_out(selected)
                self.pin_window.destroy()
                
            else:
                messagebox.showerror("Error", "Invalid PIN")
        elif action == "check_in":
            self.cursor.execute('SELECT * FROM users WHERE pin = ?', (pin,))
            if self.cursor.fetchone():
                self.finalize_check_in(selected)
                self.pin_window.destroy()
            else:
                messagebox.showerror("Error", "Invalid PIN")
    #Function to ensure the action checkin can be performed on the selected usb    
    def finalize_check_in(self, selected):
        for index in selected:
            item = self.usb_listbox.get(index)
            if "(Available)" in item:
                messagebox.showinfo("Info", "Some USB drives are already available")
                return
            
            if "(Checked Out)" in item:
                base_item = item.split(" (Checked Out)")[0]
                new_item = base_item + " (Available)"
                self.usb_listbox.delete(index)
                self.usb_listbox.insert(index, new_item)
                self.usb_listbox.itemconfig(index, {'bg': 'green'})
        
        self.update_usb_inventory()
    #function to ensure the action of checkout can be performed on the slected usb    
    def finalize_check_out(self, selected):
        check_out_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for index in selected:
            item = self.usb_listbox.get(index)
            base_item = item.split(" (Available)")[0]
            new_item = base_item + f" (Checked Out) - Checked Out By: {self.person} on {check_out_time}"
            self.usb_listbox.delete(index)
            self.usb_listbox.insert(index, new_item)
            self.usb_listbox.itemconfig(index, {'bg': 'red'})
        self.update_usb_inventory()
    #function for adding a new USB    
    def add_usb(self):
        new_usb = simpledialog.askstring("Add USB", "Enter USB drive name:")
        if new_usb:
            new_item = f"{new_usb} (Available)"
            self.usb_listbox.insert(tk.END, new_item)
            self.usb_listbox.itemconfig(tk.END, {'bg': 'green'})
            self.update_usb_inventory()
    #function to update inventory if a USB has been added
    def update_usb_inventory(self):
        with open("usb_inventory.txt", "w") as f:
            for i in range(self.usb_listbox.size()):
                f.write(self.usb_listbox.get(i) + "\n")
        self.status_label.config(text=f"Total USB Drives: {self.usb_listbox.size()}")
    #Time scheduled to send email
    def setup_email_schedule(self):
        schedule.every().day.at("17:30").do(self.check_and_send_email)
    #Checks to see if a USB is checked out still prior to creating email 
    def check_and_send_email(self):
        checked_out_usb = []
        for i in range(self.usb_listbox.size()):
            item = self.usb_listbox.get(i)
            if "(Checked Out)" in item:
                checked_out_usb.append(item)
        
        if checked_out_usb:
            self.send_email(checked_out_usb)
    #Creates email if previous checks have been meet
    def send_email(self, checked_out_usb):
        sender_email = "youremail@example.com"
        app_pass= "app Password"
        receiver_email = "receiver@example.com"
        subject = "Daily USB Check-out Report"
        
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        
        body = "The following USB drives are still checked out:\n\n"
        body += "\n".join(checked_out_usb)
        message.attach(MIMEText(body, "plain"))
        
        try:
            with smtplib.SMTP("smtp.example.com", 587) as server:
                server.starttls()
                server.login(sender_email, app_pass)
                server.sendmail(sender_email, receiver_email, message.as_string())
                print("Email sent successfully")
        except Exception as e:
            print(f"Failed to send email: {e}")
    #Runs the schedule task        
    def run_schedule(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = USBTrackerApp(root)
    root.mainloop()
   
