import tkinter as tk
from PIL import Image, ImageTk
import random
import socket
import networkx as nx
import matplotlib.pyplot as plt
import time
import re
from tkinter import messagebox  
import threading
import json
from tkinter import filedialog


def is_valid_ip(ip):
    """Validates an IPv4 address."""
    pattern = r"^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\." \
              r"(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\." \
              r"(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\." \
              r"(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$"
    return re.match(pattern, ip) is not None

def is_valid_mac(mac):
    """Validates a MAC address."""
    pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
    return re.match(pattern, mac) is not None

def is_valid_subnet(subnet):
    """Validates a subnet mask pattern of 255.255.number.number."""
    pattern = r"^255\.255\.(\d{1,3})\.(\d{1,3})$"
    match = re.match(pattern, subnet)
    if not match:
        return False
    # Ensure the last two numbers are within 0-255
    return all(0 <= int(group) <= 255 for group in match.groups())


# Validate and save function
def validate_and_save(ip, mac, subnet, popup, save_action):
    if not is_valid_ip(ip):
        messagebox.showerror("Invalid Input", f"IP Address '{ip}' is not valid.")
        return
    if not is_valid_mac(mac):
        messagebox.showerror("Invalid Input", f"MAC Address '{mac}' is not valid.")
        return
    if not is_valid_subnet(subnet):
        messagebox.showerror("Invalid Input", f"Subnet Mask '{subnet}' is not valid.")
        return
    save_action()  # Save the changes if validation passes
    popup.destroy()



class NetworkDesignApp:

    def save_configuration(self):
        """Save the canvas state (devices and connections) to a JSON file."""
        config = {
            "devices": {
                device_id: {
                    "label": self.canvas.itemcget(data["label"], "text"),
                    "icon_coords": self.canvas.coords(data["icon"]),
                    "ip": data["ip"],
                    "mac": data["mac"],
                    "subnet": data["subnet"]
                }
                for device_id, data in self.devices.items()
            },
            "connections": [
                (self.get_line_devices(line)) for line in self.canvas.find_all() if self.canvas.type(line) == "line"
            ]
        }

        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, "w") as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Save Configuration", "Configuration saved successfully!")


    def load_configuration(self):
        """Load the canvas state (devices and connections) from a JSON file."""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, "r") as f:
                config = json.load(f)

            # Clear current canvas
            self.canvas.delete("all")
            self.devices = {}

            # Add devices
            for device_id, data in config["devices"].items():
                label = data["label"]
                coords = data["icon_coords"]
                self.add_device(coords[0], coords[1], label.split(" ")[0])
                self.devices[device_id].update({
                    "ip": data["ip"],
                    "mac": data["mac"],
                    "subnet": data["subnet"]
                })

            # Add connections
            for start_device, end_device in config["connections"]:
                if start_device in self.devices and end_device in self.devices:
                    start_coords = self.get_device_center(start_device)
                    end_coords = self.get_device_center(end_device)
                    self.draw_connection(start_coords, end_coords, start_device, end_device)

            messagebox.showinfo("Load Configuration", "Configuration loaded successfully!")

    
    def __init__(self, root):
        self.root = root
        self.root.title("Mister A Networking")
        self.root.geometry("1000x700")

        self.is_dark_mode = False  # State to track theme mode

        
        # Load theme icons
        self.moon_icon = ImageTk.PhotoImage(Image.open("moon.png").resize((40, 40)))
        self.sun_icon = ImageTk.PhotoImage(Image.open("sun.png").resize((40, 40)))

        # Header (Franchise-style title with large font)
        self.header_frame = tk.Frame(root, bg="#191970", height=100)
        self.header_frame.pack(fill=tk.X)
        self.header_label = tk.Label(
            self.header_frame, text="Mister       Networking",
            font=("Arial", 24, "bold"), fg="white", bg="#191970"
        )
        self.header_label.pack(pady=25)
        
        # Theme toggle button with moon icon initially
        self.theme_button = tk.Button(
            self.header_frame, image=self.moon_icon,
            command=self.toggle_theme, bg="#191970", borderwidth=0
        )
        self.theme_button.place(relx=0.94, rely=0.3)  # Position the button within the header

        # ICON HEADER
        self.new_button_icon = ImageTk.PhotoImage(Image.open("Aveng.png").resize((40, 40)))  # Adjust file name and size
        self.new_button = tk.Button(
            self.header_frame, image=self.new_button_icon,
            command=self.some_function, bg="#191970", borderwidth=0
        )
        self.new_button.place(relx=0.455, rely=0.3)  # Adjust position as needed

        # Visualization buttons
        self.add_visualize_buttons_left()

        # Create canvas for drawing network devices and connections
        self.canvas = tk.Canvas(root, bg="white", width=1210, height=550, bd=2, relief="solid", highlightthickness=0)
        self.canvas.pack()

        # Initialize device list and variables
        self.devices = {}
        self.selected_device = None
        self.connecting = False
        self.start_coords = None
        self.start_device = None
        self.connection_type = "Ethernet"
        self.placing_device = False
        self.device_to_place = None
        self.connect_mode = False
        self.delete_mode = False  # New: Toggle delete mode

        # Load device icons
        self.device_images = {
        "Router": ImageTk.PhotoImage(Image.open("router.png").resize((40, 40))),
        "Switch": ImageTk.PhotoImage(Image.open("switch.png").resize((45, 45))),
        "Computer": ImageTk.PhotoImage(Image.open("computer.png").resize((50, 50))),
        "Laptop": ImageTk.PhotoImage(Image.open("laptop.png").resize((50, 50))),
        "Server": ImageTk.PhotoImage(Image.open("server.png").resize((50, 50))),
        "Smartphone": ImageTk.PhotoImage(Image.open("smartphone.png").resize((50, 50))) 
    }

        # Create a frame for the buttons
        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)

        # Add buttons for device management and actions
        self.device_button = tk.Button(
            button_frame, text="Devices", bg="navyblue", fg="white",
            font=("Arial", 12, "bold"), command=self.show_device_menu
        )
        self.device_button.pack(side=tk.LEFT, padx=10)

        self.computer_button = tk.Button(
            button_frame, text="End User", bg="navyblue", fg="white",
            font=("Arial", 12, "bold"), command=self.show_computer_menu
        )
        self.computer_button.pack(side=tk.LEFT, padx=10)

        self.connection_button = tk.Button(
            button_frame, text="Connections", bg="#5D3FD3", fg="white",
            font=("Arial", 12, "bold"), command=self.show_connection_menu
        )
        self.connection_button.pack(side=tk.LEFT, padx=10)

        self.connect_button = tk.Button(
            button_frame, text="Connect", bg="#5D3FD3", fg="white",
            font=("Arial", 12, "bold"), command=self.toggle_connect_mode
        )
        self.connect_button.pack(side=tk.LEFT, padx=10)

        self.delete_button = tk.Button(
            button_frame, text="Delete", bg="red", fg="white",
            font=("Arial", 12, "bold"), command=self.toggle_delete_mode
        )
        self.delete_button.pack(side=tk.LEFT, padx=10)

        self.send_packet_button = tk.Button(
            button_frame, text="Send Packet", bg="#0FFF50", fg="darkblue",
            font=("Arial", 12, "bold"), command=self.show_send_packet_menu
        )
        self.send_packet_button.pack(side=tk.LEFT, padx=10)

        # Add buttons for visualization and interaction
        simulate_button = tk.Button(
            button_frame, text="Ping", bg="#008080", fg="white",
            font=("Arial", 12, "bold"), command=self.show_interaction_menu
        )
        simulate_button.pack(side=tk.LEFT, padx=10)

        # Dropdown menus for devices and connections
        self.device_menu = tk.Menu(root, tearoff=0)
        self.device_menu.add_command(label="Add Router", command=self.prepare_to_add_router)
        self.device_menu.add_command(label="Add Switch", command=self.prepare_to_add_switch)

        self.computer_menu = tk.Menu(root, tearoff=0)
        self.computer_menu.add_command(label="Add Computer", command=self.prepare_to_add_computer)
        self.computer_menu.add_command(label="Add Laptop", command=self.prepare_to_add_laptop)
        self.computer_menu.add_command(label="Add Server", command=self.prepare_to_add_server)
        self.computer_menu.add_command(label="Add Smartphone", command=self.prepare_to_add_smartphone)  

        self.connection_menu = tk.Menu(root, tearoff=0)
        self.connection_menu.add_command(label="Ethernet", command=lambda: self.set_connection_type("Ethernet"))
        self.connection_menu.add_command(label="Fiber Optic", command=lambda: self.set_connection_type("Fiber Optic"))
        self.connection_menu.add_command(label="Wireless", command=lambda: self.set_connection_type("Wireless"))

        # Bind canvas events
        self.canvas.bind("<B1-Motion>", self.on_device_drag)
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<ButtonRelease-1>", self.on_device_release)
        self.canvas.bind("<Double-1>", self.on_double_click)


    def some_function(self):
        messagebox.showinfo("Mister A", "Start simulating MISTER!")

    # Add visualize buttons and save and load to a left-side frame
    def add_visualize_buttons_left(self):
        """Adds buttons to the left of the screen to trigger visualizations."""
        left_frame = tk.Frame(self.root, bg="white", width=120)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        # Add label at the top of the frame
        visualize_label = tk.Label(left_frame, text="Options", bg="white", font=("Arial", 14, "bold"))
        visualize_label.pack(pady=10)

        topology_button = tk.Button(
            left_frame, text="Visualize Topology", bg="#008080", fg="white",
            font=("Arial", 10, "bold"), command=self.plot_topology
        )
        topology_button.pack(pady=10, fill=tk.X)

        latency_button = tk.Button(
            left_frame, text="Show Latency", bg="#008080", fg="white",
            font=("Arial", 10, "bold"), command=self.plot_latency_graph
        )
        latency_button.pack(pady=10, fill=tk.X)

        # Add the Save and Load Configuration buttons here
        save_button = tk.Button(
            left_frame, text="Save Configuration", bg="#BA55D3", fg="white",
            font=("Arial", 10, "bold"), command=self.save_configuration
        )
        save_button.pack(pady=5, fill=tk.X)

        load_button = tk.Button(
            left_frame, text="Load Configuration", bg="#8A2BE2", fg="white",
            font=("Arial", 10, "bold"), command=self.load_configuration
        )
        load_button.pack(pady=5, fill=tk.X)

        # Add Picture button
        image_button = tk.Button(
            left_frame, text="Add Image", command=self.upload_image, bg="#005a5a", fg="white", font=("Arial", 10, "bold")
        )
        image_button.pack(pady=5, fill=tk.X)

        self.image_references = {}  # Dictionary to store image references

    def toggle_theme(self):
        """Toggles between light and dark mode."""
        self.is_dark_mode = not self.is_dark_mode

        # Define color schemes for dark and light mode
        colors = {
            "dark": {
                "root_bg": "#1e1e1e",
                "canvas_bg": "lightgray",
                "frame_bg": "#1e1e1e",
                "button_bg": "#444444",
                "button_fg": "white",
                "active_bg": "#555555",
                "active_fg": "white"
            },
            "light": {
                "root_bg": "white",
                "canvas_bg": "white",
                "frame_bg": "white",
                "button_bg": "#e0e0e0",
                "button_fg": "black",
                "active_bg": "#d9d9d9",
                "active_fg": "black"
            }
        }

        mode = "dark" if self.is_dark_mode else "light"
        theme = colors[mode]

        # Update the root background
        self.root.config(bg=theme["root_bg"])

        # Update the canvas background
        self.canvas.config(bg=theme["canvas_bg"])

        # Update all frames and buttons to match the selected theme
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame) and widget != self.header_frame:  # Exclude the header frame
                widget.config(bg=theme["frame_bg"])
            elif isinstance(widget, tk.Button):
                widget.config(
                    bg=theme["button_bg"], fg=theme["button_fg"],
                    activebackground=theme["active_bg"], activeforeground=theme["active_fg"]
                )

        # Update the toggle button icon
        new_icon = self.sun_icon if self.is_dark_mode else self.moon_icon
        self.theme_button.config(image=new_icon)

    def show_device_menu(self):
        self.show_popup("Devices", [
            ("Router", self.prepare_to_add_router),
            ("Switch", self.prepare_to_add_switch)
        ], "200x200")  # Set the size for Devices popup

    def show_computer_menu(self):
        self.show_popup("End User", [
            ("Computer", self.prepare_to_add_computer),
            ("Laptop", self.prepare_to_add_laptop),
            ("Server", self.prepare_to_add_server),
            ("Smartphone", self.prepare_to_add_smartphone)
        ], "400x400")  # Set the size for End User popup

    def show_connection_menu(self):
        x = self.connection_button.winfo_rootx()
        y = self.connection_button.winfo_rooty() + self.connection_button.winfo_height()
        self.connection_menu.post(x, y)

    def show_popup(self, title, items, size):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.geometry(size)  # Use the size passed as an argument
        popup.resizable(False, False)

        # Adjust popup theme based on the current mode
        if self.is_dark_mode:
            popup.configure(bg="#1e1e1e")
            button_bg = "#444444"
            button_fg = "white"
        else:
            popup.configure(bg="white")
            button_bg = "#e0e0e0"
            button_fg = "black"

        for label, command in items:
            # Use images for specific buttons
            if label == "Router":
                button_image = self.device_images["Router"]
            elif label == "Switch":
                button_image = self.device_images["Switch"]
            elif label == "Computer":
                button_image = self.device_images["Computer"]
            elif label == "Laptop":
                button_image = self.device_images["Laptop"]
            elif label == "Server":
                button_image = self.device_images["Server"]
            elif label == "Smartphone":
                button_image = self.device_images["Smartphone"]
            else:
                button_image = None

            frame = tk.Frame(popup, bg=popup.cget("bg"))
            frame.pack(pady=10)

            if button_image:
                button = tk.Button(
                    frame, image=button_image, command=command,
                    bg=button_bg, borderwidth=0, activebackground=button_bg
                )
                button.pack()
                label_widget = tk.Label(
                    frame, text=label, fg=button_fg, bg=popup.cget("bg"), font=("Arial", 10)
                )
                label_widget.pack()
            else:
                button = tk.Button(
                    frame, text=label, command=command,
                    bg=button_bg, fg=button_fg,
                    activebackground=button_bg, activeforeground=button_fg
                )
                button.pack()

    def toggle_delete_mode(self):
        self.delete_mode = not self.delete_mode
        if self.delete_mode:
            self.root.config(cursor="crosshair")  # Crosshair cursor for delete
            self.delete_button.config(bg="darkred", text="Deleting...")
        else:
            self.root.config(cursor="")  # Reset cursor
            self.delete_button.config(bg="red", text="Delete")

    def toggle_connect_mode(self):
        self.connect_mode = not self.connect_mode
        if self.connect_mode:
            self.root.title("Network Design Tool - Connect Mode")
            self.connect_button.config(bg="#0000FF", text="Connecting...")
        else:
            self.root.title("Network Design Tool")
            self.connect_button.config(bg="#5D3FD3", text="Connect")

    def set_connection_type(self, connection_type):
        self.connection_type = connection_type
        self.root.title(f"Network Design Tool - {connection_type} Mode")

    def prepare_to_add_router(self):
        self.device_to_place = "Router"
        self.placing_device = True
        self.root.config(cursor="crosshair")

    def prepare_to_add_switch(self):
        self.device_to_place = "Switch"
        self.placing_device = True
        self.root.config(cursor="crosshair")

    def prepare_to_add_computer(self):
        self.device_to_place = "Computer"
        self.placing_device = True
        self.root.config(cursor="crosshair")

    def prepare_to_add_laptop(self):
        self.device_to_place = "Laptop"
        self.placing_device = True
        self.root.config(cursor="crosshair")

    def prepare_to_add_server(self):
        self.device_to_place = "Server"
        self.placing_device = True
        self.root.config(cursor="crosshair")
        
    def prepare_to_add_smartphone(self):
        self.device_to_place = "Smartphone"
        self.placing_device = True
        self.root.config(cursor="crosshair")

    def generate_ip_address(self):
        while True:
            ip = f"192.168.1.{random.randint(1, 254)}"
            if is_valid_ip(ip):
                return ip

    def generate_mac_address(self):
        while True:
            mac = ':'.join(['{:02x}'.format(random.randint(0, 255)) for _ in range(6)])
            if is_valid_mac(mac):
                return mac
            
    def add_device(self, x, y, label):
        count = sum(1 for device_id in self.devices if device_id.startswith(label))
        device_name = f"{label} {count + 1}"

        ip_address = self.generate_ip_address()
        mac_address = self.generate_mac_address()
        subnet_mask = "255.255.255.0"  # Default subnet mask

        device_id = f"{label}_{count + 1}"

        # Create the device as a single entity with a common tag
        icon = self.canvas.create_image(x, y, image=self.device_images[label], tags=device_id)
        text = self.canvas.create_text(x, y + 40, text=device_name, font=("Arial", 10), tags=device_id)
        self.devices[device_id] = {
            "icon": icon,
            "label": text,  # This must point to the text object ID
            "lines": [],
            "ip": ip_address,
            "mac": mac_address,
            "subnet": subnet_mask,
        }

        # Add event bindings to the tag (affects both icon and text)
        self.canvas.tag_bind(device_id, "<Button-1>", lambda event, dev_id=device_id: self.on_device_click(event, dev_id))
        self.canvas.tag_bind(device_id, "<B1-Motion>", lambda event, dev_id=device_id: self.on_device_drag(event, dev_id))
        self.canvas.tag_bind(device_id, "<ButtonRelease-1>", lambda event, dev_id=device_id: self.on_device_release(event, dev_id))


    def on_left_click(self, event):
        if self.delete_mode:
            self.delete_at(event.x, event.y)
        elif self.connect_mode:
            closest = self.canvas.find_closest(event.x, event.y)
            for device_id, device_data in self.devices.items():
                if closest[0] in (device_data["icon"], device_data["label"]):
                    if not self.connecting:
                        self.start_coords = self.get_device_center(device_id)
                        self.start_device = device_id
                        self.connecting = True
                    else:
                        end_coords = self.get_device_center(device_id)
                        self.draw_connection(self.start_coords, end_coords, self.start_device, device_id)
                        self.connecting = False
                    return
        elif self.placing_device:
            self.add_device(event.x, event.y, self.device_to_place)
            self.placing_device = False
            self.root.config(cursor="")
        else:
            closest = self.canvas.find_closest(event.x, event.y)
            for device_id, device_data in self.devices.items():
                if closest[0] in (device_data["icon"], device_data["label"]):
                    self.selected_device = device_id
                    break

    def on_double_click(self, event):
        closest = self.canvas.find_closest(event.x, event.y)
        for device_id, device_data in self.devices.items():
            if closest[0] in (device_data["icon"], device_data["label"]):
                self.show_device_info(device_data)
                break

    def on_device_click(self, event, device_id):
        self.selected_device = device_id

    def on_device_drag(self, event, device_id):
        if self.selected_device == device_id:
            dx = event.x - self.get_device_center(device_id)[0]
            dy = event.y - self.get_device_center(device_id)[1]
            self.canvas.move(device_id, dx, dy)  # Moves all elements with the tag
            for line in self.devices[device_id]["lines"]:
                self.update_connection(line)

    def on_device_release(self, event, device_id):
        self.selected_device = None

    def show_device_info(self, device_data):
        popup = tk.Toplevel(self.root)
        popup.title("Device Info")
        popup.geometry("300x250")

        # Adjust popup theme based on the current mode
        if self.is_dark_mode:
            popup.configure(bg="#1e1e1e")
            label_fg = "white"
            entry_bg = "#333333"
            entry_fg = "white"
        else:
            popup.configure(bg="white")
            label_fg = "black"
            entry_bg = "white"
            entry_fg = "black"

        # Device name
        tk.Label(popup, text="Device Name:", fg=label_fg, bg=popup.cget("bg")).grid(row=0, column=0, sticky=tk.W)
        name_entry = tk.Entry(popup, bg=entry_bg, fg=entry_fg)
        name_entry.grid(row=0, column=1)
        name_entry.insert(0, self.canvas.itemcget(device_data["label"], "text"))

        # IP address
        tk.Label(popup, text="IP Address:", fg=label_fg, bg=popup.cget("bg")).grid(row=1, column=0, sticky=tk.W)
        ip_entry = tk.Entry(popup, bg=entry_bg, fg=entry_fg)
        ip_entry.grid(row=1, column=1)
        ip_entry.insert(0, device_data["ip"])

        # MAC address
        tk.Label(popup, text="MAC Address:", fg=label_fg, bg=popup.cget("bg")).grid(row=2, column=0, sticky=tk.W)
        mac_entry = tk.Entry(popup, bg=entry_bg, fg=entry_fg)
        mac_entry.grid(row=2, column=1)
        mac_entry.insert(0, device_data["mac"])

        # Subnet mask
        tk.Label(popup, text="Subnet Mask:", fg=label_fg, bg=popup.cget("bg")).grid(row=3, column=0, sticky=tk.W)
        subnet_entry = tk.Entry(popup, bg=entry_bg, fg=entry_fg)
        subnet_entry.grid(row=3, column=1)
        subnet_entry.insert(0, device_data.get("subnet", "255.255.255.0"))  # Default to 255.255.255.0 if missing

        # Save changes button
        save_button = tk.Button(
            popup,
            text="Save",
            command=lambda: validate_and_save(
                ip_entry.get(),
                mac_entry.get(),
                subnet_entry.get(),
                popup,
                lambda: save_changes(device_data, name_entry, ip_entry, mac_entry, subnet_entry)
            ),
            bg="blue" if not self.is_dark_mode else "#0FFF50",
            fg="white" if not self.is_dark_mode else "black"
        )
        save_button.grid(row=4, column=0, columnspan=2)

        def save_changes(device_data, name_entry, ip_entry, mac_entry, subnet_entry):
            new_name = name_entry.get()
            new_ip = ip_entry.get()
            new_mac = mac_entry.get()
            new_subnet = subnet_entry.get()

            # Update the device attributes
            device_data["ip"] = new_ip
            device_data["mac"] = new_mac
            device_data["subnet"] = new_subnet

            # Update the canvas text
            self.canvas.itemconfig(device_data["label"], text=new_name)

    def get_device_center(self, device_id):
        device_data = self.devices[device_id]
        coords = self.canvas.coords(device_data["icon"])
        return coords[0], coords[1]

    def draw_connection(self, start_coords, end_coords, start_device, end_device):
        color = {
            "Ethernet": "black",
            "Fiber Optic": "blue",
            "Wireless": "green"
        }.get(self.connection_type, "black")

        line = self.canvas.create_line(start_coords, end_coords, fill=color, width=2)
        self.devices[start_device]["lines"].append(line)
        self.devices[end_device]["lines"].append(line)

    def update_connection(self, line):
        coords = self.canvas.coords(line)
        start_device, end_device = None, None
        for device_id, device_data in self.devices.items():
            if line in device_data["lines"]:
                if not start_device:
                    start_device = device_id
                else:
                    end_device = device_id
                    break
        if start_device and end_device:
            start_coords = self.get_device_center(start_device)
            end_coords = self.get_device_center(end_device)
            self.canvas.coords(line, start_coords[0], start_coords[1], end_coords[0], end_coords[1])

    def delete_at(self, x, y):
        closest = self.canvas.find_closest(x, y)  # Find the closest object
        item_type = self.canvas.type(closest[0])  # Get the type of the closest object

        # Check if the clicked item is a line
        if item_type == "line":
            self.delete_line(closest[0])
            return

        # If not a line, check for devices
        for device_id, device_data in list(self.devices.items()):
            if closest[0] in (device_data["icon"], device_data["label"]):
                # Delete connected lines first
                for line in device_data["lines"]:
                    self.canvas.delete(line)
                # Delete the device icon and label
                self.canvas.delete(device_data["icon"])
                self.canvas.delete(device_data["label"])
                # Remove device from the devices dictionary
                del self.devices[device_id]
                return

    def delete_line(self, line_id):
        """Deletes a connection line and removes references from connected devices."""
        for device_id, device_data in self.devices.items():
            if line_id in device_data["lines"]:
                device_data["lines"].remove(line_id)  # Remove line reference from device
        self.canvas.delete(line_id)  # Remove the line from the canvas

#////////////////////////////////////////\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def export_to_networkx(self):
        """Exports the network topology to a NetworkX graph."""
        G = nx.Graph()
        for device_id, device_data in self.devices.items():
            # Add nodes with updated device label
            G.add_node(
                device_id,
                label=device_data.get("label_text", self.canvas.itemcget(device_data["label"], "text")),
                ip=device_data["ip"],
                mac=device_data["mac"]
            )
        for device_id, device_data in self.devices.items():
            for line in device_data["lines"]:
                start_device, end_device = self.get_line_devices(line)
                if start_device and end_device:
                    G.add_edge(start_device, end_device, connection=self.connection_type)
        return G

    
    def get_line_devices(self, line):
        """Finds the start and end devices connected by a line."""
        for device_id, device_data in self.devices.items():
            if line in device_data["lines"]:
                if "start" not in locals():
                    start = device_id
                else:
                    end = device_id
                    return start, end
        return None, None
    
    def plot_topology(self):
        """Plots the network topology."""
        G = self.export_to_networkx()

        # Prepare node labels and positions
        pos = nx.spring_layout(G)
        labels = nx.get_node_attributes(G, 'label')

        # Check the current theme mode
        if self.is_dark_mode:
            plt.style.use("dark_background")
            node_color = 'skyblue'
            font_color = 'white'
            edge_color = 'lightgray'
            title_color = 'white'
        else:
            plt.style.use("default")
            node_color = 'blue'
            font_color = 'black'
            edge_color = 'black'
            title_color = 'black'

        # Plot the graph
        plt.figure(figsize=(8, 6))
        nx.draw(
            G, pos, with_labels=True, labels=labels, 
            node_color=node_color, node_size=2000, 
            font_size=10, font_color=font_color, font_weight='bold'
        )
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels=nx.get_edge_attributes(G, 'connection'), 
            font_size=8, font_color=edge_color
        )
        plt.title("Network Topology", fontsize=16, color=title_color)
        plt.show()


    def plot_latency_graph(self):
        """Plots a mock latency graph for devices."""
        device_names = [data["label"] for data in self.devices.values()]
        latencies = [random.randint(1, 100) for _ in device_names]  # Mock data for latencies

        # Check the current theme mode
        if self.is_dark_mode:
            plt.style.use("dark_background")
            bar_color = 'limegreen'
            text_color = 'white'
        else:
            plt.style.use("default")
            bar_color = 'blue'
            text_color = 'black'

        # Plot the latency bar graph
        plt.figure(figsize=(10, 6))
        plt.bar(device_names, latencies, color=bar_color)
        plt.xlabel("Devices", fontsize=12, color=text_color)
        plt.ylabel("Latency (ms)", fontsize=12, color=text_color)
        plt.title("Latency per Device", fontsize=16, color=text_color)
        plt.xticks(rotation=45, ha="right", color=text_color)
        plt.yticks(color=text_color)
        plt.tight_layout()
        plt.show()

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
    def simulate_interaction(self, from_device, to_device):
        if from_device in self.devices and to_device in self.devices:
            # Create a NetworkX graph representation
            G = self.export_to_networkx()

            # Check if the devices are connected
            if nx.has_path(G, from_device, to_device):
                path = nx.shortest_path(G, from_device, to_device)

                # Get the target device's IP
                target_ip = self.devices[to_device]["ip"]

                # Generate random ping statistics
                response_times = [random.randint(1, 100) for _ in range(4)]  # Random times in ms
                ttls = [random.randint(50, 128) for _ in range(4)]  # Random TTL values
                min_time = min(response_times)
                max_time = max(response_times)
                avg_time = sum(response_times) // len(response_times)

                # Create the ping message
                message = f"Pinging {to_device} [{target_ip}] with 32 bytes of data:\n"
                for time, ttl in zip(response_times, ttls):
                    message += f"Reply from {target_ip}: bytes=32 time={time}ms TTL={ttl}\n"

                # Add Ping statistics
                message += f"\nPing statistics for {target_ip}:\n"
                message += f"    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),\n"
                message += "Approximate round trip times in milli-seconds:\n"
                message += f"    Minimum = {min_time}ms, Maximum = {max_time}ms, Average = {avg_time}ms"

                # Display result in a styled popup
                self.show_message_popup("Ping Result", message)
            else:
                # Display error pop-up
                messagebox.showerror("Ping Error", "Could not reach the host.")
        else:
            messagebox.showerror("Ping Error", "Invalid device selection.")

    # Show Interaction Menu Updated
    def show_interaction_menu(self):
        popup = tk.Toplevel(self.root)
        popup.title("Interact Between Devices")
        popup.geometry("300x200")

        # Adjust popup theme based on the current mode
        if self.is_dark_mode:
            popup.configure(bg="#1e1e1e")
            label_fg = "white"
            button_bg = "#444444"
            button_fg = "white"
        else:
            popup.configure(bg="white")
            label_fg = "black"
            button_bg = "#e0e0e0"
            button_fg = "black"

        def refresh_device_names():
            return {device_id: self.canvas.itemcget(data["label"], "text") for device_id, data in self.devices.items()}

        device_names = refresh_device_names()

        # Dropdown menu for 'from' device
        tk.Label(popup, text="From Device:", fg=label_fg, bg=popup.cget("bg")).grid(row=0, column=0, padx=10, pady=5)
        from_device = tk.StringVar(value=list(device_names.values())[0])
        from_menu = tk.OptionMenu(popup, from_device, *device_names.values())
        from_menu.configure(bg=button_bg, fg=button_fg, highlightthickness=0)
        from_menu.grid(row=0, column=1, padx=10, pady=5)

        # Dropdown menu for 'to' device
        tk.Label(popup, text="To Device:", fg=label_fg, bg=popup.cget("bg")).grid(row=1, column=0, padx=10, pady=5)
        to_device = tk.StringVar(value=list(device_names.values())[0])
        to_menu = tk.OptionMenu(popup, to_device, *device_names.values())
        to_menu.configure(bg=button_bg, fg=button_fg, highlightthickness=0)
        to_menu.grid(row=1, column=1, padx=10, pady=5)

        def trigger_interaction():
            from_id = next((k for k, v in device_names.items() if v == from_device.get()), None)
            to_id = next((k for k, v in device_names.items() if v == to_device.get()), None)
            self.simulate_interaction(from_id, to_id)
            popup.destroy()

        tk.Button(popup, text="Ping", command=trigger_interaction, bg=button_bg, fg=button_fg).grid(row=2, column=0, columnspan=2, pady=10)
        
#OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO#


    # Updated send_data_packet method
    def send_data_packet(self, from_device, to_device, data="Hello, Network!"):
        def simulate_packet():
            if from_device in self.devices and to_device in self.devices:
                G = self.export_to_networkx()
                if nx.has_path(G, from_device, to_device):
                    path = nx.shortest_path(G, from_device, to_device)

                    # Load the message icon (ensure the file is in the same directory or provide the full path)
                    message_icon = ImageTk.PhotoImage(Image.open("message.png").resize((15, 15)))

                    for i in range(len(path) - 1):
                        start_coords = self.get_device_center(path[i])
                        end_coords = self.get_device_center(path[i + 1])

                        # Create an image to represent the packet
                        packet = self.canvas.create_image(start_coords[0], start_coords[1], image=message_icon)

                        # Animate the packet along the line
                        for t in range(21):  # 21 steps for smoother animation
                            x = start_coords[0] + (end_coords[0] - start_coords[0]) * t / 20
                            y = start_coords[1] + (end_coords[1] - start_coords[1]) * t / 20
                            self.canvas.coords(packet, x, y)
                            time.sleep(0.05)  # Adjust for speed of animation
                            self.root.update_idletasks()

                        # Remove the packet from the canvas after reaching the endpoint
                        self.canvas.delete(packet)

                    message = (
                        f"Data Packet Transmission:\n"
                        f"From: {from_device}\n"
                        f"To: {to_device}\n"
                        f"Data: {data}\n"
                        f"Status: Success"
                    )
                else:
                    message = f"Data Packet Transmission Failed:\nNo Path Between {from_device} and {to_device}"
            else:
                message = f"Data Packet Transmission Failed:\nInvalid Devices: {from_device}, {to_device}"

            self.root.after(0, self.show_message_popup, "Data Packet Transmission", message)

        threading.Thread(target=simulate_packet, daemon=True).start()
            
        # Helper to display popups (to avoid duplicating code)
    def show_message_popup(self, title, message):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.geometry("400x200")

        # Adjust popup theme based on the current mode
        if self.is_dark_mode:
            popup.configure(bg="#1e1e1e")
            text_bg = "#333333"
            text_fg = "white"
            button_bg = "#444444"
            button_fg = "white"
        else:
            popup.configure(bg="white")
            text_bg = "white"
            text_fg = "black"
            button_bg = "#e0e0e0"
            button_fg = "black"

        # Add a label for the message
        message_label = tk.Label(
            popup, text=message, justify=tk.LEFT, wraplength=380,
            bg=text_bg, fg=text_fg, font=("Arial", 10), padx=10, pady=10
        )
        message_label.pack(pady=10)

        # Add a close button
        close_button = tk.Button(
            popup, text="Close", command=popup.destroy,
            bg=button_bg, fg=button_fg, font=("Arial", 10)
        )
        close_button.pack(pady=10)

    def show_send_packet_menu(self):
        popup = tk.Toplevel(self.root)
        popup.title("Send Data Packet")
        popup.geometry("300x300")  # Adjusted height to accommodate all elements

        # Adjust popup theme based on the current mode
        if self.is_dark_mode:
            popup.configure(bg="#1e1e1e")
            label_fg = "white"
            entry_bg = "#333333"
            entry_fg = "white"
            button_bg = "#444444"
            button_fg = "white"
        else:
            popup.configure(bg="white")
            label_fg = "black"
            entry_bg = "white"
            entry_fg = "black"
            button_bg = "#e0e0e0"
            button_fg = "black"

        def refresh_device_list():
            """Refresh the dropdown menus with updated device names."""
            return {device_id: data.get("label_text", self.canvas.itemcget(data["label"], "text")) 
                    for device_id, data in self.devices.items()}

        devices = refresh_device_list()

        # Dropdown menu for 'from' device
        tk.Label(popup, text="From Device:", fg=label_fg, bg=popup.cget("bg")).grid(row=0, column=0, padx=10, pady=5)
        from_device = tk.StringVar(value=list(devices.values())[0])
        from_menu = tk.OptionMenu(popup, from_device, *devices.values())
        from_menu.configure(bg=button_bg, fg=button_fg, highlightthickness=0)
        from_menu.grid(row=0, column=1, padx=10, pady=5)

        # Dropdown menu for 'to' device
        tk.Label(popup, text="To Device:", fg=label_fg, bg=popup.cget("bg")).grid(row=1, column=0, padx=10, pady=5)
        to_device = tk.StringVar(value=list(devices.values())[0])
        to_menu = tk.OptionMenu(popup, to_device, *devices.values())
        to_menu.configure(bg=button_bg, fg=button_fg, highlightthickness=0)
        to_menu.grid(row=1, column=1, padx=10, pady=5)

        # Entry for data content
        tk.Label(popup, text="Data:", fg=label_fg, bg=popup.cget("bg")).grid(row=2, column=0, padx=10, pady=5)
        data_entry = tk.Entry(popup, bg=entry_bg, fg=entry_fg)
        data_entry.grid(row=2, column=1, padx=10, pady=5)
        data_entry.insert(0, "Hello, Network!")

        def trigger_send_packet(protocol):
            # Match selected names back to device IDs
            from_device_id = next((device_id for device_id, name in devices.items() if name == from_device.get()), None)
            to_device_id = next((device_id for device_id, name in devices.items() if name == to_device.get()), None)

            if from_device_id and to_device_id:
                if protocol == "TCP":
                    self.send_data_packet_with_return(from_device_id, to_device_id, data_entry.get())
                else:
                    self.send_data_packet(from_device_id, to_device_id, data_entry.get())
            else:
                messagebox.showerror("Error", "Invalid device selected.")
            popup.destroy()

        # Buttons for sending with TCP or UDP
        tcp_button = tk.Button(popup, text="Send via TCP", command=lambda: trigger_send_packet("TCP"),
                            bg=button_bg, fg=button_fg)
        tcp_button.grid(row=3, column=0, pady=10, padx=5, sticky="ew")

        udp_button = tk.Button(popup, text="Send via UDP", command=lambda: trigger_send_packet("UDP"),
                            bg=button_bg, fg=button_fg)
        udp_button.grid(row=3, column=1, pady=10, padx=5, sticky="ew")

        # Close button
        tk.Button(popup, text="Close", command=popup.destroy, bg=button_bg, fg=button_fg).grid(
            row=4, column=0, columnspan=2, pady=10)


    def send_data_packet_with_return(self, from_device, to_device, data="Hello, Network!"):
        def simulate_packet():
            if from_device in self.devices and to_device in self.devices:
                G = self.export_to_networkx()
                if nx.has_path(G, from_device, to_device):
                    path = nx.shortest_path(G, from_device, to_device)

                    # Load the message icon (ensure the file is in the same directory or provide the full path)
                    message_icon = ImageTk.PhotoImage(Image.open("message.png").resize((15, 15)))

                    # Forward message from source to destination
                    for i in range(len(path) - 1):
                        start_coords = self.get_device_center(path[i])
                        end_coords = self.get_device_center(path[i + 1])

                        # Create an image to represent the packet
                        packet = self.canvas.create_image(start_coords[0], start_coords[1], image=message_icon)

                        # Animate the packet along the line
                        for t in range(21):  # 21 steps for smoother animation
                            x = start_coords[0] + (end_coords[0] - start_coords[0]) * t / 20
                            y = start_coords[1] + (end_coords[1] - start_coords[1]) * t / 20
                            self.canvas.coords(packet, x, y)
                            time.sleep(0.05)  # Adjust for speed of animation
                            self.root.update_idletasks()

                        # Remove the packet from the canvas after reaching the endpoint
                        self.canvas.delete(packet)

                    # Backward acknowledgment message from destination to source
                    for i in range(len(path) - 1, 0, -1):
                        start_coords = self.get_device_center(path[i])
                        end_coords = self.get_device_center(path[i - 1])

                        # Create an image to represent the acknowledgment packet
                        ack_packet = self.canvas.create_image(start_coords[0], start_coords[1], image=message_icon)

                        # Animate the packet along the line
                        for t in range(21):  # 21 steps for smoother animation
                            x = start_coords[0] + (end_coords[0] - start_coords[0]) * t / 20
                            y = start_coords[1] + (end_coords[1] - start_coords[1]) * t / 20
                            self.canvas.coords(ack_packet, x, y)
                            time.sleep(0.05)  # Adjust for speed of animation
                            self.root.update_idletasks()

                        # Remove the acknowledgment packet from the canvas after reaching the endpoint
                        self.canvas.delete(ack_packet)

                    message = (
                        f"TCP Data Packet Transmission Round Trip: 60ms\n"
                        f"From: {from_device}\n"
                        f"To: {to_device}\n"
                        f"Data: {data}\n"
                        f"Acknowledgment: Received\n"
                        f"Status: Success"
                    )
                else:
                    message = f"Data Packet Transmission Failed:\nNo Path Between {from_device} and {to_device}"
            else:
                message = f"Data Packet Transmission Failed:\nInvalid Devices: {from_device}, {to_device}"

            self.root.after(0, self.show_message_popup, "TCP Data Packet Transmission", message)

        threading.Thread(target=simulate_packet, daemon=True).start()

    def upload_image(self):
        """Allows the user to upload an image and place it on the canvas."""
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")])
        if file_path:
            # Load and resize the image
            image = Image.open(file_path).resize((100, 100))  # Resize as needed
            tk_image = ImageTk.PhotoImage(image)

            # Default placement coordinates
            x, y = 200, 200
            image_id = self.canvas.create_image(x, y, image=tk_image, tags="uploaded_image")

            # Save reference to prevent garbage collection
            self.image_references[image_id] = tk_image

            # Bind events for dragging and deleting
            self.canvas.tag_bind(image_id, "<B1-Motion>", lambda event: self.on_image_drag(event, image_id))
            self.canvas.tag_bind(image_id, "<Button-3>", lambda event: self.delete_image(image_id))

    def on_image_drag(self, event, image_id):
        """Handles dragging of images on the canvas."""
        self.canvas.coords(image_id, event.x, event.y)


    def delete_image(self, image_id):
        """Deletes an image from the canvas."""
        if image_id in self.image_references:
            del self.image_references[image_id]  # Remove reference
        self.canvas.delete(image_id)


if __name__ == "__main__":
    root = tk.Tk()
    icon = tk.PhotoImage(file="A.png")
    root.iconphoto(False, icon)
    app = NetworkDesignApp(root)
    root.mainloop()
    app.add_save_load_buttons()

    #Final code