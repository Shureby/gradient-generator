import tkinter as tk
from tkinter import ttk, colorchooser, filedialog
from PIL import Image, ImageDraw, ImageTk
LANCZOS: int
try:
    # For newer Pillow versions (9.0.0 and above)
    from PIL.Image import Resampling
    LANCZOS = Resampling.LANCZOS
except ImportError:
    # For older Pillow versions
    import warnings
    warnings.warn(
        "Using deprecated `Image.LANCZOS`. Upgrade Pillow to 9.0.0 or newer: pip install --upgrade pillow",
        DeprecationWarning,
        stacklevel=2
    )
    LANCZOS = Image.LANCZOS  # type: ignore
import colorsys
import random
import numpy as np
import threading
import queue
import time

class GradientImageGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Gradient Image Generator")
        self.root.geometry("800x600")
        
        # Set window icon
        try:
            # Try PNG icon first, then SVG as fallback
            icon_paths = ["icon/app_icon.png", "icon/app_icon.svg"]
            icon_loaded = False
            
            for icon_path in icon_paths:
                try:
                    icon_image = Image.open(icon_path)
                    icon_photo = ImageTk.PhotoImage(icon_image)
                    self.root.iconphoto(True, icon_photo)
                    # Keep a reference to prevent garbage collection
                    self.icon_photo = icon_photo
                    icon_loaded = True
                    break
                except Exception:
                    continue
            
            if not icon_loaded:
                raise Exception("No valid icon found")
                
        except Exception as e:
            print(f"Failed to load icon: {e}")
        
        # Default values
        self.primary_color = "#c5022f"
        self.secondary_color = "#8ef9e0"
        self.gradient_type = "linear"
        self.direction = "top-left-to-bottom-right"
        self.position = "center"  # Default position for radial gradient
        self.width = 1024
        self.height = 1024
        self.aspect_ratio = "1:1"  # Default aspect ratio
        
        # For preview scaling
        self.preview_max_width = 400
        self.preview_max_height = 400
        self.zoom_factor = 1.0  # Default zoom factor for preview
        
        # For asynchronous image generation
        self.image_queue = queue.Queue()
        self.preview_queue = queue.Queue()
        self.is_generating = False
        self.generation_thread = None
        self.gradient_image = None
        self.progress_value = 0
        
        # Store references to PhotoImage objects to prevent garbage collection
        self.photo_images = []
        
        self.create_widgets()
        self.update_preview()
        
        # Bind window resize event to update preview
        self.root.bind("<Configure>", self._on_window_resize)
        
        # Start the queue checker
        self.check_queue()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for controls
        control_frame = ttk.Frame(main_frame, padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # Primary Color
        ttk.Label(control_frame, text="Primary Color").grid(row=0, column=0, sticky=tk.W, pady=5)
        primary_frame = ttk.Frame(control_frame)
        primary_frame.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        self.primary_entry = ttk.Entry(primary_frame, width=10)
        self.primary_entry.insert(0, self.primary_color)
        self.primary_entry.pack(side=tk.LEFT)
        self.primary_entry.bind("<KeyRelease>", self._on_primary_color_change)
        
        self.primary_button = ttk.Button(primary_frame, text="Choose", command=self.choose_primary)
        self.primary_button.pack(side=tk.LEFT, padx=5)
        
        self.primary_random = ttk.Button(primary_frame, text="Random", command=self.random_primary)
        self.primary_random.pack(side=tk.LEFT)
        
        # Primary color preview box
        self.primary_preview = tk.Label(primary_frame, width=3, height=1)
        self.primary_preview.pack(side=tk.LEFT, padx=5)
        self._update_primary_preview(self.primary_color)
        
        # Secondary Color
        ttk.Label(control_frame, text="Secondary Color").grid(row=1, column=0, sticky=tk.W, pady=5)
        secondary_frame = ttk.Frame(control_frame)
        secondary_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        self.secondary_entry = ttk.Entry(secondary_frame, width=10)
        self.secondary_entry.insert(0, self.secondary_color)
        self.secondary_entry.pack(side=tk.LEFT)
        self.secondary_entry.bind("<KeyRelease>", self._on_secondary_color_change)
        
        self.secondary_button = ttk.Button(secondary_frame, text="Choose", command=self.choose_secondary)
        self.secondary_button.pack(side=tk.LEFT, padx=5)
        
        self.secondary_random = ttk.Button(secondary_frame, text="Random", command=self.random_secondary)
        self.secondary_random.pack(side=tk.LEFT)
        
        # Secondary color preview box
        self.secondary_preview = tk.Label(secondary_frame, width=3, height=1)
        self.secondary_preview.pack(side=tk.LEFT, padx=5)
        self._update_secondary_preview(self.secondary_color)
        
        # Gradient Type
        ttk.Label(control_frame, text="Gradient Type").grid(row=2, column=0, sticky=tk.W, pady=5)
        gradient_frame = ttk.Frame(control_frame)
        gradient_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        self.gradient_var = tk.StringVar(value=self.gradient_type)
        ttk.Radiobutton(gradient_frame, 
                        text="Linear Gradient", 
                        variable=self.gradient_var, 
                        value="linear", 
                        command=self.update_preview).pack(anchor=tk.W)
        ttk.Radiobutton(gradient_frame, 
                        text="Radial Gradient", 
                        variable=self.gradient_var, 
                        value="radial", 
                        command=self.update_preview).pack(anchor=tk.W)
        
        # Direction (for linear gradient)
        self.direction_label = ttk.Label(control_frame, text="Direction")
        self.direction_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        self.direction_var = tk.StringVar(value=self.direction)
        self.direction_combo = ttk.Combobox(control_frame, textvariable=self.direction_var, state="readonly")
        self.direction_combo['values'] = (
            "left-to-right",
            "right-to-left",
            "top-to-bottom",
            "bottom-to-top",
            "top-left-to-bottom-right",
            "top-right-to-bottom-left",
            "bottom-left-to-top-right",
            "bottom-right-to-top-left"
        )
        self.direction_combo.grid(row=3, column=1, sticky=tk.W, pady=5)
        self.direction_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())
        
        # Position (for radial gradient)
        self.position_label = ttk.Label(control_frame, text="Position")
        self.position_label.grid(row=4, column=0, sticky=tk.W, pady=5)
        self.position_var = tk.StringVar(value=self.position)
        self.position_combo = ttk.Combobox(control_frame, textvariable=self.position_var, state="readonly")
        self.position_combo['values'] = (
            "center",
            "top",
            "top-right",
            "right",
            "bottom-right",
            "bottom",
            "bottom-left",
            "left",
            "top-left"
        )
        self.position_combo.grid(row=4, column=1, sticky=tk.W, pady=5)
        self.position_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())
        
        # Show/hide direction and position based on gradient type
        self._toggle_controls()
        
        # Image Size
        ttk.Label(control_frame, text="Image Size (in pixels)").grid(row=5, column=0, sticky=tk.W, pady=5)
        size_frame = ttk.Frame(control_frame)
        size_frame.grid(row=5, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(size_frame, text="Width:").pack(side=tk.LEFT)
        self.width_entry = ttk.Entry(size_frame, width=6)
        self.width_entry.insert(0, str(self.width))
        self.width_entry.pack(side=tk.LEFT, padx=5)
        self.width_entry.bind("<KeyRelease>", self._on_width_change)
        
        ttk.Label(size_frame, text="Height:").pack(side=tk.LEFT, padx=5)
        self.height_entry = ttk.Entry(size_frame, width=6)
        self.height_entry.insert(0, str(self.height))
        self.height_entry.pack(side=tk.LEFT)
        self.height_entry.bind("<KeyRelease>", self._on_height_change)
        
        # Swap button
        self.swap_button = ttk.Button(size_frame, text="Swap", command=self.swap_dimensions)
        self.swap_button.pack(side=tk.LEFT, padx=5)
        
        # Aspect Ratio
        ttk.Label(control_frame, text="Aspect Ratio").grid(row=6, column=0, sticky=tk.W, pady=5)
        ratio_frame = ttk.Frame(control_frame)
        ratio_frame.grid(row=6, column=1, sticky=tk.W, pady=5)
        
        self.ratio_var = tk.StringVar(value=self.aspect_ratio)
        self.ratio_combo = ttk.Combobox(ratio_frame, textvariable=self.ratio_var, state="readonly", width=10)
        self.ratio_combo['values'] = (
            "Custom",
            "1:1",
            "4:3",
            "3:4",
            "16:9",
            "9:16",
            "2:1",
            "1:2",
            "3:2",
            "2:3"
        )
        self.ratio_combo.pack(side=tk.LEFT)
        self.ratio_combo.bind("<<ComboboxSelected>>", self._on_ratio_change)
        
        # Zoom control for preview
        ttk.Label(control_frame, text="Preview Zoom").grid(row=7, column=0, sticky=tk.W, pady=5)
        zoom_frame = ttk.Frame(control_frame)
        zoom_frame.grid(row=7, column=1, sticky=tk.W, pady=5)
        
        # Zoom slider
        self.zoom_var = tk.DoubleVar(value=self.zoom_factor)
        self.zoom_slider = ttk.Scale(zoom_frame, from_=0.5, to=2.0, orient=tk.HORIZONTAL, 
                                    variable=self.zoom_var, length=150, command=self._on_zoom_change)
        self.zoom_slider.pack(side=tk.LEFT)
        
        # Zoom percentage label
        self.zoom_label = ttk.Label(zoom_frame, text="100%")
        self.zoom_label.pack(side=tk.LEFT, padx=5)
        
        # CSS code display
        ttk.Label(control_frame, text="CSS code").grid(row=8, column=0, sticky=tk.W, pady=5)
        self.css_text = tk.Text(control_frame, height=3, width=40)
        self.css_text.grid(row=8, column=1, sticky=tk.W, pady=5)
        
        # Progress bar for image generation
        ttk.Label(control_frame, text="Generation Progress").grid(row=9, column=0, sticky=tk.W, pady=5)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=9, column=1, sticky=tk.EW, pady=5)
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Ready")
        self.status_label.grid(row=10, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Update and Save buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=11, column=0, columnspan=2, pady=10)
        
        self.update_button = ttk.Button(button_frame, text="Update Preview", command=self.update_preview)
        self.update_button.pack(side=tk.LEFT, padx=5)
        
        self.save_png_button = ttk.Button(button_frame, text="Save PNG", command=self.save_png)
        self.save_png_button.pack(side=tk.LEFT, padx=5)
        
        self.save_jpg_button = ttk.Button(button_frame, text="Save JPG", command=self.save_jpg)
        self.save_jpg_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.cancel_generation, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        # Preview frame
        self.preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding=10)
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.preview_label = ttk.Label(self.preview_frame)
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        # Add a minimum size to the preview frame
        self.preview_frame.update_idletasks()
        min_width = 300
        min_height = 300
        self.preview_frame.config(width=min_width, height=min_height)
    
    def choose_primary(self):
        color = colorchooser.askcolor(initialcolor=self.primary_color)[1]
        if color:
            self.primary_color = color
            self.primary_entry.delete(0, tk.END)
            self.primary_entry.insert(0, color)
            self._update_primary_preview(color)
            self.update_preview()
    
    def choose_secondary(self):
        color = colorchooser.askcolor(initialcolor=self.secondary_color)[1]
        if color:
            self.secondary_color = color
            self.secondary_entry.delete(0, tk.END)
            self.secondary_entry.insert(0, color)
            self._update_secondary_preview(color)
            self.update_preview()
    
    def random_primary(self):
        self.primary_color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        self.primary_entry.delete(0, tk.END)
        self.primary_entry.insert(0, self.primary_color)
        self._update_primary_preview(self.primary_color)
        self.update_preview()
    
    def random_secondary(self):
        self.secondary_color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        self.secondary_entry.delete(0, tk.END)
        self.secondary_entry.insert(0, self.secondary_color)
        self._update_secondary_preview(self.secondary_color)
        self.update_preview()
    
    def _on_gradient_type_change(self):
        self.gradient_type = self.gradient_var.get()
        self._toggle_controls()
        self.update_preview()
    
    def _toggle_controls(self):
        if self.gradient_type == "linear":
            self.direction_label.grid(row=3, column=0, sticky=tk.W, pady=5)
            self.direction_combo.grid(row=3, column=1, sticky=tk.W, pady=5)
            self.position_label.grid_remove()
            self.position_combo.grid_remove()
        else:  # radial
            self.direction_label.grid_remove()
            self.direction_combo.grid_remove()
            self.position_label.grid(row=3, column=0, sticky=tk.W, pady=5)
            self.position_combo.grid(row=3, column=1, sticky=tk.W, pady=5)
    
    def _update_primary_preview(self, color):
        try:
            if hasattr(self, 'primary_preview'):
                self.primary_preview.config(bg=color)
        except tk.TclError:
            # Invalid color format
            pass
    
    def _update_secondary_preview(self, color):
        try:
            if hasattr(self, 'secondary_preview'):
                self.secondary_preview.config(bg=color)
        except tk.TclError:
            # Invalid color format
            pass
    
    def _on_primary_color_change(self, event):
        color = self.primary_entry.get()
        if color.startswith('#') and (len(color) == 7 or len(color) == 4):
            self._update_primary_preview(color)
            self.update_preview()
    
    def _on_secondary_color_change(self, event):
        color = self.secondary_entry.get()
        if color.startswith('#') and (len(color) == 7 or len(color) == 4):
            self._update_secondary_preview(color)
            self.update_preview()
    
    def _on_width_change(self, event):
        try:
            new_width = int(self.width_entry.get())
            if new_width > 0 and self.ratio_var.get() != "Custom":
                # Calculate new height based on aspect ratio
                ratio_parts = self.ratio_var.get().split(":")
                width_ratio = int(ratio_parts[0])
                height_ratio = int(ratio_parts[1])
                new_height = int(new_width * height_ratio / width_ratio)
                
                # Update height entry
                self.height_entry.delete(0, tk.END)
                self.height_entry.insert(0, str(new_height))
        except ValueError:
            # Invalid input, ignore
            pass
    
    def _on_height_change(self, event):
        try:
            new_height = int(self.height_entry.get())
            if new_height > 0 and self.ratio_var.get() != "Custom":
                # Calculate new width based on aspect ratio
                ratio_parts = self.ratio_var.get().split(":")
                width_ratio = int(ratio_parts[0])
                height_ratio = int(ratio_parts[1])
                new_width = int(new_height * width_ratio / height_ratio)
                
                # Update width entry
                self.width_entry.delete(0, tk.END)
                self.width_entry.insert(0, str(new_width))
        except ValueError:
            # Invalid input, ignore
            pass
    
    def _on_ratio_change(self, event):
        selected_ratio = self.ratio_var.get()
        if selected_ratio != "Custom":
            try:
                current_width = int(self.width_entry.get())
                if current_width > 0:
                    # Calculate new height based on selected aspect ratio
                    ratio_parts = selected_ratio.split(":")
                    width_ratio = int(ratio_parts[0])
                    height_ratio = int(ratio_parts[1])
                    new_height = int(current_width * height_ratio / width_ratio)
                    
                    # Update height entry
                    self.height_entry.delete(0, tk.END)
                    self.height_entry.insert(0, str(new_height))
                    self.update_preview()
            except ValueError:
                # Invalid input, ignore
                pass
    
    def swap_dimensions(self):
        # Get current width and height
        try:
            current_width = self.width_entry.get()
            current_height = self.height_entry.get()
            
            # Swap values
            self.width_entry.delete(0, tk.END)
            self.width_entry.insert(0, current_height)
            
            self.height_entry.delete(0, tk.END)
            self.height_entry.insert(0, current_width)
            
            # Set ratio to Custom
            self.ratio_var.set("Custom")
            
            # Update preview
            self.update_preview()
        except:
            # Error handling
            pass
    
    def _on_window_resize(self, event):
        # Only respond to the root window resize events
        if event.widget == self.root:
            # Store current window dimensions to avoid unnecessary updates
            current_width = self.root.winfo_width()
            current_height = self.root.winfo_height()
            
            # Only update if the size has changed significantly (more than 10 pixels)
            if not hasattr(self, '_last_window_size') or \
               abs(self._last_window_size[0] - current_width) > 10 or \
               abs(self._last_window_size[1] - current_height) > 10:
                # Store the new size
                self._last_window_size = (current_width, current_height)
                # Update the preview after a short delay to avoid too many updates
                self.root.after(100, self.update_preview)
            
    def check_queue(self):
        """Check if there are any images in the queue and update the UI"""
        try:
            # Check for completed full-size images
            while not self.image_queue.empty():
                image, is_preview = self.image_queue.get_nowait()
                if not is_preview:
                    self.gradient_image = image
                    self.is_generating = False
                    self.enable_controls()
                    self.status_label.config(text="Generation Completed")
                    self.progress_var.set(100)
                    
                    # Hide the progress bar and its label after generation is complete
                    for widget in self.root.winfo_children():
                        if isinstance(widget, ttk.Frame):
                            for child in widget.winfo_children():
                                if isinstance(child, ttk.Frame):
                                    for grandchild in child.winfo_children():
                                        if isinstance(grandchild, ttk.Label) and grandchild.cget("text") == "Generation Progress":
                                            grandchild.grid_remove()
                                            # Also hide the progress bar which is at the same row
                                            for sibling in grandchild.master.winfo_children():
                                                if isinstance(sibling, ttk.Progressbar):
                                                    sibling.grid_remove()
                    
                    # Update preview with the new full image
                    preview_width, preview_height = self._calculate_preview_size()
                    # Use high-quality downsampling with antialiasing
                    preview_image = self.gradient_image.resize((preview_width, preview_height), LANCZOS)
                    
                    # Clear old photo images to prevent memory issues
                    if len(self.photo_images) > 10:  # Keep only the last 10 images
                        self.photo_images = self.photo_images[-10:]
                    
                    # Create new PhotoImage and store reference
                    photo_image = ImageTk.PhotoImage(preview_image)
                    self.photo_images.append(photo_image)  # Store reference to prevent garbage collection
                    self.preview_label.config(image=photo_image)
                    
                    # Update CSS code
                    self.update_css_code()
            
            # Check for preview updates
            while not self.preview_queue.empty():
                try:
                    progress, preview_image = self.preview_queue.get_nowait()
                    if preview_image:
                        # Ensure the preview image is properly sized
                        preview_width, preview_height = self._calculate_preview_size()
                        # Resize if the dimensions don't match (could happen during window resize)
                        if (preview_image.width, preview_image.height) != (preview_width, preview_height):
                            preview_image = preview_image.resize((preview_width, preview_height), LANCZOS)
                        
                        # Clear old photo images to prevent memory issues
                        if len(self.photo_images) > 10:  # Keep only the last 10 images
                            self.photo_images = self.photo_images[-10:]
                        
                        # Create new PhotoImage and store reference
                        photo_image = ImageTk.PhotoImage(preview_image)
                        self.photo_images.append(photo_image)  # Store reference to prevent garbage collection
                        self.preview_label.config(image=photo_image)
                    self.progress_var.set(progress)
                    
                    # Only update status text if we're still generating
                    # This prevents overwriting the "Generation Completed" message
                    if self.is_generating:
                        self.status_label.config(text=f"Generating... {int(progress)}%")
                except Exception as e:
                    print(f"Error processing preview image: {e}")
        except Exception as e:
            print(f"Error in queue processing: {e}")
        
        # Schedule the next queue check
        self.root.after(100, self.check_queue)
        
    def disable_controls(self):
        """Disable controls during image generation"""
        self.update_button.config(state=tk.DISABLED)
        self.save_png_button.config(state=tk.DISABLED)
        self.save_jpg_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        
    def enable_controls(self):
        """Enable controls after image generation"""
        self.update_button.config(state=tk.NORMAL)
        self.save_png_button.config(state=tk.NORMAL)
        self.save_jpg_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        
    def cancel_generation(self):
        """Cancel the current image generation process"""
        if self.is_generating and self.generation_thread and self.generation_thread.is_alive():
            self.is_generating = False
            self.status_label.config(text="Generation cancelled")
            self.enable_controls()
            # Thread will terminate on its own by checking self.is_generating
    
    def _calculate_preview_size(self):
        # Get the available size for the preview
        self.preview_frame.update_idletasks()
        
        # Get the available width and height for the preview
        available_width = self.preview_frame.winfo_width() - 20  # Subtract padding
        available_height = self.preview_frame.winfo_height() - 20  # Subtract padding
        
        # Ensure we have valid dimensions (minimum size)
        available_width = max(200, available_width)
        available_height = max(200, available_height)
        
        # Also cap at maximum size to prevent excessive memory usage
        available_width = min(self.preview_max_width, available_width)
        available_height = min(self.preview_max_height, available_height)
        
        # Calculate the scaling factors for width and height
        width_scale = available_width / self.width
        height_scale = available_height / self.height
        
        # Use the smaller scaling factor to ensure the image fits within the preview area
        scale_factor = min(width_scale, height_scale)
        
        # Apply the zoom factor
        scale_factor *= self.zoom_factor
        
        # Calculate the new dimensions - ensure they're at least 1 pixel
        # Use math.ceil to avoid zero-sized dimensions and ensure complete coverage
        import math
        preview_width = max(1, math.ceil(self.width * scale_factor))
        preview_height = max(1, math.ceil(self.height * scale_factor))
        
        return preview_width, preview_height
        
    def _on_zoom_change(self, event):
        # Update the zoom factor
        self.zoom_factor = self.zoom_var.get()
        
        # Update the zoom label
        zoom_percentage = int(self.zoom_factor * 100)
        self.zoom_label.config(text=f"{zoom_percentage}%")
        
        # Update the preview
        self.update_preview()
    
    def update_preview(self):
        # Get current values from UI
        new_primary_color = self.primary_entry.get()
        new_secondary_color = self.secondary_entry.get()
        new_gradient_type = self.gradient_var.get()
        new_direction = self.direction_var.get()
        new_position = self.position_var.get()
        
        try:
            new_width = int(self.width_entry.get())
            new_height = int(self.height_entry.get())
        except ValueError:
            # Use default values if invalid input
            new_width = 2000
            new_height = 3000
        
        # Check if we're already generating an image
        if self.is_generating:
            self.status_label.config(text="Already generating an image, please wait or cancel")
            return
            
        # Check if any parameters have changed since last generation
        if (self.gradient_image is not None and 
            new_primary_color == self.primary_color and 
            new_secondary_color == self.secondary_color and 
            new_gradient_type == self.gradient_type and 
            new_direction == self.direction and 
            new_position == self.position and 
            new_width == self.width and 
            new_height == self.height):
            # No changes, just update the CSS code and return
            self.update_css_code()
            return
        
        # Update instance variables with new values
        self.primary_color = new_primary_color
        self.secondary_color = new_secondary_color
        self.gradient_type = new_gradient_type
        self.direction = new_direction
        self.position = new_position
        self.width = new_width
        self.height = new_height
        
        # Update status
        self.is_generating = True
        self.progress_var.set(0)
        self.status_label.config(text="Starting generation...")
        self.disable_controls()
        
        # First generate a small preview quickly
        preview_width, preview_height = self._calculate_preview_size()
        
        # Start a thread for image generation
        self.generation_thread = threading.Thread(
            target=self._generate_image_async, 
            args=(self.width, self.height, preview_width, preview_height)
        )
        self.generation_thread.daemon = True
        self.generation_thread.start()
        
        # Update CSS code immediately
        self.update_css_code()
    
    def _generate_image_async(self, width, height, preview_width, preview_height):
        """Generate the gradient image in a separate thread with progress updates"""
        try:
            # First generate a small preview quickly - generate at slightly higher resolution
            # to ensure quality, then resize down to the exact preview size
            preview_scale = 1.5  # Generate at 1.5x the needed size for better quality
            temp_preview_width = int(preview_width * preview_scale)
            temp_preview_height = int(preview_height * preview_scale)
            
            # Generate high-quality preview
            preview_image = self.create_gradient_image(temp_preview_width, temp_preview_height, is_preview=True)
            # Resize to exact preview dimensions with high-quality downsampling
            preview_image = preview_image.resize((preview_width, preview_height), LANCZOS)
            
            # Put a copy of the PIL Image in the queue, not the PhotoImage
            # PhotoImage objects should only be created in the main thread
            self.preview_queue.put((10, preview_image.copy()))
            
            # Generate the full image in one go, without blocks
            # Check if generation was cancelled before starting
            if not self.is_generating:
                return
                
            # Update progress to indicate we're starting the main generation
            self.preview_queue.put((20, None))
            
            # For large images, we'll still provide progress updates during generation
            # by updating the preview at regular intervals
            is_large_image = width * height > 1000000  # If image is larger than ~1 megapixel
            
            # Generate the full image at once
            full_image = self.create_gradient_image(width, height, is_preview=False)
            
            # Check if generation was cancelled after creating the image
            if not self.is_generating:
                return
                
            # For large images, provide a progress update with the completed image
            if is_large_image:
                # Create a preview of the completed image
                preview = full_image.resize((preview_width, preview_height), LANCZOS)
                # Put a copy of the PIL Image in the queue with 90% progress
                self.preview_queue.put((90, preview.copy()))
                
                # Give the main thread a chance to process
                time.sleep(0.01)
            else:
                # For smaller images, just update to 90% progress
                self.preview_queue.put((90, None))
            
            # Update progress to 100% before putting the completed image in the queue
            self.preview_queue.put((100, None))
            
            # Put the completed image in the queue
            self.image_queue.put((full_image, False))
        
        except Exception as e:
            print(f"Error in image generation: {e}")
            self.status_label.config(text=f"Error: {e}")
            self.is_generating = False
            self.enable_controls()
    
    def create_gradient_image(self, width, height, is_preview=False):
        """Create a gradient image with the specified dimensions
        
        Args:
            width: Image width
            height: Image height
            is_preview: Whether this is a preview image (lower quality for speed)
        """
        # Parse colors once
        r1, g1, b1 = int(self.primary_color[1:3], 16), int(self.primary_color[3:5], 16), int(self.primary_color[5:7], 16)
        r2, g2, b2 = int(self.secondary_color[1:3], 16), int(self.secondary_color[3:5], 16), int(self.secondary_color[5:7], 16)
        
        # Create numpy arrays for the RGB channels
        rgb_array = np.zeros((height, width, 3), dtype=np.uint8)
        
        if self.gradient_type == "linear":
            # Create coordinate arrays
            y_coords, x_coords = np.mgrid[0:height, 0:width]
            
            # Calculate the ratio based on direction using vectorized operations
            if self.direction == "left-to-right":
                ratio = x_coords / width
            elif self.direction == "right-to-left":
                ratio = 1 - (x_coords / width)
            elif self.direction == "top-to-bottom":
                ratio = y_coords / height
            elif self.direction == "bottom-to-top":
                ratio = 1 - (y_coords / height)
            elif self.direction == "top-left-to-bottom-right":
                ratio = (x_coords / width + y_coords / height) / 2
            elif self.direction == "top-right-to-bottom-left":
                ratio = ((width - x_coords) / width + y_coords / height) / 2
            elif self.direction == "bottom-left-to-top-right":
                ratio = (x_coords / width + (height - y_coords) / height) / 2
            elif self.direction == "bottom-right-to-top-left":
                ratio = ((width - x_coords) / width + (height - y_coords) / height) / 2
            else:
                ratio = (x_coords / width + y_coords / height) / 2  # Default
            
            # Interpolate between colors using vectorized operations
            r = (r1 * (1 - ratio) + r2 * ratio).astype(np.uint8)
            g = (g1 * (1 - ratio) + g2 * ratio).astype(np.uint8)
            b = (b1 * (1 - ratio) + b2 * ratio).astype(np.uint8)
            
            # Assign the RGB values to the array
            rgb_array[..., 0] = r
            rgb_array[..., 1] = g
            rgb_array[..., 2] = b
        else:
            # Radial gradient using vectorized operations
            # Set center point based on position
            if self.position == "center":
                center_x, center_y = width // 2, height // 2
            elif self.position == "top":
                center_x, center_y = width // 2, 0
            elif self.position == "top-right":
                center_x, center_y = width, 0
            elif self.position == "right":
                center_x, center_y = width, height // 2
            elif self.position == "bottom-right":
                center_x, center_y = width, height
            elif self.position == "bottom":
                center_x, center_y = width // 2, height
            elif self.position == "bottom-left":
                center_x, center_y = 0, height
            elif self.position == "left":
                center_x, center_y = 0, height // 2
            elif self.position == "top-left":
                center_x, center_y = 0, 0
            else:  # Default to center
                center_x, center_y = width // 2, height // 2
                
            max_dist = (width**2 + height**2)**0.5 / 2
            
            # Create coordinate arrays
            y_coords, x_coords = np.mgrid[0:height, 0:width]
            
            # Calculate distances from center
            dist = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
            ratio = np.minimum(1.0, dist / max_dist)
            
            # Interpolate between colors using vectorized operations
            r = (r1 * (1 - ratio) + r2 * ratio).astype(np.uint8)
            g = (g1 * (1 - ratio) + g2 * ratio).astype(np.uint8)
            b = (b1 * (1 - ratio) + b2 * ratio).astype(np.uint8)
            
            # Assign the RGB values to the array
            rgb_array[..., 0] = r
            rgb_array[..., 1] = g
            rgb_array[..., 2] = b
        
        # Convert the numpy array to a PIL Image
        image = Image.fromarray(rgb_array)
        
        return image
    
    def update_css_code(self):
        if self.gradient_type == "linear":
            direction_css = {
                "left-to-right": "to right",
                "top-to-bottom": "to bottom",
                "top-left-to-bottom-right": "135deg",
                "top-right-to-bottom-left": "225deg"
            }.get(self.direction, "135deg")
            
            css = f"background: linear-gradient({direction_css}, {self.primary_color} 0%, {self.secondary_color} 100%);"
        else:
            # Map position to CSS position
            position_css = {
                "center": "center",
                "top": "top",
                "top-right": "top right",
                "right": "right",
                "bottom-right": "bottom right",
                "bottom": "bottom",
                "bottom-left": "bottom left",
                "left": "left",
                "top-left": "top left"
            }.get(self.position, "center")
            
            css = f"background: radial-gradient(circle at {position_css}, {self.primary_color} 0%, {self.secondary_color} 100%);"
        
        self.css_text.delete(1.0, tk.END)
        self.css_text.insert(tk.END, css)
    
    def save_png(self):
        # Check if we have a valid image to save
        if self.is_generating:
            self.status_label.config(text="Cannot save while generating image")
            return
        if self.gradient_image is None:
            self.status_label.config(text="No image to save")
            return
            
        color1 = self.primary_color[1:]  # Remove '#'
        color2 = self.secondary_color[1:]  # Remove '#'
        gradient_type = "lg" if self.gradient_type == "linear" else "rg"
        default_name = f"{color1}-{color2}_{gradient_type}_{self.width}x{self.height}.png"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            title="Save PNG Image",
            initialfile=default_name
        )
        if file_path:
            try:
                self.status_label.config(text="Saving PNG...")
                # Store current image before saving
                current_image = self.gradient_image
                current_image.save(file_path, "PNG")
                self.status_label.config(text="The file has been saved successfully.")
                # Ensure we don't trigger unnecessary UI updates
                self.root.update_idletasks()
                # Clear status message after 3 seconds
                self.root.after(3000, lambda: self.status_label.config(text=""))
            except Exception as e:
                self.status_label.config(text=f"Error saving PNG: {e}")
                print(f"Error saving PNG: {e}")
    
    def save_jpg(self):
        # Check if we have a valid image to save
        if self.is_generating:
            self.status_label.config(text="Cannot save while generating image")
            return
        if self.gradient_image is None:
            self.status_label.config(text="No image to save")
            return
            
        color1 = self.primary_color[1:]  # Remove '#'
        color2 = self.secondary_color[1:]  # Remove '#'
        gradient_type = "lg" if self.gradient_type == "linear" else "rg"
        default_name = f"{color1}-{color2}_{gradient_type}_{self.width}x{self.height}.jpg"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG files", "*.jpg")],
            title="Save JPEG Image",
            initialfile=default_name
        )
        if file_path:
            try:
                self.status_label.config(text="Saving JPG...")
                # Store current image before saving
                current_image = self.gradient_image
                # Convert to RGB mode if needed (in case we're using RGBA)
                rgb_image = current_image.convert('RGB')
                rgb_image.save(file_path, "JPEG", quality=95)
                self.status_label.config(text="The file has been saved successfully.")
                # Ensure we don't trigger unnecessary UI updates
                self.root.update_idletasks()
                # Clear status message after 3 seconds
                self.root.after(3000, lambda: self.status_label.config(text=""))
            except Exception as e:
                self.status_label.config(text=f"Error saving JPG: {e}")
                print(f"Error saving JPG: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = GradientImageGenerator(root)
    root.mainloop()