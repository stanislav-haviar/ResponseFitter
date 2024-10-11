# app.py

import tkinter as tk
from scipy.signal import medfilt, savgol_filter
from tkinter import ttk, filedialog, messagebox, simpledialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector
import numpy as np
import os

from modules.data_loader import DataLoader
from modules.fitter import Fitter

class App(tk.Tk):
    def __init__(self, BASE_DIR):
        super().__init__()
        self.title("Response Fitter")
        self.geometry("1200x800")
        icon_path = os.path.join(BASE_DIR, "icons", "app.ico")
        self.dialog_icon = os.path.join(BASE_DIR, "icons", "app_bw.ico")
        self.iconbitmap(False, icon_path)

        self.data = None  # Dictionary to hold 'x', 'y', 'c', 'xlabel', 'ylabel', 'zlabel'
        self.knees = []  # List to hold identified knees
        self.knee_annotations = []
        self.sections = []  # List to hold sections for fitting
        self.fits = []  # List to hold fitting results
        self.loaded_filename = ""  # To store the name of the loaded file
        self.highlight_rectangle = None  # To keep track of the highlight rectangle


        self.columns = ("#", "From", "To", "Type", "y0", "A1", "tau1", "A2", "tau2", "tau90", "Comment")
        self.columns_formats = ("{:d}", "{:.2f}", "{:.2f}", "{}", "{:.5e}", "{:.5G}", "{:.5G}", "{:.5G}", "{:.5G}", "{:.3G}", "{}")

        self.fitter = Fitter()

        self.create_widgets()

    def create_widgets(self):
        # Top frame with buttons
        top_frame = tk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        # Left-aligned buttons
        left_button_frame = tk.Frame(top_frame)
        left_button_frame.pack(side=tk.LEFT)

        open_button = tk.Button(left_button_frame, text="Open Data (Delimited)", command=self.open_data)
        open_button.pack(side=tk.LEFT, padx=5, pady=5)

        crop_button = tk.Button(left_button_frame, text="Crop Data", command=self.crop_data)
        crop_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Right-aligned buttons
        right_button_frame = tk.Frame(top_frame)
        right_button_frame.pack(side=tk.RIGHT)

        save_button = tk.Button(right_button_frame, text="Save Project", command=self.save_project, state="disabled")
        save_button.pack(side=tk.RIGHT, padx=5, pady=5)

        export_plot_button = tk.Button(right_button_frame, text="Export Plot", command=self.export_plot)
        export_plot_button.pack(side=tk.RIGHT, padx=5, pady=5)

        export_fits_button = tk.Button(right_button_frame, text="Export Fits", command=self.export_fits, state="disabled")
        export_fits_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Main frame
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        plot_frame = tk.Frame(main_frame)
        plot_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # Plotting area
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.plot_axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        # self.canvas.draw()  # Remove this line from here

        # Add the navigation toolbar
        toolbar_frame = tk.Frame(plot_frame)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        # Pack the canvas
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.draw()

        # Add cursors A and B using SpanSelector
        self.cursor_A = None
        self.cursor_B = None
        self.cursor_A_line = None
        self.cursor_B_line = None
        self.span = SpanSelector(self.plot_axes, self.on_select, 'horizontal', useblit=True, interactive=True)

        # Right panel with controls
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)


        find_knees_button = tk.Button(right_frame, text="Find Knees", command=self.find_knees, state="disabled")
        find_knees_button.pack(padx=5, pady=5, fill=tk.X)

        edit_knees_button = tk.Button(right_frame, text="Edit Knees", command=self.edit_knees)
        edit_knees_button.pack(padx=5, pady=5, fill=tk.X)

        remove_knees_button = tk.Button(right_frame, text="Remove Knees", command=self.remove_knees)
        remove_knees_button.pack(padx=5, pady=5, fill=tk.X)

        create_sections_button = tk.Button(right_frame, text="Create Sections", command=self.create_sections)
        create_sections_button.pack(padx=5, pady=5, fill=tk.X)

        create_section_button = tk.Button(right_frame, text="Create Section", command=self.create_section)
        create_section_button.pack(padx=5, pady=5, fill=tk.X)


        # RadioBox for Fit curve
        fit_curve_label = tk.Label(right_frame, text="Fit Curve:")
        fit_curve_label.pack(padx=5, pady=(20, 5))

        self.fit_curve_var = tk.StringVar(value="Single Exp. Decay")
        fit_curve_options = ["Single Exp. Decay", "Double Exp. Decay", "Aux"]
        for option in fit_curve_options:
            rb = tk.Radiobutton(right_frame, text=option, variable=self.fit_curve_var, value=option)
            rb.pack(anchor='w', padx=20)

        # RadioBox for Display
        display_label = tk.Label(right_frame, text="Display:")
        display_label.pack(padx=5, pady=(20, 5))

        self.display_var = tk.StringVar(value="None")
        self.display_var.trace_add('write', self.on_display_option_changed)  # Use trace_add for modern Tkinter
        display_options = ["None", "Whole plot", "Just section"]
        for option in display_options:
            rb = tk.Radiobutton(right_frame, text=option, variable=self.display_var, value=option)
            rb.pack(anchor='w', padx=20)

        interpolate_button = tk.Button(right_frame, text="Interpolate Data", command=self.interpolate_data)
        interpolate_button.pack(padx=5, pady=5, fill=tk.X)

        filter_data_button = tk.Button(right_frame, text="Filter Data", command=self.filter_data)
        filter_data_button.pack(padx=5, pady=5, fill=tk.X)

        # Status bar at the bottom
        status_frame = tk.Frame(self, bd=1, relief=tk.SUNKEN)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # Create three labels within the status bar
        self.status_label_file = tk.Label(status_frame, text="No file loaded", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label_file.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_label_info = tk.Label(status_frame, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label_info.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Resize grip (the third section)
        self.status_resize_grip = ttk.Sizegrip(status_frame)
        self.status_resize_grip.pack(side=tk.RIGHT)

        # Table for Fitted Sections
        table_frame = tk.Frame(self)
        table_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        label = tk.Label(table_frame, text="Fitted Sections")
        label.pack(anchor='w')

        table_buttons = tk.Frame(table_frame)
        table_buttons.pack(side=tk.BOTTOM, fill=tk.X, expand=False)

        remove_section_button = tk.Button(table_buttons, text="Clear Sections", command=self.clear_all_sections)
        remove_section_button.pack(padx=5, pady=5,  side=tk.LEFT)

        remove_section_button = tk.Button(table_buttons, text="Remove Section", command=self.remove_section)
        remove_section_button.pack(padx=5, pady=5,  side=tk.LEFT)

        fit_selected_button = tk.Button(table_buttons, text="Fit Selected", command=self.fit_selected_section)
        fit_selected_button.pack(padx=5, pady=5, side=tk.LEFT)

        fit_all_button = tk.Button(table_buttons, text="Fit All Sections", command=self.fit_all_sections)
        fit_all_button.pack(padx=5, pady=5, side=tk.LEFT)

        copy_table_button = tk.Button(table_buttons, text="Copy All Fits", command=self.copy_whole_table)
        copy_table_button.pack(padx=5, pady=5, side=tk.RIGHT)

        self.tree = ttk.Treeview(table_frame, columns=self.columns, show='headings')
        self.tree.bind("<Double-1>", self.edit_section_on_double_click)

        self.tree = ttk.Treeview(table_frame, columns=self.columns, show='headings')
        self.tree.bind("<Double-1>", self.edit_section_on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_section_selected)

        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80, anchor=tk.CENTER)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add scrollbar
        scrollbar = tk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.tree.yview)

        # Modify the existing context menu creation
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy Selected Item", command=self.copy_selected_item)
        self.context_menu.add_command(label="Copy Whole Table", command=self.copy_whole_table)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def copy_selected_item(self):
        selected = self.tree.selection()
        if selected:
            items = []
            for sel in selected:
                item = self.tree.item(sel)
                items.append("\t".join(map(str, item['values'])))
            clipboard_text = "\n".join(items)
            self.clipboard_clear()
            self.clipboard_append(clipboard_text)
            self.update_status_info("Selected item(s) copied to clipboard.")
        else:
            self.update_status_info("No item selected to copy.")

    def copy_whole_table(self):
        items = []
        # Get column headers
        headers = [self.tree.heading(col)["text"] for col in self.tree["columns"]]
        items.append("\t".join(headers))
        # Get all rows
        for child in self.tree.get_children():
            item = self.tree.item(child)
            items.append("\t".join(map(str, item['values'])))
        clipboard_text = "\n".join(items)
        self.clipboard_clear()
        self.clipboard_append(clipboard_text)
        self.update_status_info("Whole table copied to clipboard.")

    def open_data(self):
        filepath = filedialog.askopenfilename(filetypes=[("Delimited files", "*.csv;*.txt"), ("All files", "*.*")])
        if filepath:
            loader = DataLoader()
            self.data = loader.load_xyc(filepath)
            if self.data is not None:
                self.plot_data()
                # self.add_cursors()
                self.clear_fits()
                self.loaded_filename = filepath  # Store the filename
                # Update the status bar with the file name
                self.status_label_file.config(text=f"Loaded file: {filepath}")
                self.update_status_info("Data loaded successfully.")
            else:
                self.update_status_info("Failed to load data. Check the file format.")

    def save_project(self):
        if self.fits:
            filepath = filedialog.asksaveasfilename(defaultextension=".dat", filetypes=[("DAT Files", "*.dat")])
            if filepath:
                try:
                    self.fitter.save_project(filepath, self.fits)
                    # Update status bar instead of message box
                    self.update_status_info("Project saved successfully.")
                except Exception as e:
                    self.update_status_info(f"Failed to save project: {e}")
        else:
            self.update_status_info("No fit data to save.")

    def export_plot(self):
        if self.data is not None:
            filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
            if filepath:
                try:
                    self.figure.savefig(filepath, dpi=200)  # Double resolution (standard 100 dpi)
                    # Update status bar instead of message box
                    self.update_status_info("Plot exported successfully.")
                except Exception as e:
                    self.update_status_info(f"Failed to export plot: {e}")
        else:
            self.update_status_info("No plot to export.")

    def export_fits(self):
        if self.fits:
            filepath = filedialog.asksaveasfilename(defaultextension=".csv",
                                                    filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xls;*.xlsx"),
                                                               ("All Files", "*.*")])
            if filepath:
                try:
                    self.fitter.export_fits(filepath, self.fits)
                    # Update status bar instead of message box
                    self.update_status_info("Fits exported successfully.")
                except Exception as e:
                    self.update_status_info(f"Failed to export fits: {e}")
        else:
            self.update_status_info("No fit data to export.")

    def plot_data(self):
        self.plot_axes.clear()
        try:
            self.plot_axes2.clear()
        except:
            self.plot_axes2 = self.plot_axes.twinx()

        self.plot_axes.plot(self.data['x'], self.data['y'], label=self.data['ylabel'], color='blue')
        self.plot_axes2.plot(self.data['x'], self.data['c'], label=self.data['zlabel'], color='green')

        self.plot_axes.set_xlabel(self.data['xlabel'])
        self.plot_axes.set_ylabel(self.data['ylabel'], color='blue')
        self.plot_axes2.set_ylabel(self.data['zlabel'], color='green')

        lines_1, labels_1 = self.plot_axes.get_legend_handles_labels()
        lines_2, labels_2 = self.plot_axes2.get_legend_handles_labels()
        self.plot_axes.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')

        # Re-plot knees and fits
        self.plot_knees()
        self.plot_fits()

        # Re-plot highlight rectangle
        if hasattr(self, 'highlight_rectangle') and self.highlight_rectangle is not None:
            from_x = self.highlight_rectangle.xy[0][0]
            to_x = self.highlight_rectangle.xy[2][0]
            self.highlight_rectangle = self.plot_axes.axvspan(
                from_x, to_x, color='yellow', alpha=0.3, zorder=0
            )

        self.canvas.draw()

    def crop_data(self):
        if self.cursor_A is not None and self.cursor_B is not None:
            A = min(self.cursor_A, self.cursor_B)
            B = max(self.cursor_A, self.cursor_B)
            if A == B:
                self.update_status_info("Cursor A and B positions are the same.")
                return

            # Create mask for cropping
            cropped_mask = (self.data['x'] >= A) & (self.data['x'] <= B)

            if not cropped_mask.any():
                self.update_status_info("No data in the selected range.")
                return

            # Ensure 'x', 'y', and 'c' have the same length before cropping
            if not (len(self.data['x']) == len(self.data['y']) == len(self.data['c'])):
                self.update_status_info("Data inconsistency before cropping.")
                return

            # Apply mask to 'x', 'y', and 'c'
            cropped_x = self.data['x'][cropped_mask] - A  # Shift 'x' to start at 0
            cropped_y = self.data['y'][cropped_mask]
            cropped_c = self.data['c'][cropped_mask]

            # Ensure the lengths match after cropping
            if not (len(cropped_x) == len(cropped_y) == len(cropped_c)):
                self.update_status_info("Data inconsistency after cropping.")
                return

            # Update the data
            self.data['x'] = cropped_x
            self.data['y'] = cropped_y
            self.data['c'] = cropped_c

            # Clear existing knees and sections
            self.knees = []
            self.sections = []
            self.clear_fits()
            self.refresh_table()

            # Add knees at the beginning and end
            new_start = self.data['x'].min()
            new_end = self.data['x'].max()
            self.knees.extend([new_start, new_end])
            self.knees = sorted(set(self.knees))  # Ensure knees are unique and sorted

            # Update the plot and cursors
            self.plot_data()
            self.plot_knees()
            # self.add_cursors()

            self.update_status_info(f"Data cropped from {A} to {B} with knees added at start and end.")
        else:
            self.update_status_info("Please select range using cursors A and B.")


    def fit_selected_section(self):
        selected_item = self.tree.selection()
        if selected_item:
            item_index = self.tree.index(selected_item[0])
            section = self.sections[item_index]
            self.fit_section(section, item_index)
            self.refresh_table()
            self.plot_fits()  # Update the fits on the plot
            self.update_status_info(f"Section {section['#']} fitted.")
        else:
            self.update_status_info("No section selected to fit.")

    def fit_all_sections(self):
        if not self.sections:
            self.update_status_info("No sections to fit.")
            return
        for idx, section in enumerate(self.sections):
            self.fit_section(section, idx)
        self.refresh_table()
        self.plot_fits()  # Plot fits after fitting all sections
        self.update_status_info("All sections have been fitted.")
    def update_status_info(self, message):
        """Update the status bar with the latest executed command."""
        self.status_label_info.config(text=message)

    def fit_section(self, section, idx):
        try:
            from_x = section["From"]
            to_x = section["To"]
            # Extract data for the current section
            mask = (self.data['x'] >= from_x) & (self.data['x'] <= to_x)
            x_data = self.data['x'][mask]
            y_data = self.data['y'][mask]

            if len(x_data) < 2:
                section["Comment"] = "Insufficient data"
                return

            x0 = x_data.min()
            fit_type = self.fit_curve_var.get()  # Use the selected fit type

            section["Type"] = fit_type

            if fit_type == "Single Exp. Decay":
                params = self.fitter.single_exp_decay(x_data, y_data, x0)
                if params is not None:
                    section["y0"], section["A1"], section["tau1"] = [f"{p:.3E}" for p in params]
                    section["A2"] = ""
                    section["tau2"] = ""
                else:
                    section["Comment"] = "error"
            elif fit_type == "Double Exp. Decay":
                params = self.fitter.double_exp_decay(x_data, y_data, x0)
                if params is not None:
                    section["y0"], section["A1"], section["tau1"], section["A2"], section["tau2"] = [
                        f"{p:.3E}" for p in params]
                    section["tau90"] = ""
                else:
                    section["Comment"] = "error"
            elif fit_type == "Aux":
                params = self.fitter.auxiliary(x_data, y_data, x0)
                if params is not None:
                    section["y0"], section["A1"] = [f"{p:.3E}" for p in params]
                    section["tau1"] = ""
                    section["A2"] = ""
                    section["tau2"] = ""
                    section["tau90"] = ""
                else:
                    section["Comment"] = "error"

            if ((idx+1) < len(self.sections)): #set prev_y0 for following section
                next_section = self.sections[idx+1]
                next_section["prev_y0"] = params[0]
            if (idx==0):  # first section does not have prev_y0
                section["prev_y0"] = y_data[0]

            self.fitter.calculate_t90(section)

        except Exception as e:
            section["Comment"] = f"Exception: {e}"

    def _add_cursors(self):
        """
        Removes existing cursor lines (A and B) from the plot and reinitializes the SpanSelector
        for selecting a new range.
        """
        # Remove existing cursor lines if they exist
        if hasattr(self, 'cursor_A') and self.cursor_A:
            self.cursor_A.remove()
            self.cursor_A = None
        if hasattr(self, 'cursor_B') and self.cursor_B:
            self.cursor_B.remove()
            self.cursor_B = None

        # Reinitialize SpanSelector for selecting new range
        self.span = SpanSelector(
            self.plot_axes,
            self.on_select,
            'horizontal',
            useblit=True,
            #rectprops=dict(alpha=0.5, facecolor='red')
        )
        self.canvas.draw()

    def on_select(self, xmin, xmax):
        # Remove old cursor lines
        if self.cursor_A_line:
            self.cursor_A_line.remove()
        if self.cursor_B_line:
            self.cursor_B_line.remove()

        # Add new vertical lines for cursors A and B
        self.cursor_A_line = self.plot_axes.axvline(
            x=xmin, color='red', linestyle='--'
        )
        self.cursor_B_line = self.plot_axes.axvline(
            x=xmax, color='red', linestyle='--'
        )

        self.cursor_A = xmin
        self.cursor_B = xmax

        # Redraw the canvas to show updated cursors
        self.canvas.draw()

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for section in self.sections:
            formatted_values = []
            for value, fmt in zip(section.values(), self.columns_formats):
                try:
                    if value == "" or value is None:
                        formatted_value = ""
                    else:
                        # Determine the appropriate type casting based on the format
                        if fmt == "{}":
                            # String format, no casting needed
                            formatted_value = fmt.format(value)
                        elif fmt == "{:d}":
                            # Integer format
                            formatted_value = fmt.format(int(float(value)))
                        else:
                            # Float format
                            formatted_value = fmt.format(float(value))
                except (ValueError, TypeError) as e:
                    # If formatting fails, use the original value as a string
                    formatted_value = str(value)
                formatted_values.append(formatted_value)
            self.tree.insert("", "end", values=formatted_values)

    def plot_fits(self):
        # Remove previous fit lines
        for line in self.plot_axes.lines[:]:
            if getattr(line, '_is_fit', False):
                line.remove()

        display_option = self.display_var.get()
        if display_option != "None":
            for section in self.sections:
                if section["Comment"] != "error":
                    from_x = section["From"]
                    to_x = section["To"]

                    if display_option == "Whole plot":
                        x_data_plot = self.data['x'][self.data['x'] >= from_x]
                    elif display_option == "Just section":
                        mask = (self.data['x'] >= from_x) & (self.data['x'] <= to_x)
                        x_data_plot = self.data['x'][mask]

                    fit_params = {k: float(section[k]) if section[k] else 0 for k in ["y0", "A1", "tau1", "A2", "tau2"]}
                    fit_type = section["Type"]
                    x0 = from_x  # Assuming x0 is from_x

                    fitted_curve = self.fitter.get_fit_curve(x_data_plot, fit_type, fit_params, x0)
                    line, = self.plot_axes.plot(x_data_plot, fitted_curve, linestyle=':')
                    line._is_fit = True  # Mark the line as a fit

        self.canvas.draw()

    def clear_fits(self):
        self.fits = []
        for line in self.plot_axes.lines[:]:
            if line.get_label().startswith('Fit Section'):
                line.remove()
        self.canvas.draw()

    def find_knees(self):
            # Placeholder method
        self.update_status_info("Find Knees functionality is currently a placeholder.")

    def edit_knees(self):
        # Format the current knees for display
        knees_str = ";".join(f"{knee:.2f}" for knee in self.knees)
        input_str = simpledialog.askstring("Edit Knees", "Enter x-coordinates separated by semicolons:",
                                           initialvalue=knees_str)
        if input_str is not None:
            try:
                new_knees = list(map(float, input_str.split(';')))
                new_knees = sorted(new_knees)
                self.knees = new_knees
                self.update_status_info("Knees updated.")
                # Optionally, replot the knees
                self.plot_knees()
            except Exception as e:
                self.update_status_info(f"Invalid input: {e}")
        else:
            self.update_status_info("Knees editing cancelled.")

    def plot_knees(self):
        # Remove existing knee markers and annotations
        # Remove lines
        for line in self.plot_axes.lines[:]:
            if getattr(line, '_is_knee', False):
                line.remove()

        # Remove annotations
        for annotation in self.knee_annotations:
            annotation.remove()
        self.knee_annotations.clear()

        # Plot new knees
        y_knees = [np.interp(x, self.data['x'], self.data['y']) for x in self.knees]
        for x, y in zip(self.knees, y_knees):
            line, = self.plot_axes.plot(x, y, 'o', color='darkgoldenrod', markersize=8)
            line._is_knee = True  # Mark the line as a knee
            annotation = self.plot_axes.annotate(f"{x:.2f}", (x, y))
            self.knee_annotations.append(annotation)

        self.canvas.draw()

    def remove_knees(self):
        if self.cursor_A is not None and self.cursor_B is not None:
            A = min(self.cursor_A, self.cursor_B)
            B = max(self.cursor_A, self.cursor_B)
            original_knee_count = len(self.knees)
            # Remove knees between A and B
            self.knees = [knee for knee in self.knees if not (A < knee < B)]
            removed_knee_count = original_knee_count - len(self.knees)
            self.update_status_info(f"Removed {removed_knee_count} knees between {A:.2f} and {B:.2f}.")
            # Update the plot
            self.plot_knees()
        else:
            self.update_status_info("Please select range using cursors A and B to remove knees.")

    def create_sections(self):
        if not self.knees:
            self.update_status_info("No knees defined to create sections.")
            return
        if len(self.knees) < 2:
            self.update_status_info("At least two knees are required to create sections.")
            return
        if len(self.sections):
            confirm = messagebox.askyesno("Confirm Replacing Current Sections",
                                      f"Are you sure you want to replace all currently set sections?")
            if not confirm:
                return
        # Clear existing sections
        self.sections = []
        # Create sections between knees
        for i in range(len(self.knees) - 1):
            section = {
                "#": i + 1,
                "From": self.knees[i],
                "To": self.knees[i + 1],
                "Type": "",
                "y0": "",
                "A1": "",
                "tau1": "",
                "A2": "",
                "tau2": "",
                "tau90": "",
                "Comment": ""
            }
            self.sections.append(section)
        self.refresh_table()
        self.update_status_info("Sections created between knees.")

    def create_section(self):
        if self.cursor_A is not None and self.cursor_B is not None:
            A = min(self.cursor_A, self.cursor_B)
            B = max(self.cursor_A, self.cursor_B)
            if A == B:
                self.update_status_info("Cursor A and B positions are the same.")
                return

            # Add knees at A and B if they are not already in the list
            self.knees.extend([A, B])
            self.knees = sorted(set(self.knees))  # Ensure knees are unique and sorted

            # Add a new section between A and B
            section_number = len(self.sections) + 1
            section = {
                "#": section_number,
                "From": A,
                "To": B,
                "Type": "",
                "y0": "",
                "A1": "",
                "tau1": "",
                "A2": "",
                "tau2": "",
                "tau90": "",
                "Comment": "",
                "prev_y0": ""
            }

            self.sections.append(section)
            self.update_section_comment_with_median_concentration(section)

            # Update the plot and table
            self.plot_knees()
            self.refresh_table()
            self.update_status_info(f"Section created between {A:.2f} and {B:.2f}.")
        else:
            self.update_status_info("Please select range using cursors A and B to create a section.")

    def remove_section(self):
        selected_item = self.tree.selection()
        if selected_item:
            item_index = self.tree.index(selected_item[0])
            section_number = self.sections[item_index]["#"]
            confirm = messagebox.askyesno("Confirm Deletion",
                                          f"Are you sure you want to remove section {section_number}?")
            if confirm:
                # Remove the section from the sections list
                del self.sections[item_index]
                # Update section numbers
                for idx, section in enumerate(self.sections):
                    section["#"] = idx + 1
                self.refresh_table()
                self.update_status_info(f"Section {section_number} removed.")
                self.plot_data()
        else:
            self.update_status_info("No section selected to remove.")

    def clear_all_sections(self):
        confirm = messagebox.askyesno("Confirm Deletion",
                                         f"Are you sure you want to remove all sections?")
        if confirm:
            # Remove the section from the sections list
            self.sections = []
            self.clear_fits()
            self.plot_data()
            self.refresh_table()
            self.update_status_info(f"All sections removed.")

    def interpolate_data(self):
        if self.cursor_A is not None and self.cursor_B is not None:
            A = min(self.cursor_A, self.cursor_B)
            B = max(self.cursor_A, self.cursor_B)
            if A == B:
                self.update_status_info("Cursor A and B positions are the same.")
                return
            mask = (self.data['x'] >= A) & (self.data['x'] <= B)
            if not mask.any():
                self.update_status_info("No data in the selected range.")
                return
            x_data = self.data['x'][mask]
            y_data = self.data['y']
            # Find y-values at A and B by interpolation
            y_A = np.interp(A, self.data['x'], self.data['y'])
            y_B = np.interp(B, self.data['x'], self.data['y'])
            # Linear interpolation
            y_interp = y_A + (y_B - y_A) * ((x_data - A) / (B - A))
            # Replace y_data in the selected range
            y_data[mask] = y_interp
            # Update the data
            self.data['y'] = y_data
            # Update the plot
            self.plot_data()
            self.update_status_info(f"Data interpolated between {A:.2f} and {B:.2f}.")
        else:
            self.update_status_info("Please select range using cursors A and B to interpolate.")

    def filter_data(self):
        dialog = tk.Toplevel(self)
        dialog.title("Filter Data")
        dialog.iconbitmap(self.dialog_icon)

        tk.Label(dialog, text="Filter Type:").grid(row=0, column=0, padx=10, pady=5, sticky='e')
        filter_type_var = tk.StringVar(value="Smooth")
        filter_type_combo = ttk.Combobox(dialog, textvariable=filter_type_var, values=["Smooth", "Median"],
                                         state='readonly')
        filter_type_combo.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Width:").grid(row=1, column=0, padx=10, pady=5, sticky='e')
        width_var = tk.IntVar(value=5)
        width_entry = tk.Entry(dialog, textvariable=width_var)
        width_entry.grid(row=1, column=1, padx=10, pady=5)

        def apply_filter():
            filter_type = filter_type_var.get()
            width = width_var.get()
            if width <= 0:
                messagebox.showerror("Invalid Width", "Width must be a positive integer.")
                return

            # Determine the range to apply the filter
            if self.cursor_A is not None and self.cursor_B is not None:
                A = min(self.cursor_A, self.cursor_B)
                B = max(self.cursor_A, self.cursor_B)
                mask = (self.data['x'] >= A) & (self.data['x'] <= B)
                if not mask.any():
                    self.update_status_info("No data in the selected range.")
                    dialog.destroy()
                    return
                y_data = self.data['y'][mask]
            else:
                # Apply to all data
                mask = slice(None)
                y_data = self.data['y']

            if filter_type == "Smooth":
                if width % 2 == 0:
                    width += 1  # Savitzky-Golay filter requires odd window length
                try:
                    filtered_y = savgol_filter(y_data, window_length=width, polyorder=2)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to apply smoothing filter: {e}")
                    dialog.destroy()
                    return
            elif filter_type == "Median":
                if width % 2 == 0:
                    width += 1  # Median filter requires odd window length
                try:
                    filtered_y = medfilt(y_data, kernel_size=width)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to apply median filter: {e}")
                    dialog.destroy()
                    return

            # Update the data
            self.data['y'][mask] = filtered_y

            # Update the plot
            self.plot_data()
            self.update_status_info(f"Applied {filter_type.lower()} filter with width {width}.")
            dialog.destroy()

        def cancel():
            dialog.destroy()
            self.update_status_info("Filter operation cancelled.")

        button_frame = tk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ok_button = tk.Button(button_frame, text="OK", command=apply_filter)
        ok_button.pack(side=tk.LEFT, padx=5)

        cancel_button = tk.Button(button_frame, text="Cancel", command=cancel)
        cancel_button.pack(side=tk.LEFT, padx=5)

        dialog.grab_set()
        self.wait_window(dialog)

    def on_display_option_changed(self, *args):
        self.plot_fits()

    def edit_section_on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        item_index = self.tree.index(item_id)
        section = self.sections[item_index]
        self.edit_section_dialog(section)

    def edit_section_dialog(self, section):
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Section {section['#']}")
        dialog.iconbitmap(self.dialog_icon)
        # Variables for From and To
        from_var = tk.DoubleVar(value=section['From'])
        to_var = tk.DoubleVar(value=section['To'])

        # Create labels and entries
        tk.Label(dialog, text="From:").grid(row=0, column=0, padx=10, pady=5, sticky='e')
        from_entry = tk.Entry(dialog, textvariable=from_var)
        from_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(dialog, text="To:").grid(row=1, column=0, padx=10, pady=5, sticky='e')
        to_entry = tk.Entry(dialog, textvariable=to_var)
        to_entry.grid(row=1, column=1, padx=10, pady=5)

        def save():
            try:
                from_value = float(from_var.get())
                to_value = float(to_var.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter numeric values for 'From' and 'To'.", parent=dialog)
                return

            # Validate the values
            if from_value >= to_value:
                messagebox.showerror("Invalid Input", "'From' value must be less than 'To' value.", parent=dialog)
                return
            data_min = self.data['x'].min()
            data_max = self.data['x'].max()
            if not (data_min <= from_value <= data_max) or not (data_min <= to_value <= data_max):
                messagebox.showerror("Invalid Input", f"'From' and 'To' values must be within data range. ({data_min}, {data_max})",
                                     parent=dialog)
                return

            # Update the section
            section['From'] = from_value
            section['To'] = to_value

            # Recalculate knees based on updated sections
            self.knees = []
            for sec in self.sections:
                self.knees.extend([sec['From'], sec['To']])
            self.knees = sorted(set(self.knees))

            # Update the plot and table
            self.plot_knees()

            self.update_section_comment_with_median_concentration(section)

            self.refresh_table()
            self.update_status_info(f"Section {section['#']} updated.")
            dialog.destroy()

        def cancel():
            dialog.destroy()

        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        save_button = tk.Button(button_frame, text="Save", command=save)
        save_button.pack(side=tk.LEFT, padx=5)

        cancel_button = tk.Button(button_frame, text="Cancel", command=cancel)
        cancel_button.pack(side=tk.LEFT, padx=5)

        # Set focus to the dialog
        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)

    def on_section_selected(self, event):
        # Remove existing highlight rectangle if it exists
        if hasattr(self, 'highlight_rectangle') and self.highlight_rectangle is not None:
            self.highlight_rectangle.remove()
            self.highlight_rectangle = None

        selected_item = self.tree.selection()

        if selected_item:
            item_index = self.tree.index(selected_item[0])
            section = self.sections[item_index]
            from_x = section["From"]
            to_x = section["To"]

            # Add rectangle to highlight the selected section
            self.highlight_rectangle = self.plot_axes.axvspan(
                from_x, to_x, color='yellow', alpha=0.3, zorder=0
            )

        # Redraw the canvas to show updates
        self.canvas.draw()

    def update_section_comment_with_median_concentration(self, section):
        """
        Calculates the median concentration within the section's range
        and updates the 'Comment' field of the section.
        """
        from_x = section['From']
        to_x = section['To']
        # Ensure 'c' data exists
        if 'c' in self.data:
            mask = (self.data['x'] >= from_x) & (self.data['x'] <= to_x)
            if mask.any():
                c_data = self.data['c'][mask]
                # Calculate median concentration
                concentration_median = np.median(c_data)
                # Update the 'Comment' field
                section['Comment'] = f"{concentration_median:.0f} ppm"
            else:
                section['Comment'] = "err."
        else:
            section['Comment'] = " "