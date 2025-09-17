import sqlite3
import tkinter as tk
from tkinter import messagebox

def add_user(table, username, password, gender=None):
    conn = sqlite3.connect('credential.db')
    cur = conn.cursor()
    if table in ['teachers', 'staffs']:
        cur.execute(f"INSERT INTO {table} (username, password, gender) VALUES (?, ?, ?)", (username, password, gender))
    else:
        cur.execute(f"INSERT INTO {table} (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()

def update_gender_field(*args):
    user_type = user_type_var.get()
    if user_type in ['teacher', 'staff']:
        gender_label.grid(row=3, column=0, padx=10, pady=5)
        gender_menu.grid(row=3, column=1, padx=10, pady=5)
    else:
        gender_label.grid_remove()
        gender_menu.grid_remove()

def submit():
    user_type = user_type_var.get()
    username = username_var.get()
    password = password_var.get()
    gender = gender_var.get()
    if user_type not in ['admin', 'teacher', 'staff']:
        messagebox.showerror("Error", "Please select a user type.")
        return
    if not username or not password:
        messagebox.showerror("Error", "Username and password cannot be empty.")
        return
    if user_type in ['teacher', 'staff'] and not gender:
        messagebox.showerror("Error", "Please select a gender for teacher or staff.")
        return
    try:
        if user_type in ['teacher', 'staff']:
            add_user(user_type + "s", username, password, gender)
        else:
            add_user(user_type + "s", username, password)
        messagebox.showinfo("Success", f"{user_type.capitalize()} added successfully!")
        username_var.set("")
        password_var.set("")
        gender_var.set("")
    except Exception as e:
        messagebox.showerror("Database Error", str(e))

root = tk.Tk()
root.title("Add User")

user_type_var = tk.StringVar()
username_var = tk.StringVar()
password_var = tk.StringVar()
gender_var = tk.StringVar()

tk.Label(root, text="User Type:").grid(row=0, column=0, padx=10, pady=5)
user_type_menu = tk.OptionMenu(root, user_type_var, "admin", "teacher", "staff")
user_type_menu.grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Username:").grid(row=1, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=username_var).grid(row=1, column=1, padx=10, pady=5)

tk.Label(root, text="Password:").grid(row=2, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=password_var, show="*").grid(row=2, column=1, padx=10, pady=5)

gender_label = tk.Label(root, text="Gender:")
gender_menu = tk.OptionMenu(root, gender_var, "Male", "Female", "Other")

tk.Button(root, text="Add User", command=submit).grid(row=4, column=0, columnspan=2, pady=10)

user_type_var.trace('w', update_gender_field)
update_gender_field()

root.mainloop()