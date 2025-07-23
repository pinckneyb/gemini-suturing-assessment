#!/usr/bin/env python3
"""
Suturing Assessment Tool
A GUI application for assessing suturing procedures using Gemini AI
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
from typing import Optional
from pathlib import Path
from config import Config
from gemini_assessor import SuturingAssessor
import cv2
from PIL import Image, ImageTk
from google.genai import types
from reportlab.lib import colors
try:
    from PIL.Image import Resampling
    RESAMPLE_LANCZOS = Resampling.LANCZOS
except ImportError:
    try:
        from PIL.Image import LANCZOS
        RESAMPLE_LANCZOS = LANCZOS
    except ImportError:
        try:
            from PIL.Image import BICUBIC
            RESAMPLE_LANCZOS = BICUBIC
        except ImportError:
            RESAMPLE_LANCZOS = Image.NEAREST

class SuturingAssessmentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Suturing Assessment Tool - Gemini 2.5 Pro")
        self.root.geometry("1400x900")  # Wider and taller
        self.config = Config()
        self.assessor: Optional[SuturingAssessor] = None
        self.video_path = tk.StringVar()
        self.api_key = tk.StringVar(value=self.config.get_api_key())
        self.suture_type = tk.StringVar(value="simple_interrupted")
        self.final_frame_image = None  # Store the selected final product frame
        self.final_frame_path = None
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="Suturing Assessment Tool", font=("Arial", 18, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # API Configuration
        api_frame = ttk.LabelFrame(main_frame, text="API Configuration", padding="10")
        api_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        api_frame.columnconfigure(1, weight=1)
        ttk.Label(api_frame, text="Gemini API Key:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        api_entry = ttk.Entry(api_frame, textvariable=self.api_key, show="*", width=50)
        api_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        save_api_btn = ttk.Button(api_frame, text="Save API Key", command=self.save_api_key)
        save_api_btn.grid(row=0, column=2)

        # Video Selection
        video_frame = ttk.LabelFrame(main_frame, text="Video Selection", padding="10")
        video_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        video_frame.columnconfigure(1, weight=1)
        ttk.Label(video_frame, text="Video File:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        video_entry = ttk.Entry(video_frame, textvariable=self.video_path, width=50)
        video_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        browse_btn = ttk.Button(video_frame, text="Browse", command=self.browse_video)
        browse_btn.grid(row=0, column=2)

        # Suture Type Selection
        suture_frame = ttk.LabelFrame(main_frame, text="Suture Type", padding="10")
        suture_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        suture_frame.columnconfigure(1, weight=1)
        ttk.Label(suture_frame, text="Suture Type:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        suture_combo = ttk.Combobox(suture_frame, textvariable=self.suture_type, state="readonly", width=30)
        suture_combo['values'] = [
            "simple_interrupted",
            "vertical_mattress", 
            "subcuticular"
        ]
        suture_combo.grid(row=0, column=1, sticky="w", padx=(0, 10))
        ttk.Label(suture_frame, text="(Select the type of suture being performed)").grid(row=0, column=2, sticky="w")

        # Assessment Actions
        action_frame = ttk.LabelFrame(main_frame, text="Assessment Actions", padding="10")
        action_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        action_frame.columnconfigure(1, weight=1)
        
        # Single video assessment
        single_btn = ttk.Button(action_frame, text="Single Video Assessment", 
                               command=self.run_assessment, style="Accent.TButton")
        single_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # PDF export button (initially disabled)
        self.pdf_btn = ttk.Button(action_frame, text="Export PDF Report", 
                                 command=self.generate_pdf_report, state="disabled")
        self.pdf_btn.grid(row=0, column=1, sticky="ew", padx=(5, 5))
        
        # Clear/Reset button
        clear_btn = ttk.Button(action_frame, text="Clear All", 
                              command=self.clear_all_data)
        clear_btn.grid(row=0, column=2, sticky="ew", padx=(5, 0))

        # Progress Bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Results Notebook (Tabbed Interface)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        main_frame.rowconfigure(6, weight=1)

        # Assessment Tab
        assess_frame = ttk.Frame(self.notebook)
        self.notebook.add(assess_frame, text="Suturing Assessment")
        self.assess_text = scrolledtext.ScrolledText(assess_frame, wrap=tk.WORD, height=20)
        self.assess_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Raw Response Tab
        raw_frame = ttk.Frame(self.notebook)
        self.notebook.add(raw_frame, text="Raw Response")
        self.raw_text = scrolledtext.ScrolledText(raw_frame, wrap=tk.WORD, height=20)
        self.raw_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Batch Processing
        batch_frame = ttk.LabelFrame(main_frame, text="Batch Processing", padding="10")
        batch_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        batch_frame.columnconfigure(1, weight=1)
        
        # Batch assessment buttons
        batch_btn_frame = ttk.Frame(batch_frame)
        batch_btn_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        batch_btn_frame.columnconfigure(0, weight=1)
        batch_btn_frame.columnconfigure(1, weight=1)
        batch_btn_frame.columnconfigure(2, weight=1)
        
        # Single folder batch
        single_batch_btn = ttk.Button(batch_btn_frame, text="Single Folder\nBatch Assessment", 
                                     command=self.single_folder_batch_assessment)
        single_batch_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Multi-folder batch
        multi_batch_btn = ttk.Button(batch_btn_frame, text="Multi-Folder\nBatch Assessment", 
                                    command=self.multi_folder_batch_assessment)
        multi_batch_btn.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Batch preprocessing
        preprocess_btn = ttk.Button(batch_btn_frame, text="Batch Preprocess\nVideos (>200MB)", 
                                   command=self.batch_preprocess_videos)
        preprocess_btn.grid(row=0, column=2, sticky="ew", padx=(5, 0))
        
        # Batch progress indicators
        self.batch_status = tk.StringVar(value="")
        batch_status_label = ttk.Label(batch_frame, textvariable=self.batch_status, 
                                      font=("Arial", 9), foreground="blue")
        batch_status_label.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        # Batch progress bar
        self.batch_progress = ttk.Progressbar(batch_frame, mode='determinate')
        self.batch_progress.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=8, column=0, columnspan=2, sticky="ew")

        # Consensus Mode Checkbox
        self.consensus_mode = tk.BooleanVar(value=True)
        consensus_check = ttk.Checkbutton(action_frame, text="Consensus Mode (multiple runs per rubric)", variable=self.consensus_mode, command=self._toggle_consensus_options)
        consensus_check.grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(5, 0))
        # Number of runs Spinbox (default 3, min 2, max 3)
        self.num_runs = tk.IntVar(value=3)
        self.runs_spinbox = ttk.Spinbox(action_frame, from_=2, to=3, textvariable=self.num_runs, width=5, state="normal")
        self.runs_spinbox.grid(row=1, column=1, sticky="w", padx=(0, 5), pady=(5, 0))
        ttk.Label(action_frame, text="runs per rubric").grid(row=1, column=2, sticky="w", pady=(5, 0))

    def _toggle_consensus_options(self):
        if self.consensus_mode.get():
            self.runs_spinbox.config(state="normal")
        else:
            self.runs_spinbox.config(state="disabled")

    def clear_all_data(self):
        """Clear all current assessment data and reset the GUI for the next run."""
        # Clear video path
        self.video_path.set("")
        
        # Clear suture type selection
        self.suture_type.set("")
        
        # Clear final frame path
        self.final_frame_path = None
        
        # Clear assessment results
        self.last_result = None
        
        # Clear text areas
        self.assess_text.config(state=tk.NORMAL)
        self.assess_text.delete(1.0, tk.END)
        self.assess_text.config(state=tk.DISABLED)
        
        self.raw_text.config(state=tk.NORMAL)
        self.raw_text.delete(1.0, tk.END)
        self.raw_text.config(state=tk.DISABLED)
        
        # Clear images by calling _display_final_product_images with no data
        self._display_final_product_images(clear_only=True)
        
        # Reset status
        self.status_var.set("Ready")
        
        # Stop progress bar
        self.progress.stop()
        
        # Disable PDF button
        self.pdf_btn.config(state="disabled")
        
        # Reset consensus mode to defaults
        self.consensus_mode.set(True)
        self.num_runs.set(3)
        self.runs_spinbox.config(state="normal")
        
        # Clear batch status
        self.batch_status.set("")
        self.batch_progress['value'] = 0
        
        # Switch to assessment tab
        self.notebook.select(0)
        
        # Show confirmation
        messagebox.showinfo("Cleared", "All data has been cleared. Ready for next assessment.")

    def save_api_key(self):
        api_key = self.api_key.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter a valid API key")
            return
        self.config.set_api_key(api_key)
        messagebox.showinfo("Success", "API key saved successfully!")

    def browse_video(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.m4v"), ("All files", "*.*")]
        )
        if file_path:
            # Always preprocess/compress/convert first, even for small files, to ensure compatibility
            self.status_var.set("Processing video for compatibility...")
            self.progress.start()
            def preprocess_and_extract():
                processed_path = self.preprocess_video(file_path)
                self.video_path.set(processed_path)
                self.status_var.set("Extracting final product frame...")
                self.extract_final_frame_thread(processed_path)
            thread = threading.Thread(target=preprocess_and_extract)
            thread.daemon = True
            thread.start()

    def preprocess_video(self, video_path):
        import os
        import subprocess
        import cv2
        base, ext = os.path.splitext(video_path)
        processed_path = base + '_processed.mp4'
        # Only process if over 200MB
        if os.path.getsize(video_path) <= 200 * 1024 * 1024:
            return video_path
        # Show status in GUI
        self.status_var.set("Processing video for Gemini API size limits...")
        self.root.update_idletasks()
        # Check format and resolution
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        # More conservative scaling - maintain higher quality for assessment
        scale_str = 'scale=-2:1080' if max(width, height) > 1080 else 'scale=trunc(iw/2)*2:trunc(ih/2)*2'
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-vf', scale_str,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '24',  # Better quality (was 28)
            '-an',  # strip audio
            processed_path
        ]
        subprocess.run(cmd, check=True)
        # Notify user that conversion is done
        self.status_var.set("Video processing complete. Beginning assessment...")
        self.root.update_idletasks()
        return processed_path

    def extract_final_frame_thread(self, video_path):
        # Always extract final frame from the processed video
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_idx = max(0, total_frames - 10)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            # Fallback to last frame
            frame_idx = total_frames - 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
        cap.release()
        found = ret and frame is not None
        candidate_path = os.path.splitext(video_path)[0] + "_final_frame.png"
        if found:
            # Resize so long side is 1024 pixels, maintain aspect ratio
            import numpy as np
            h, w = frame.shape[:2]
            if h > w:
                new_h = 1024
                new_w = int(w * (1024 / h))
            else:
                new_w = 1024
                new_h = int(h * (1024 / w))
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            cv2.imwrite(candidate_path, resized)
            self.root.after(0, lambda: self._manual_frame_selection(candidate_path))
        else:
            # No suitable frame found: warn and offer manual selection
            self.root.after(0, lambda: self._manual_frame_selection(video_path))

    def _manual_frame_selection(self, image_path):
        import cv2
        from PIL import Image, ImageTk
        import tkinter as tk
        from tkinter import Toplevel, Label, Button, messagebox, Canvas
        # Load the image before creating the dialog
        img = Image.open(image_path)
        # All image processing is done before dialog creation
        def show_dialog():
            sel_win = Toplevel(self.root)
            sel_win.title("Select Final Product Frame and Region")
            sel_win.minsize(800, 700)
            sel_win.grab_set()
            Label(sel_win, text="Rotate as needed, then select the suture to assess by dragging a rectangle.").pack(pady=10)
            # Store rotation state
            rotation = {'angle': 0}
            def rotate_img(angle):
                rotation['angle'] = (rotation['angle'] + angle) % 360
                update_canvas()
            # Confirm selection button at the bottom
            confirm_frame = tk.Frame(sel_win)
            confirm_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
            def save_and_close():
                # Apply rotation
                rotated = img.rotate(rotation['angle'], expand=True)
                w, h = rotated.size
                scale = min(600 / w, 600 / h)
                # Map selection to original image coordinates
                if not selection['rect'] or not all(isinstance(v, int) for v in selection['rect']):
                    messagebox.showerror("Error", "Please select a region to assess.")
                    return
                x0, y0, x1, y1 = selection['rect']
                x0, x1 = sorted([x0, x1])
                y0, y1 = sorted([y0, y1])
                # Scale back to original image
                x0 = int(x0 / scale)
                x1 = int(x1 / scale)
                y0 = int(y0 / scale)
                y1 = int(y1 / scale)
                cropped = rotated.crop((x0, y0, x1, y1))
                # Resize so long side is 1024 pixels
                ch, cw = cropped.size[1], cropped.size[0]
                if ch > cw:
                    new_h = 1024
                    new_w = int(cw * (1024 / ch))
                else:
                    new_w = 1024
                    new_h = int(ch * (1024 / cw))
                try:
                    resized = cropped.resize((new_w, new_h), RESAMPLE_LANCZOS)
                except Exception:
                    resized = cropped.resize((new_w, new_h))
                candidate_path = os.path.splitext(image_path)[0] + "_cropped.png"
                resized.save(candidate_path)
                sel_win.destroy()
                self._final_frame_result(True, candidate_path)
            use_btn = Button(confirm_frame, text="Use This Region", command=save_and_close)
            use_btn.pack(side=tk.BOTTOM, pady=5)
            # Keyboard shortcut for Enter/Return
            def on_enter(event):
                save_and_close()
            sel_win.bind('<Return>', on_enter)
            # Canvas for image and selection
            canvas = Canvas(sel_win, width=600, height=600, cursor="cross")
            canvas.pack(pady=10)
            tk_img = None
            start_x = start_y = end_x = end_y = None
            selection = {'rect': None}
            def update_canvas():
                nonlocal tk_img, img
                display_img = img.rotate(rotation['angle'], expand=True)
                w, h = display_img.size
                scale = min(600 / w, 600 / h)
                disp = display_img.resize((int(w*scale), int(h*scale)), RESAMPLE_LANCZOS)
                tk_img = ImageTk.PhotoImage(disp)
                canvas.delete("all")
                canvas.create_image(0, 0, anchor="nw", image=tk_img)
                if selection['rect'] and all(isinstance(v, int) for v in selection['rect']):
                    canvas.create_rectangle(*selection['rect'], outline="red", width=2)
            def on_mouse_down(event):
                nonlocal start_x, start_y
                start_x, start_y = event.x, event.y
                selection['rect'] = None
                update_canvas()
            def on_mouse_drag(event):
                nonlocal end_x, end_y
                end_x, end_y = event.x, event.y
                selection['rect'] = (start_x, start_y, end_x, end_y)
                update_canvas()
            def on_mouse_up(event):
                nonlocal end_x, end_y
                end_x, end_y = event.x, event.y
                selection['rect'] = (start_x, start_y, end_x, end_y)
                update_canvas()
            canvas.bind("<ButtonPress-1>", on_mouse_down)
            canvas.bind("<B1-Motion>", on_mouse_drag)
            canvas.bind("<ButtonRelease-1>", on_mouse_up)
            # Rotation buttons
            btn_frame = tk.Frame(sel_win)
            btn_frame.pack(pady=5)
            Button(btn_frame, text="Rotate Left 90°", command=lambda: rotate_img(-90)).pack(side=tk.LEFT, padx=10)
            Button(btn_frame, text="Rotate Right 90°", command=lambda: rotate_img(90)).pack(side=tk.LEFT, padx=10)
            update_canvas()
        # Always create the dialog on the main thread
        self.root.after(0, show_dialog)

    def _final_frame_result(self, found, candidate_path):
        self.progress.stop()
        if found:
            self.final_frame_path = candidate_path
            self.final_frame_image = Image.open(candidate_path)
            self.status_var.set("Final product frame selected.")
        else:
            self.final_frame_path = None
            self.final_frame_image = None
            self.status_var.set("Final product not assessible.")
            messagebox.showwarning("Final Product Not Assessible", "Could not find a suitable final product frame in the video.")

    def is_good_final_frame(self, image_path):
        """Send the frame to Gemini 2.5 and ask if it is a clear, well-lit, unobstructed final product image of a completed suture."""
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key.get().strip())
            model = 'models/gemini-2.5-pro'
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            prompt = (
                "Is this a clear, well-lit, unobstructed final product image of a completed suture? "
                "Answer yes or no and explain. Only answer yes if the suture is clearly visible, the image is not blurry, and the suture appears finished."
            )
            content = types.Content(parts=[
                types.Part.from_bytes(data=image_bytes, mime_type='image/png'),
                types.Part.from_text(text=prompt)
            ])
            response = client.models.generate_content(
                model=model,
                contents=[content]
            )
            text = getattr(response, 'text', str(response)).lower()
            if 'yes' in text and 'no' not in text:
                return True
            return False
        except Exception as e:
            print(f"Error validating final frame with Gemini: {e}")
            return False

    def run_assessment(self):
        """Run suturing assessment"""
        if not self._validate_inputs():
            return
        try:
            self.assessor = SuturingAssessor(self.api_key.get().strip())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize assessor: {str(e)}")
            return
        self.status_var.set("Assessing suturing procedure...")
        self.progress.start()
        consensus = self.consensus_mode.get()
        num_runs = self.num_runs.get() if consensus else 1
        print(f"GUI DEBUG: consensus={consensus}, num_runs={num_runs}")
        thread = threading.Thread(target=self._run_assessment_thread, args=(consensus, num_runs))
        thread.daemon = True
        thread.start()

    def _validate_inputs(self):
        """Validate user inputs"""
        if not self.api_key.get().strip():
            messagebox.showerror("Error", "Please enter and save your Gemini API key")
            return False
        if not self.video_path.get():
            messagebox.showerror("Error", "Please select a video file")
            return False
        if not os.path.exists(self.video_path.get()):
            messagebox.showerror("Error", "Selected video file does not exist")
            return False
        return True

    def _run_assessment_thread(self, consensus, num_runs):
        """Run assessment in background thread with progress updates."""
        print(f"ASSESSMENT THREAD DEBUG: consensus={consensus}, num_runs={num_runs}")
        try:
            video_path = self.video_path.get()
            suture_type = self.suture_type.get()
            if not video_path or not suture_type:
                self.root.after(0, lambda: self._show_error("Please select a video file and suture type"))
                return
            self.root.after(0, lambda: self.status_var.set("Initializing assessor..."))
            api_key = self.config.get_api_key()
            if not api_key:
                self.root.after(0, lambda: self._show_error("Please set your API key first"))
                return
            self.assessor = SuturingAssessor(api_key)
            self.root.after(0, lambda: self.status_var.set("Extracting final frame..."))
            if not self.final_frame_path:
                self.root.after(0, lambda: self._show_error("No final frame available. Please browse for a video first."))
                return
            def progress_callback(message):
                self.root.after(0, lambda: self.status_var.set(message))
                self.root.after(0, self.root.update_idletasks)
                if "Assessing rubric point" in message:
                    self.root.after(0, lambda: self._update_assessment_progress(message))
            self.root.after(0, lambda: self.status_var.set("Running assessment..."))
            print(f"ASSESS_VOP CALL DEBUG: consensus={consensus}, num_runs={num_runs}")
            result = self.assessor.assess_vop(
                video_path,
                self.final_frame_path,
                None,
                suture_type,
                progress_callback,
                consensus,
                num_runs
            )
            self.root.after(0, lambda: self._display_assessment_result(result))
        except Exception as e:
            import traceback
            error_msg = f"Assessment failed: {str(e)}\n\n{traceback.format_exc()}"
            self.root.after(0, lambda: self._show_error(error_msg))
        finally:
            self.root.after(0, lambda: self.progress.stop())
    
    def _update_assessment_progress(self, message):
        """Update the assessment text area with current rubric point being assessed."""
        self.assess_text.config(state=tk.NORMAL)
        # Clear previous progress messages
        content = self.assess_text.get(1.0, tk.END)
        lines = content.split('\n')
        # Remove any previous progress messages
        filtered_lines = [line for line in lines if not line.startswith("🔄 Assessing rubric point")]
        # Add current progress message
        filtered_lines.append(f"🔄 {message}")
        # Update the text area
        self.assess_text.delete(1.0, tk.END)
        self.assess_text.insert(1.0, '\n'.join(filtered_lines))
        self.assess_text.config(state=tk.DISABLED)
        # Scroll to bottom
        self.assess_text.see(tk.END)

    def _display_assessment_result(self, result):
        """Display suturing assessment results with improved formatting."""
        self.last_result = result  # Store for PDF export
        self.progress.stop()
        self.status_var.set("Assessment completed")
        
        # Enable PDF button if assessment was successful
        if 'vop_assessment' in result and 'error' not in result:
            self.pdf_btn.config(state="normal")
        else:
            self.pdf_btn.config(state="disabled")
            
        self.assess_text.config(state=tk.NORMAL)
        self.assess_text.delete(1.0, tk.END)
        self._display_final_product_images()
        if 'vop_assessment' in result:
            self.assess_text.insert(tk.END, "SUTURING ASSESSMENT RESULTS\n")
            self.assess_text.insert(tk.END, f"Suture Type: {result.get('suture_type', 'Unknown').replace('_', ' ').title()}\n")
            self.assess_text.insert(tk.END, f"{'=' * 50}\n\n")
            assessment = result['vop_assessment']
            self.assess_text.insert(tk.END, assessment.strip() + "\n")
        elif 'error' in result:
            self.assess_text.insert(tk.END, f"ERROR:\n{result['error']}")
        else:
            self.assess_text.insert(tk.END, str(result))
        self.assess_text.config(state=tk.DISABLED)
        self._update_raw_response(result)

    def _show_enlarged_image(self, image_path, title):
        """Open a new window to show the image at a larger size. Allows multiple windows, does not freeze UI, adds scrollbars for large images."""
        if not image_path or not os.path.exists(image_path):
            messagebox.showerror("Error", f"Image not found: {image_path}")
            return
        top = tk.Toplevel(self.root)
        top.title(title)
        img = Image.open(image_path)
        # Resize to fit screen but keep aspect ratio
        screen_w = self.root.winfo_screenwidth() - 100
        screen_h = self.root.winfo_screenheight() - 100
        img.thumbnail((min(1000, screen_w), min(1000, screen_h)), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(img)
        canvas = tk.Canvas(top, width=tk_img.width(), height=tk_img.height())
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
        canvas.image = tk_img  # type: ignore
        # Add scrollbars if image is large
        if tk_img.width() > 800 or tk_img.height() > 800:
            x_scroll = tk.Scrollbar(top, orient=tk.HORIZONTAL, command=canvas.xview)
            x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
            y_scroll = tk.Scrollbar(top, orient=tk.VERTICAL, command=canvas.yview)
            y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.config(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set, scrollregion=(0, 0, tk_img.width(), tk_img.height()))
        # No grab_set(), so UI remains responsive
        top.focus_set()

    def _display_final_product_images(self, clear_only=False):
        """Display the reference and student final product images side by side above the assessment text. Both images are clickable to enlarge."""
        # Remove any previous image frames
        if hasattr(self, 'image_frame') and self.image_frame:
            self.image_frame.destroy()
        
        # If clear_only is True, just remove the images and return
        if clear_only:
            return
            
        # Create a new frame above the assessment text
        parent = self.assess_text.master
        self.image_frame = tk.Frame(parent)
        self.image_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        # Select reference image based on suture type
        suture_type = self.suture_type.get()
        ref_image_path = None
        if suture_type == "simple_interrupted":
            ref_image_path = "simple_interrupted_example.png"
        elif suture_type == "vertical_mattress":
            ref_image_path = "vertical_mattress_example.png"
        elif suture_type == "subcuticular":
            ref_image_path = "subcuticular_example.png"
        
        # Load and display reference image
        if ref_image_path and os.path.exists(ref_image_path):
            ref_img = Image.open(ref_image_path).resize((300, 300))
            ref_tk_img = ImageTk.PhotoImage(ref_img)
            ref_label = tk.Label(self.image_frame, image=ref_tk_img, text="Reference", compound=tk.TOP, cursor="hand2")
            ref_label.image = ref_tk_img  # type: ignore
            ref_label.pack(side=tk.LEFT, padx=20)
            ref_label.bind("<Button-1>", lambda e, p=ref_image_path: self._show_enlarged_image(p, "Reference Image"))
        else:
            ref_label = tk.Label(self.image_frame, text="Reference image not found", width=25, height=12)
            ref_label.pack(side=tk.LEFT, padx=20)
        
        # Load and display student final product image
        if self.final_frame_path and os.path.exists(self.final_frame_path):
            stu_img = Image.open(self.final_frame_path).resize((300, 300))
            stu_tk_img = ImageTk.PhotoImage(stu_img)
            stu_label = tk.Label(self.image_frame, image=stu_tk_img, text="Your Final Product", compound=tk.TOP, cursor="hand2")
            stu_label.image = stu_tk_img  # type: ignore
            stu_label.pack(side=tk.LEFT, padx=20)
            stu_label.bind("<Button-1>", lambda e, p=self.final_frame_path: self._show_enlarged_image(p, "Your Final Product"))
        else:
            stu_label = tk.Label(self.image_frame, text="No final product image", width=25, height=12)
            stu_label.pack(side=tk.LEFT, padx=20)

    def _display_vop_simple_interrupted(self, assessment):
        """Display VoP Simple Interrupted assessment results"""
        criteria = [
            ("1. Passes needle perpendicular to skin on both sides of skin", "needle_perpendicular"),
            ("2. Avoids multiple forceps grasps of skin", "avoids_multiple_grasps"),
            ("3. Instrument ties with square knots", "square_knots"),
            ("4. Approximates skin with appropriate tension", "appropriate_tension"),
            ("5. Places sutures 0.5 - 1.0 centimeters apart", "suture_spacing"),
            ("6. Eversion of the skin edges", "skin_eversion"),
            ("7. Economy of time and motion", "economy_of_motion"),
            ("8. Final rating/demonstrates proficiency", "demonstrates_proficiency")
        ]
        
        self._display_vop_criteria(criteria, assessment)

    def _display_vop_vertical_mattress(self, assessment):
        """Display VoP Vertical Mattress assessment results"""
        criteria = [
            ("1. Passes needle perpendicular to skin on both sides of skin", "needle_perpendicular"),
            ("2. Avoids multiple forceps grasps of skin", "avoids_multiple_grasps"),
            ("3. Instrument ties with square knots", "square_knots"),
            ("4. Approximates skin with appropriate tension", "appropriate_tension"),
            ("5. Places sutures 0.5 - 1.0 centimeters apart", "suture_spacing"),
            ("6. Eversion of the skin edges", "skin_eversion"),
            ("7. Economy of time and motion", "economy_of_motion"),
            ("8. Final rating/demonstrates proficiency", "demonstrates_proficiency")
        ]
        
        self._display_vop_criteria(criteria, assessment)

    def _display_vop_subcuticular(self, assessment):
        """Display VoP Subcuticular assessment results"""
        criteria = [
            ("1. Runs the suture, placing appropriate bites into dermal layer", "dermal_bites"),
            ("2. Enters the dermal layer directly across from exit site", "direct_entry"),
            ("3. Avoids multiple penetrations of the dermis", "avoids_multiple_penetrations"),
            ("4. Avoids multiple forceps grasps of skin", "avoids_multiple_grasps"),
            ("5. Instrument ties with square knots", "square_knots"),
            ("6. Approximates skin with appropriate tension", "appropriate_tension"),
            ("7. Economy of time and motion", "economy_of_motion"),
            ("8. Final rating/demonstrates proficiency", "demonstrates_proficiency")
        ]
        
        self._display_vop_criteria(criteria, assessment)

    def _display_vop_criteria(self, criteria, assessment):
        """Display VoP criteria with OSATS scoring"""
        # OSATS scale labels
        osats_labels = {
            1: "Very Poor / Novice",
            2: "Poor / Beginner", 
            3: "Acceptable / Competent",
            4: "Good / Proficient",
            5: "Excellent / Expert"
        }
        
        for display_name, key in criteria:
            value = assessment.get(key, "ERROR")
            
            # Handle new format with Likert score and reasoning
            if isinstance(value, dict) and 'score' in value and 'reasoning' in value:
                score = value['score']
                reasoning = value['reasoning']
                label = osats_labels.get(score, "Unknown")
                self.assess_text.insert(tk.END, f"{display_name}: {score} / 5 ({label})\n")
                self.assess_text.insert(tk.END, f"  Reasoning: {reasoning}\n\n")
            else:
                # Fallback for old format
                self.assess_text.insert(tk.END, f"{display_name}: {value}\n")
        
        # Summative comments
        if 'summative_comments' in assessment:
            self.assess_text.insert(tk.END, f"\nDETAILED FEEDBACK:\n{assessment['summative_comments']}\n")

    def _display_generic_assessment(self, assessment):
        """Display generic assessment results"""
        # OSATS scale labels
        osats_labels = {
            1: "Very Poor / Novice",
            2: "Poor / Beginner", 
            3: "Acceptable / Competent",
            4: "Good / Proficient",
            5: "Excellent / Expert"
        }
        
        for category, items in assessment.items():
            if isinstance(items, dict):
                self.assess_text.insert(tk.END, f"\n{category.upper()}:\n")
                for item, value in items.items():
                    display_name = item.replace('_', ' ').title()
                    
                    # Handle new format with Likert score and reasoning
                    if isinstance(value, dict) and 'score' in value and 'reasoning' in value:
                        score = value['score']
                        reasoning = value['reasoning']
                        label = osats_labels.get(score, "Unknown")
                        self.assess_text.insert(tk.END, f"  {display_name}: {score} / 5 ({label})\n")
                        self.assess_text.insert(tk.END, f"    Reasoning: {reasoning}\n\n")
                    else:
                        # Fallback for old format
                        self.assess_text.insert(tk.END, f"  {display_name}: {value}\n")
            else:
                display_name = category.replace('_', ' ').title()
                self.assess_text.insert(tk.END, f"{display_name}: {items}\n")

    def _update_raw_response(self, result):
        """Update raw response tab"""
        self.raw_text.config(state=tk.NORMAL)
        self.raw_text.delete(1.0, tk.END)
        
        if 'raw_response' in result:
            self.raw_text.insert(tk.END, result['raw_response'])
        else:
            self.raw_text.insert(tk.END, str(result))
        
        self.raw_text.config(state=tk.DISABLED)

    def _show_error(self, message):
        """Show error message"""
        self.progress.stop()
        self.status_var.set("Error occurred")
        messagebox.showerror("Error", message)

    def generate_pdf_report(self):
        """Generate a professional PDF report of the assessment with separator lines and improved formatting."""
        import datetime
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader, simpleSplit
        from reportlab.lib import colors
        from tkinter import filedialog
        import io
        import re
        
        # Get assessment data
        assessment = getattr(self, 'last_result', None)
        if not assessment:
            messagebox.showerror("Error", "No assessment data to export.")
            return
        
        suture_type = self.suture_type.get()
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        video_filename = os.path.basename(self.video_path.get()) if self.video_path.get() else "Unknown"
        
        # Use suture type and video filename in PDF title
        default_pdf_name = f"Suturing Assessment - {suture_type.replace('_', ' ').title()} - {video_filename}.pdf"
        pdf_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=default_pdf_name, filetypes=[("PDF files", "*.pdf")], title="Save PDF Report")
        if not pdf_path:
            return
        
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        y = height - 40
        
        # Page 1: Header and Assessment Results
        # Title with professional formatting
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width // 2, y, "Suturing Assessment Report")
        y -= 30
        
        # Add separator line after title
        c.setStrokeColor(colors.grey)
        c.line(40, y + 5, width - 40, y + 5)
        y -= 20
        
        # Metadata section
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Assessment Information")
        y -= 20
        
        c.setFont("Helvetica", 10)
        c.drawString(40, y, f"Video File: {video_filename}")
        y -= 15
        c.drawString(40, y, f"Suture Type: {suture_type.replace('_', ' ').title()}")
        y -= 15
        c.drawString(40, y, f"Assessment Date: {now}")
        y -= 25
        
        # Add separator line before assessment results
        c.setStrokeColor(colors.grey)
        c.line(40, y + 5, width - 40, y + 5)
        y -= 20
        
        # Assessment Results section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Assessment Results")
        y -= 25
        
        # Get assessment text
        assessment_text = None
        if isinstance(assessment, dict) and 'vop_assessment' in assessment:
            assessment_text = assessment['vop_assessment']
        else:
            assessment_text = str(assessment)
        
        # Remove duplicate headings from assessment_text
        assessment_text = re.sub(r"SUTURING ASSESSMENT RESULTS.*?={10,}\n+", "", assessment_text, flags=re.DOTALL)
        
        # Process assessment text with professional formatting
        max_width = width - 80
        lines = assessment_text.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                y -= 8  # Extra space for empty lines
                continue
                
            # Handle rubric point headers (e.g., "1) passes needle perpendicular to skin")
            if re.match(r'^\d+\)', line):
                # Add section separator line
                c.setStrokeColor(colors.grey)
                c.line(40, y + 5, width - 40, y + 5)
                y -= 10
                
                c.setFont("Helvetica-Bold", 11)
                wrapped = simpleSplit(line, "Helvetica-Bold", 11, max_width)
                for wline in wrapped:
                    if y < 60:
                        c.showPage()
                        y = height - 40
                        c.setFont("Helvetica-Bold", 11)
                    c.drawString(40, y, wline)
                    y -= 14
                y -= 8  # Extra space after rubric point
            
            # Handle score lines (e.g., "3/5 competent")
            elif re.match(r'^\d+/5\s+(poor|substandard|competent|proficient|exemplary)', line, re.IGNORECASE):
                c.setFont("Helvetica-Bold", 11)
                c.drawString(40, y, line)
                y -= 16
                y -= 8  # Extra space after score
            
            # Handle description lines (formerly justification)
            elif line and not line.startswith('Final Score:') and not line.startswith('Summative Comment:'):
                c.setFont("Helvetica", 10)
                wrapped = simpleSplit(line, "Helvetica", 10, max_width)
                for wline in wrapped:
                    if y < 60:
                        c.showPage()
                        y = height - 40
                        c.setFont("Helvetica", 10)
                    c.drawString(40, y, wline)
                    y -= 12
                y -= 10  # Extra space after description
                
                # Add separator line after each complete rubric point
                c.setStrokeColor(colors.lightgrey)
                c.line(40, y + 5, width - 40, y + 5)
                y -= 15  # Extra space after separator
            
            # Handle final score line
            elif line.startswith('Final Score:'):
                # Add separator line before final score
                c.setStrokeColor(colors.grey)
                c.line(40, y + 5, width - 40, y + 5)
                y -= 15
                
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, line)
                y -= 20
            
            # Handle summative comment
            elif line.startswith('Summative Comment:'):
                y -= 10  # Extra space before comment
                c.setFont("Helvetica-Bold", 11)
                c.drawString(40, y, line)
                y -= 16
            else:
                # Handle any other lines
                c.setFont("Helvetica", 10)
                wrapped = simpleSplit(line, "Helvetica", 10, max_width)
                for wline in wrapped:
                    if y < 60:
                        c.showPage()
                        y = height - 40
                        c.setFont("Helvetica", 10)
                    c.drawString(40, y, wline)
                    y -= 12
        
        # Page 2: Student Final Product (centered, enlarged)
        c.showPage()
        y = height - 60
        
        # Add separator line at top
        c.setStrokeColor(colors.grey)
        c.line(40, y + 5, width - 40, y + 5)
        y -= 20
        
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width // 2, y, "Student Final Product")
        y -= 25
        
        if self.final_frame_path and os.path.exists(self.final_frame_path):
            img_w, img_h = 600, 450
            x = (width - img_w) // 2
            c.drawImage(self.final_frame_path, x, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, mask='auto')
        
        # Page 3: Reference Image (centered, enlarged)
        c.showPage()
        y = height - 60
        
        # Add separator line at top
        c.setStrokeColor(colors.grey)
        c.line(40, y + 5, width - 40, y + 5)
        y -= 20
        
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width // 2, y, "Reference Image")
        y -= 25
        
        if suture_type == "simple_interrupted":
            ref_image_path = "simple_interrupted_example.png"
        elif suture_type == "vertical_mattress":
            ref_image_path = "vertical_mattress_example.png"
        elif suture_type == "subcuticular":
            ref_image_path = "subcuticular_example.png"
        else:
            ref_image_path = None
            
        if ref_image_path and os.path.exists(ref_image_path):
            img_w, img_h = 600, 450
            x = (width - img_w) // 2
            c.drawImage(ref_image_path, x, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, mask='auto')

        c.save()
        messagebox.showinfo("PDF Saved", f"Professional PDF report saved to: {pdf_path}")
        
        # Offer to open the PDF
        import sys
        import subprocess
        if messagebox.askyesno("Open PDF", "Would you like to open the PDF now?"):
            try:
                if sys.platform.startswith('darwin'):
                    subprocess.call(('open', pdf_path))
                elif os.name == 'nt':
                    os.startfile(pdf_path)
                elif os.name == 'posix':
                    subprocess.call(('xdg-open', pdf_path))
            except Exception as e:
                messagebox.showerror("Error", f"Could not open PDF: {e}")

    def batch_assessment(self):
        """Initiate batch assessment - choose between single folder or multi-folder"""
        choice = messagebox.askyesnocancel("Batch Assessment Type", 
                                          "Choose batch assessment type:\n\n"
                                          "Yes = Multi-folder (different suture types)\n"
                                          "No = Single folder (same suture type)\n"
                                          "Cancel = Abort")
        
        if choice is None:  # Cancel
            return
        elif choice:  # Multi-folder
            self.multi_folder_batch_assessment()
        else:  # Single folder
            self.single_folder_batch_assessment()

    def single_folder_batch_assessment(self):
        """Initiate batch assessment of multiple videos in a single folder using smart video selection"""
        from pathlib import Path
        
        folder_path = filedialog.askdirectory(title="Select Folder with Videos")
        if not folder_path:
            return
        
        # Use smart video selection
        video_files = self._smart_video_selection(folder_path)
        
        if not video_files:
            messagebox.showwarning("No Videos Found", "No suitable video files found in selected folder")
            return
        
        # Confirm with user
        result = messagebox.askyesno("Confirm Smart Batch Assessment", 
                                    f"Assess {len(video_files)} videos as {self.suture_type.get()} sutures?\n\n"
                                    f"Smart selection will use preprocessed videos when available and skip large originals.\n"
                                    f"Videos will be processed one by one and PDF reports will be saved in the same folder.")
        if not result:
            return
        
        # Create batch configuration
        batch_config = [(folder_path, self.suture_type.get(), video_files)]
        
        # Run batch processing in separate thread
        thread = threading.Thread(target=self._run_multi_batch_assessment, args=(batch_config,))
        thread.daemon = True
        thread.start()

    def multi_folder_batch_assessment(self):
        """Initiate multi-folder batch assessment with different suture types"""
        self._show_multi_folder_setup_dialog()

    def _show_multi_folder_setup_dialog(self):
        """Show dialog for setting up multi-folder batch assessment"""
        from tkinter import Toplevel, Label, Button, Frame, ttk
        from pathlib import Path
        
        # Create setup window
        setup_win = Toplevel(self.root)
        setup_win.title("Multi-Folder Batch Assessment Setup")
        setup_win.geometry("600x500")
        setup_win.transient(self.root)
        setup_win.grab_set()
        
        # Store folder configurations
        folder_configs = []
        
        # Main frame
        main_frame = ttk.Frame(setup_win, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Multi-Folder Batch Assessment Setup", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Instructions
        instructions = ttk.Label(main_frame, text="Add folders containing videos for different suture types.\nEach folder will be assessed with its specified suture type.")
        instructions.pack(pady=(0, 20))
        
        # Folder list frame
        list_frame = ttk.LabelFrame(main_frame, text="Folders to Process", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Treeview for folders
        columns = ("Folder", "Suture Type", "Videos")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=6)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        tree.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        def add_folder():
            folder_path = filedialog.askdirectory(title="Select Folder with Videos")
            if not folder_path:
                return
            
            # Use smart video selection
            video_files = self._smart_video_selection(folder_path)
            
            if not video_files:
                messagebox.showwarning("No Videos Found", f"No suitable video files found in {folder_path}")
                return
            
            # Create suture type selection dialog
            suture_win = Toplevel(setup_win)
            suture_win.title("Select Suture Type")
            suture_win.geometry("300x150")
            suture_win.transient(setup_win)
            suture_win.grab_set()
            
            suture_type = tk.StringVar(value="simple_interrupted")
            
            ttk.Label(suture_win, text="Select suture type for this folder:").pack(pady=10)
            suture_combo = ttk.Combobox(suture_win, textvariable=suture_type, state="readonly", width=30)
            suture_combo['values'] = ["simple_interrupted", "vertical_mattress", "subcuticular"]
            suture_combo.pack(pady=10)
            
            def confirm_suture():
                folder_name = os.path.basename(folder_path)
                tree.insert("", tk.END, values=(folder_name, suture_type.get(), len(video_files)))
                folder_configs.append((folder_path, suture_type.get(), video_files))
                suture_win.destroy()
            
            ttk.Button(suture_win, text="Confirm", command=confirm_suture).pack(pady=10)
        
        def remove_folder():
            selected = tree.selection()
            if selected:
                item = tree.item(selected[0])
                folder_name = item['values'][0]
                
                # Remove from folder_configs
                for i, (path, suture_type, files) in enumerate(folder_configs):
                    if os.path.basename(path) == folder_name:
                        folder_configs.pop(i)
                        break
                
                tree.delete(selected[0])
        
        def clear_all():
            tree.delete(*tree.get_children())
            folder_configs.clear()
        
        def start_assessment():
            if not folder_configs:
                messagebox.showwarning("No Folders", "Please add at least one folder before starting.")
                return
            
            # Calculate total videos
            total_videos = sum(len(files) for _, _, files in folder_configs)
            
            # Confirm with user
            result = messagebox.askyesno("Confirm Multi-Folder Batch Assessment", 
                                        f"Process {len(folder_configs)} folders with {total_videos} total videos?\n\n"
                                        f"Folders will be processed in order and PDF reports saved in each folder.")
            if not result:
                return
            
            setup_win.destroy()
            
            # Run batch processing in separate thread
            thread = threading.Thread(target=self._run_multi_batch_assessment, args=(folder_configs,))
            thread.daemon = True
            thread.start()
        
        # Add buttons
        ttk.Button(button_frame, text="Add Folder", command=add_folder).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Remove Selected", command=remove_folder).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Clear All", command=clear_all).pack(side=tk.LEFT, padx=(0, 10))
        
        # Start/Cancel buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X)
        
        ttk.Button(action_frame, text="Start Assessment", command=start_assessment, style="Accent.TButton").pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(action_frame, text="Cancel", command=setup_win.destroy).pack(side=tk.RIGHT)

    def _run_multi_batch_assessment(self, batch_config):
        """Run batch assessment across multiple folders with different suture types"""
        from pathlib import Path
        import datetime
        
        # Calculate total videos across all folders
        total_videos = sum(len(files) for _, _, files in batch_config)
        total_folders = len(batch_config)
        
        self.root.after(0, lambda: self.status_var.set(f"Starting multi-folder batch assessment: {total_folders} folders, {total_videos} videos..."))
        self.root.after(0, lambda: self.progress.start())
        
        successful_assessments = 0
        failed_assessments = 0
        current_video_global = 0
        
        # Process each folder
        for folder_idx, (folder_path, suture_type, video_files) in enumerate(batch_config):
            folder_name = os.path.basename(folder_path)
            
            self.root.after(0, lambda f=folder_name, idx=folder_idx+1, total=total_folders: 
                           self.status_var.set(f"Processing folder {idx}/{total}: {f}"))
            
            print(f"Starting folder {folder_idx + 1}/{total_folders}: {folder_name} with {len(video_files)} videos")
            
            # Process videos in this folder
            for video_idx, video_file in enumerate(video_files):
                current_video_global += 1
                current_video_in_folder = video_idx + 1
                
                try:
                    print(f"Processing video {current_video_global}/{total_videos}: {video_file.name} in folder {folder_name}")
                    
                    # Update status on main thread
                    self.root.after(0, lambda v=video_file.name, f=folder_name, cg=current_video_global, 
                                   cf=current_video_in_folder, tf=len(video_files), tg=total_videos: 
                                   self.status_var.set(f"Processing {f}: {v} ({cf}/{tf}) - Total: {cg}/{tg}"))
                    
                    # Use existing assessment logic with specific suture type
                    result = self._assess_single_video_with_type(str(video_file), suture_type)
                    
                    if result:
                        print(f"Assessment successful for {video_file.name}")
                        # Generate PDF using existing method
                        pdf_path = self._generate_batch_pdf_with_type(result, str(video_file), folder_path, suture_type)
                        successful_assessments += 1
                        self.root.after(0, lambda v=video_file.name, f=folder_name, cg=current_video_global, 
                                       cf=current_video_in_folder, tf=len(video_files), tg=total_videos: 
                                       self.status_var.set(f"Completed {f}: {v} ({cf}/{tf}) - Total: {cg}/{tg} - PDF saved"))
                    else:
                        print(f"Assessment failed for {video_file.name} - no result returned")
                        failed_assessments += 1
                        self.root.after(0, lambda v=video_file.name, f=folder_name, cg=current_video_global, 
                                       cf=current_video_in_folder, tf=len(video_files), tg=total_videos: 
                                       self.status_var.set(f"Failed to assess {f}: {v} ({cf}/{tf}) - Total: {cg}/{tg}"))
                    
                except Exception as e:
                    print(f"Exception processing {video_file.name}: {e}")
                    import traceback
                    traceback.print_exc()
                    failed_assessments += 1
                    self.root.after(0, lambda v=video_file.name, f=folder_name, cg=current_video_global, 
                                   cf=current_video_in_folder, tf=len(video_files), tg=total_videos, err=str(e): 
                                   self.status_var.set(f"Error processing {f}: {v} ({cf}/{tf}) - Total: {cg}/{tg}: {err}"))
            
            print(f"Completed folder {folder_idx + 1}/{total_folders}: {folder_name}")
        
        # Final status update on main thread
        self.root.after(0, lambda: self.progress.stop())
        self.root.after(0, lambda: self.status_var.set(f"Multi-folder batch assessment complete ({total_videos}/{total_videos}). {successful_assessments} successful, {failed_assessments} failed."))
        self.root.after(0, lambda: messagebox.showinfo("Batch Complete", 
                           f"Processed {total_folders} folders with {total_videos} total videos.\n"
                           f"Successful: {successful_assessments}\n"
                           f"Failed: {failed_assessments}\n\n"
                           f"PDF reports saved in respective folders."))

    def _run_batch_assessment(self, folder_path, video_files):
        """Run batch assessment of multiple videos (legacy method for single folder)"""
        # Convert to new format and use multi-batch method
        batch_config = [(folder_path, self.suture_type.get(), video_files)]
        self._run_multi_batch_assessment(batch_config)

    def _assess_single_video_with_type(self, video_path, suture_type):
        """Assess a single video with specified suture type"""
        try:
            print(f"Starting assessment of {video_path} with suture type {suture_type}")
            
            # Validate inputs
            if not video_path or not os.path.exists(video_path):
                print(f"Video path invalid or file doesn't exist: {video_path}")
                return None
            
            if not suture_type:
                print("Suture type is empty")
                return None
            
            api_key = self.api_key.get().strip()
            if not api_key:
                print("API key is empty")
                return None
            
            print("Initializing assessor...")
            # Initialize assessor
            self.assessor = SuturingAssessor(api_key)
            
            print("Extracting final frame...")
            # Extract final frame
            final_frame_path = self._extract_final_frame_for_batch(video_path)
            if not final_frame_path:
                print("Failed to extract final frame")
                return None
            
            # Save final frame to video directory for PDF inclusion
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            saved_final_frame_path = os.path.join(video_dir, f"{video_name}_final_frame.png")
            
            try:
                import shutil
                shutil.copy2(final_frame_path, saved_final_frame_path)
                print(f"Saved final frame to: {saved_final_frame_path}")
            except Exception as e:
                print(f"Warning: Could not save final frame: {e}")
            
            print("Checking if video needs preprocessing...")
            # Check if video is already preprocessed or needs preprocessing
            if video_path.endswith('_processed.mp4'):
                # Already preprocessed - use as is
                processed_video_path = video_path
                print("Using preprocessed video directly")
            else:
                # Check if preprocessed version exists
                base, ext = os.path.splitext(video_path)
                preprocessed_path = base + '_processed.mp4'
                if os.path.exists(preprocessed_path):
                    processed_video_path = preprocessed_path
                    print(f"Using existing preprocessed version: {preprocessed_path}")
                else:
                    # Preprocess video if needed
                    processed_video_path = self.preprocess_video(video_path)
            
            print("Running assessment...")
            # Run assessment with specified suture type
            result = self.assessor.assess_vop(processed_video_path, final_frame_path, None, suture_type)
            
            print("Cleaning up temporary files...")
            # Clean up processed video if it was created
            if processed_video_path != video_path and os.path.exists(processed_video_path):
                try:
                    os.remove(processed_video_path)
                except Exception as cleanup_error:
                    print(f"Warning: Could not remove processed video: {cleanup_error}")
            
            # Clean up final frame
            if os.path.exists(final_frame_path):
                try:
                    os.remove(final_frame_path)
                except Exception as cleanup_error:
                    print(f"Warning: Could not remove final frame: {cleanup_error}")
            
            print(f"Assessment completed successfully for {video_path}")
            return result
            
        except Exception as e:
            print(f"Error in _assess_single_video_with_type for {video_path}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _assess_single_video(self, video_path):
        """Assess a single video using existing logic (legacy method)"""
        return self._assess_single_video_with_type(video_path, self.suture_type.get())

    def _extract_final_frame_for_batch(self, video_path):
        """Extract final frame for batch processing"""
        import cv2
        
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_idx = max(0, total_frames - 10)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            # Fallback to last frame
            frame_idx = total_frames - 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
        cap.release()
        
        if not ret or frame is None:
            return None
        
        # Resize so long side is 1024 pixels, maintain aspect ratio
        h, w = frame.shape[:2]
        if h > w:
            new_h = 1024
            new_w = int(w * (1024 / h))
        else:
            new_w = 1024
            new_h = int(h * (1024 / w))
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Save to temporary file
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
        os.close(temp_fd)
        cv2.imwrite(temp_path, resized)
        
        return temp_path

    def _generate_batch_pdf_with_type(self, assessment, video_path, output_folder, suture_type):
        """Generate PDF for batch processing with specified suture type"""
        import datetime
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader, simpleSplit
        
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        video_filename = os.path.basename(video_path)
        
        # Create PDF filename
        pdf_filename = f"Assessment_{suture_type}_{video_filename}_{now}.pdf"
        pdf_path = os.path.join(output_folder, pdf_filename)
        
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        y = height - 40
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, f"Suturing Assessment Report - {video_filename}")
        y -= 30
        c.setFont("Helvetica", 10)
        c.drawString(40, y, f"Video File: {video_filename}")
        y -= 15
        c.drawString(40, y, f"Suture Type: {suture_type.replace('_', ' ').title()}")
        y -= 15
        c.drawString(40, y, f"Assessment Date: {now}")
        y -= 25
        
        # Add final product image if available
        final_frame_path = os.path.splitext(video_path)[0] + "_final_frame.png"
        if os.path.exists(final_frame_path):
            try:
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, "Final Product Image:")
                y -= 15
                
                # Load and resize image for PDF
                img = ImageReader(final_frame_path)
                img_width, img_height = img.getSize()
                
                # Scale image to fit on page (max 300px width)
                scale = min(300 / img_width, 200 / img_height)
                display_width = img_width * scale
                display_height = img_height * scale
                
                # Check if we need a new page
                if y - display_height < 60:
                    c.showPage()
                    y = height - 40
                
                c.drawImage(final_frame_path, 40, y - display_height, width=display_width, height=display_height)
                y -= display_height + 20
                
            except Exception as e:
                print(f"Error adding final product image to PDF: {e}")
                y -= 20
        
        # Add exemplar image if available
        exemplar_path = f"{suture_type}_example.png"
        if os.path.exists(exemplar_path):
            try:
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, "Exemplar Image:")
                y -= 15
                
                # Load and resize image for PDF
                img = ImageReader(exemplar_path)
                img_width, img_height = img.getSize()
                
                # Scale image to fit on page (max 300px width)
                scale = min(300 / img_width, 200 / img_height)
                display_width = img_width * scale
                display_height = img_height * scale
                
                # Check if we need a new page
                if y - display_height < 60:
                    c.showPage()
                    y = height - 40
                
                c.drawImage(exemplar_path, 40, y - display_height, width=display_width, height=display_height)
                y -= display_height + 20
                
            except Exception as e:
                print(f"Error adding exemplar image to PDF: {e}")
                y -= 20
        
        # Assessment output
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Assessment Results:")
        y -= 20
        
        assessment_text = None
        if isinstance(assessment, dict) and 'vop_assessment' in assessment:
            assessment_text = assessment['vop_assessment']
        else:
            assessment_text = str(assessment)
        
        # Remove duplicate headings
        import re
        assessment_text = re.sub(r"SUTURING ASSESSMENT RESULTS.*?={10,}\n+", "", assessment_text, flags=re.DOTALL)
        
        # Process assessment text with improved formatting
        max_width = width - 80
        lines = assessment_text.splitlines()
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Check if we need a new page
            if y < 60:
                c.showPage()
                y = height - 40
            
            # Handle rubric point headers (e.g., "1) passes needle perpendicular to skin")
            if re.match(r'^\d+\)', line):
                # Add section separator line
                c.setStrokeColor(colors.grey)
                c.line(40, y + 5, width - 40, y + 5)
                y -= 10
                
                c.setFont("Helvetica-Bold", 11)
                wrapped = simpleSplit(line, "Helvetica-Bold", 11, max_width)
                for wline in wrapped:
                    if y < 60:
                        c.showPage()
                        y = height - 40
                        c.setFont("Helvetica-Bold", 11)
                    c.drawString(40, y, wline)
                    y -= 14
                y -= 8  # Extra space after rubric point
            
            # Handle score lines (e.g., "3/5 competent")
            elif re.match(r'^\d+/5\s+(poor|substandard|competent|proficient|exemplary)', line, re.IGNORECASE):
                c.setFont("Helvetica-Bold", 11)
                c.drawString(40, y, line)
                y -= 16
                y -= 8  # Extra space after score
            
            # Handle description lines (formerly justification)
            elif line and not line.startswith('Final Score:') and not line.startswith('Summative Comment:'):
                c.setFont("Helvetica", 10)
                wrapped = simpleSplit(line, "Helvetica", 10, max_width)
                for wline in wrapped:
                    if y < 60:
                        c.showPage()
                        y = height - 40
                        c.setFont("Helvetica", 10)
                    c.drawString(40, y, wline)
                    y -= 12
                y -= 10  # Extra space after description
                
                # Add separator line after each complete rubric point
                c.setStrokeColor(colors.lightgrey)
                c.line(40, y + 5, width - 40, y + 5)
                y -= 15  # Extra space after separator
            
            # Handle final score line
            elif line.startswith('Final Score:'):
                # Add separator before final score
                y -= 15
                c.setStrokeColor(colors.grey)
                c.line(40, y + 5, width - 40, y + 5)
                y -= 10
                
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, line)
                y -= 20
                y -= 15  # Extra space after final score
            
            # Handle summative comment header
            elif line.startswith('Summative Comment:'):
                y -= 10  # Extra space before summative comment
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, line)
                y -= 20
            
            # Handle empty lines
            elif not line:
                y -= 10  # Increased spacing for empty lines
            
            # Handle other lines
            else:
                c.setFont("Helvetica", 10)
                wrapped = simpleSplit(line, "Helvetica", 10, max_width)
                for wline in wrapped:
                    if y < 60:
                        c.showPage()
                        y = height - 40
                        c.setFont("Helvetica", 10)
                    c.drawString(40, y, wline)
                    y -= 12
            
            i += 1
        
        c.save()
        return pdf_path

    def _generate_batch_pdf(self, assessment, video_path, output_folder):
        """Generate PDF for batch processing (legacy method)"""
        return self._generate_batch_pdf_with_type(assessment, video_path, output_folder, self.suture_type.get())

    def batch_preprocess_videos(self):
        """Initiate batch preprocessing of all large videos in a folder using parallel processing."""
        folder_path = filedialog.askdirectory(title="Select Folder with Videos to Preprocess")
        if not folder_path:
            return
        
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.m4v']
        video_files = []
        for ext in video_extensions:
            video_files.extend(Path(folder_path).glob(f"*{ext}"))
        
        if not video_files:
            messagebox.showwarning("No Videos Found", "No video files found in selected folder to preprocess.")
            return
        
        # Filter for large videos only
        large_videos = [vf for vf in video_files if os.path.getsize(vf) > 200 * 1024 * 1024]
        
        if not large_videos:
            messagebox.showinfo("No Large Videos", "No videos over 200MB found in the selected folder.")
            return
        
        result = messagebox.askyesno("Confirm Parallel Batch Preprocessing", 
                                    f"Preprocess {len(large_videos)} large videos in {folder_path}?\n\n"
                                    f"This will create '_processed.mp4' files using parallel processing for faster completion.")
        if not result:
            return
        
        self.batch_status.set("Starting parallel batch preprocessing...")
        self.root.update_idletasks()
        
        # Start parallel processing in background thread
        thread = threading.Thread(target=self._run_parallel_preprocessing, args=(large_videos,))
        thread.daemon = True
        thread.start()

    def _run_parallel_preprocessing(self, video_files):
        """Run parallel video preprocessing with progress tracking."""
        import concurrent.futures
        import time
        
        total_videos = len(video_files)
        processed_count = 0
        failed_count = 0
        start_time = time.time()
        last_update_time = 0
        
        # Thread-safe counters
        from threading import Lock
        counter_lock = Lock()
        
        def process_single_video(video_file):
            nonlocal processed_count, failed_count
            video_name = video_file.name
            video_path = str(video_file)
            
            try:
                print(f"Starting parallel preprocessing of {video_name}...")
                
                # Use the same compression settings as individual preprocessing
                import subprocess
                import cv2
                base, ext = os.path.splitext(video_path)
                processed_path = base + '_processed.mp4'
                
                # Check format and resolution
                cap = cv2.VideoCapture(video_path)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                
                # More conservative scaling - maintain higher quality for assessment
                scale_str = 'scale=-2:1080' if max(width, height) > 1080 else 'scale=trunc(iw/2)*2:trunc(ih/2)*2'
                cmd = [
                    'ffmpeg', '-y', '-i', video_path,
                    '-vf', scale_str,
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '24',  # Better quality
                    '-an',  # strip audio
                    processed_path
                ]
                
                subprocess.run(cmd, check=True, capture_output=True)
                
                if os.path.exists(processed_path):
                    print(f"Successfully preprocessed {video_name}")
                    with counter_lock:
                        processed_count += 1
                    return True, video_name
                else:
                    print(f"Failed to preprocess {video_name} - output file not created")
                    with counter_lock:
                        failed_count += 1
                    return False, video_name
                    
            except Exception as e:
                print(f"Exception during preprocessing of {video_name}: {e}")
                import traceback
                traceback.print_exc()
                with counter_lock:
                    failed_count += 1
                return False, video_name
        
        # Determine optimal number of workers based on CPU cores
        import multiprocessing
        max_workers = min(multiprocessing.cpu_count(), len(video_files), 4)  # Cap at 4 to avoid overwhelming system
        
        print(f"Starting parallel preprocessing with {max_workers} workers for {total_videos} videos...")
        
        # Initial status update and progress bar setup
        self.root.after(0, lambda: self.batch_status.set(f"Starting parallel preprocessing with {max_workers} workers..."))
        self.root.after(0, lambda: self.batch_progress.configure(maximum=total_videos, value=0))
        
        # Process videos in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_video = {executor.submit(process_single_video, video_file): video_file for video_file in video_files}
            
            # Process completed tasks and update progress (throttled)
            for future in concurrent.futures.as_completed(future_to_video):
                video_file = future_to_video[future]
                try:
                    success, video_name = future.result()
                    current_processed = processed_count
                    current_failed = failed_count
                    
                    # Throttle GUI updates to prevent freezing (update every 2 seconds max)
                    current_time = time.time()
                    if current_time - last_update_time >= 2.0:
                        # Update progress in GUI (throttled)
                        self.root.after(0, lambda p=current_processed, f=current_failed, t=total_videos: 
                                       self.batch_status.set(f"Processing: {p} completed, {f} failed ({p+f}/{t})"))
                        
                        # Update progress bar
                        self.root.after(0, lambda p=current_processed, f=current_failed: 
                                       self.batch_progress.configure(value=p + f))
                        
                        # Calculate and show time estimates
                        elapsed_time = current_time - start_time
                        if current_processed + current_failed > 0:
                            avg_time_per_video = elapsed_time / (current_processed + current_failed)
                            remaining_videos = total_videos - (current_processed + current_failed)
                            estimated_remaining = avg_time_per_video * remaining_videos
                            
                            self.root.after(0, lambda p=current_processed, f=current_failed, t=total_videos, 
                                           est=estimated_remaining: 
                                           self.batch_status.set(f"Processing: {p} completed, {f} failed ({p+f}/{t}) - Est. {est:.1f}s remaining"))
                        
                        last_update_time = current_time
                    
                except Exception as e:
                    print(f"Error processing result for {video_file.name}: {e}")
                    with counter_lock:
                        failed_count += 1
        
        # Final status update
        total_time = time.time() - start_time
        avg_time = total_time / total_videos if total_videos > 0 else 0
        
        self.root.after(0, lambda p=processed_count, f=failed_count, t=total_videos, 
                       time_taken=total_time, avg=avg_time: 
                       self.batch_status.set(f"Complete: {p} processed, {f} failed in {time_taken:.1f}s (avg {avg:.1f}s/video)"))
        
        # Show completion dialog after a short delay to ensure GUI is responsive
        self.root.after(1000, lambda: messagebox.showinfo("Parallel Batch Preprocessing Complete", 
                                                         f"Parallel preprocessing of {total_videos} videos complete.\n\n"
                                                         f"Successfully processed: {processed_count}\n"
                                                         f"Failed: {failed_count}\n"
                                                         f"Total time: {total_time:.1f} seconds\n"
                                                         f"Average time per video: {avg_time:.1f} seconds\n"
                                                         f"Speedup: ~{max_workers}x faster than sequential processing\n\n"
                                                         f"Processed files are marked with '_processed.mp4' in their original location."))

    def _smart_video_selection(self, folder_path):
        """Smart video selection that prioritizes preprocessed videos and skips large originals when preprocessed versions exist"""
        from pathlib import Path
        
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.m4v']
        all_videos = []
        
        # Get all video files in folder
        for ext in video_extensions:
            all_videos.extend(Path(folder_path).glob(f"*{ext}"))
        
        if not all_videos:
            return []
        
        # Separate original and preprocessed videos
        original_videos = []
        preprocessed_videos = []
        
        for video in all_videos:
            if video.name.endswith('_processed.mp4'):
                preprocessed_videos.append(video)
            else:
                original_videos.append(video)
        
        # Create mapping of original to preprocessed
        original_to_processed = {}
        for processed in preprocessed_videos:
            # Extract original name (remove '_processed.mp4')
            original_name = processed.name.replace('_processed.mp4', '')
            # Find corresponding original file
            for original in original_videos:
                if original.name == original_name:
                    original_to_processed[original] = processed
                    break
        
        # Select videos using smart logic
        selected_videos = []
        
        for original in original_videos:
            original_size = os.path.getsize(original)
            
            if original in original_to_processed:
                # Original has a preprocessed version - use the preprocessed one
                selected_videos.append(original_to_processed[original])
                print(f"Using preprocessed version: {original_to_processed[original].name} (original: {original.name})")
            elif original_size <= 200 * 1024 * 1024:
                # Original is under 200MB and no preprocessed version exists - use original
                selected_videos.append(original)
                print(f"Using original (under 200MB): {original.name}")
            else:
                # Original is over 200MB but no preprocessed version exists - skip
                print(f"Skipping large original without preprocessed version: {original.name} ({original_size / (1024*1024):.1f}MB)")
        
        # Add any preprocessed videos that don't have corresponding originals (edge case)
        for processed in preprocessed_videos:
            original_name = processed.name.replace('_processed.mp4', '')
            has_original = any(original.name == original_name for original in original_videos)
            if not has_original:
                selected_videos.append(processed)
                print(f"Using orphaned preprocessed video: {processed.name}")
        
        print(f"Smart video selection: {len(selected_videos)} videos selected from {len(all_videos)} total videos")
        return selected_videos

def main():
    root = tk.Tk()
    app = SuturingAssessmentGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 