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
from config import Config
from gemini_assessor import SuturingAssessor
import cv2
from PIL import Image, ImageTk
from google.genai import types

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

        # Action Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        assess_btn = ttk.Button(button_frame, text="Assess Suturing", command=self.run_assessment, style="Accent.TButton")
        assess_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        batch_btn = ttk.Button(button_frame, text="Batch Assessment", command=self.batch_assessment)
        batch_btn.pack(side=tk.LEFT)

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
        # PDF Button
        self.pdf_btn = ttk.Button(assess_frame, text="Download PDF Report", command=self.generate_pdf_report)
        self.pdf_btn.pack(pady=(0, 10))

        # Raw Response Tab
        raw_frame = ttk.Frame(self.notebook)
        self.notebook.add(raw_frame, text="Raw Response")
        self.raw_text = scrolledtext.ScrolledText(raw_frame, wrap=tk.WORD, height=20)
        self.raw_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=7, column=0, columnspan=2, sticky="ew")

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
            self.video_path.set(file_path)
            self.status_var.set("Extracting final product frame...")
            self.progress.start()
            thread = threading.Thread(target=self.extract_final_frame_thread, args=(file_path,))
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
        scale_str = 'scale=-2:720' if max(width, height) > 720 else 'scale=trunc(iw/2)*2:trunc(ih/2)*2'
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-vf', scale_str,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '28',
            '-an',  # strip audio
            processed_path
        ]
        subprocess.run(cmd, check=True)
        # Notify user that conversion is done
        self.status_var.set("Video processing complete. Beginning assessment...")
        self.root.update_idletasks()
        return processed_path

    def extract_final_frame_thread(self, video_path):
        # Always extract final frame from original video
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
            self.root.after(0, lambda: self._final_frame_result(found, candidate_path))
        else:
            # No suitable frame found: warn and offer manual selection
            self.root.after(0, lambda: self._manual_frame_selection(video_path))

    def _manual_frame_selection(self, video_path):
        import cv2
        from PIL import Image, ImageTk
        import tkinter as tk
        from tkinter import Toplevel, Label, Button, Scale, HORIZONTAL, messagebox
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            messagebox.showwarning("Final Product Not Accessible", "Could not find a suitable final product frame in the video.")
            return
        # Create a simple frame selection dialog
        sel_win = Toplevel(self.root)
        sel_win.title("Select Final Product Frame")
        sel_win.geometry("600x500")
        Label(sel_win, text="No suitable final product frame was found. Please select a frame manually.").pack(pady=10)
        img_label = Label(sel_win)
        img_label.pack(pady=10)
        def show_frame(idx):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                return
            # Resize for display
            h, w = frame.shape[:2]
            scale = 400 / max(h, w)
            disp = cv2.resize(frame, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
            img = Image.fromarray(cv2.cvtColor(disp, cv2.COLOR_BGR2RGB))
            tk_img = ImageTk.PhotoImage(img)
            img_label.configure(image=tk_img)
            img_label.image = tk_img
        def save_and_close():
            idx = slider.get()
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                messagebox.showerror("Error", "Could not extract selected frame.")
                sel_win.destroy()
                return
            # Resize so long side is 1024 pixels
            h, w = frame.shape[:2]
            if h > w:
                new_h = 1024
                new_w = int(w * (1024 / h))
            else:
                new_w = 1024
                new_h = int(h * (1024 / w))
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            candidate_path = os.path.splitext(video_path)[0] + "_final_frame.png"
            cv2.imwrite(candidate_path, resized)
            sel_win.destroy()
            self._final_frame_result(True, candidate_path)
        slider = Scale(sel_win, from_=0, to=total_frames-1, orient=HORIZONTAL, length=500, command=lambda idx: show_frame(int(idx)))
        slider.set(total_frames-1)
        slider.pack(pady=10)
        Button(sel_win, text="Use This Frame", command=save_and_close).pack(pady=10)
        show_frame(total_frames-1)

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
        thread = threading.Thread(target=self._run_assessment_thread)
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

    def _run_assessment_thread(self):
        """Run suturing assessment in background thread"""
        try:
            assert self.assessor is not None
            suture_type = self.suture_type.get()
            # Only preprocess if over 200MB
            video_path = self.video_path.get()
            if os.path.getsize(video_path) > 200 * 1024 * 1024:
                self.status_var.set("Processing video for Gemini API size limits...")
                self.root.update_idletasks()
                video_path = self.preprocess_video(video_path)
            if self.final_frame_path is None:
                self.root.after(0, lambda: self._show_error("No final product image available for assessment"))
                return
            result = self.assessor.assess_video(self.final_frame_path, None, suture_type, video_path)
            self.root.after(0, lambda: self._display_assessment_result(result))
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self._show_error(f"Assessment failed: {error_msg}"))

    def _display_assessment_result(self, result):
        """Display suturing assessment results with improved formatting."""
        self.last_result = result  # Store for PDF export
        self.progress.stop()
        self.status_var.set("Assessment completed")
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

    def _display_final_product_images(self):
        """Display the reference and student final product images side by side above the assessment text. Both images are clickable to enlarge."""
        # Remove any previous image frames
        if hasattr(self, 'image_frame') and self.image_frame:
            self.image_frame.destroy()
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
        """Generate a PDF report of the assessment, including images, scores, comments, and metadata. Handles new assessment format."""
        import datetime
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from tkinter import filedialog
        import io
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
        # Assessment output (no duplicate headings)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Assessment Results:")
        y -= 20
        c.setFont("Helvetica", 10)
        assessment_text = None
        if isinstance(assessment, dict) and 'vop_assessment' in assessment:
            assessment_text = assessment['vop_assessment']
        else:
            assessment_text = str(assessment)
        # Remove duplicate headings from assessment_text
        import re
        assessment_text = re.sub(r"SUTURING ASSESSMENT RESULTS.*?={10,}\n+", "", assessment_text, flags=re.DOTALL)
        # Word wrap assessment text
        from reportlab.lib.utils import simpleSplit
        max_width = width - 80
        for line in assessment_text.splitlines():
            wrapped = simpleSplit(line.strip(), "Helvetica", 10, max_width)
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
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width // 2, y, "Student Final Product:")
        y -= 20
        if self.final_frame_path and os.path.exists(self.final_frame_path):
            img_w, img_h = 600, 450
            x = (width - img_w) // 2
            c.drawImage(self.final_frame_path, x, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, mask='auto')
        
        # Page 3: Reference Image (centered, enlarged)
        c.showPage()
        y = height - 60
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width // 2, y, "Reference Image:")
        y -= 20
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
        messagebox.showinfo("PDF Saved", f"PDF report saved to: {pdf_path}")
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
        """Initiate batch assessment of multiple videos in a single folder"""
        from pathlib import Path
        
        folder_path = filedialog.askdirectory(title="Select Folder with Videos")
        if not folder_path:
            return
        
        # Get all video files
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.m4v']
        video_files = []
        for ext in video_extensions:
            video_files.extend(Path(folder_path).glob(f"*{ext}"))
        
        if not video_files:
            messagebox.showwarning("No Videos Found", "No video files found in selected folder")
            return
        
        # Confirm with user
        result = messagebox.askyesno("Confirm Batch Assessment", 
                                    f"Assess {len(video_files)} videos as {self.suture_type.get()} sutures?\n\n"
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
            
            # Check for video files
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.m4v']
            video_files = []
            for ext in video_extensions:
                video_files.extend(Path(folder_path).glob(f"*{ext}"))
            
            if not video_files:
                messagebox.showwarning("No Videos Found", f"No video files found in {folder_path}")
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
            
            # Process videos in this folder
            for video_idx, video_file in enumerate(video_files):
                current_video_global += 1
                current_video_in_folder = video_idx + 1
                
                try:
                    # Update status on main thread
                    self.root.after(0, lambda v=video_file.name, f=folder_name, cg=current_video_global, 
                                   cf=current_video_in_folder, tf=len(video_files), tg=total_videos: 
                                   self.status_var.set(f"Processing {f}: {v} ({cf}/{tf}) - Total: {cg}/{tg}"))
                    
                    # Use existing assessment logic with specific suture type
                    result = self._assess_single_video_with_type(str(video_file), suture_type)
                    
                    if result:
                        # Generate PDF using existing method
                        pdf_path = self._generate_batch_pdf_with_type(result, str(video_file), folder_path, suture_type)
                        successful_assessments += 1
                        self.root.after(0, lambda v=video_file.name, f=folder_name, cg=current_video_global, 
                                       cf=current_video_in_folder, tf=len(video_files), tg=total_videos: 
                                       self.status_var.set(f"Completed {f}: {v} ({cf}/{tf}) - Total: {cg}/{tg} - PDF saved"))
                    else:
                        failed_assessments += 1
                        self.root.after(0, lambda v=video_file.name, f=folder_name, cg=current_video_global, 
                                       cf=current_video_in_folder, tf=len(video_files), tg=total_videos: 
                                       self.status_var.set(f"Failed to assess {f}: {v} ({cf}/{tf}) - Total: {cg}/{tg}"))
                    
                except Exception as e:
                    failed_assessments += 1
                    self.root.after(0, lambda v=video_file.name, f=folder_name, cg=current_video_global, 
                                   cf=current_video_in_folder, tf=len(video_files), tg=total_videos, err=str(e): 
                                   self.status_var.set(f"Error processing {f}: {v} ({cf}/{tf}) - Total: {cg}/{tg}: {err}"))
                    print(f"Error processing {video_file.name}: {e}")
        
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
            # Validate inputs
            if not video_path or not os.path.exists(video_path):
                return None
            
            if not suture_type:
                return None
            
            api_key = self.api_key.get().strip()
            if not api_key:
                return None
            
            # Initialize assessor
            self.assessor = SuturingAssessor(api_key)
            
            # Extract final frame
            final_frame_path = self._extract_final_frame_for_batch(video_path)
            if not final_frame_path:
                return None
            
            # Preprocess video if needed
            processed_video_path = self.preprocess_video(video_path)
            
            # Run assessment with specified suture type
            result = self.assessor.assess_vop(processed_video_path, final_frame_path, None, suture_type)
            
            # Clean up processed video if it was created
            if processed_video_path != video_path and os.path.exists(processed_video_path):
                try:
                    os.remove(processed_video_path)
                except:
                    pass
            
            # Clean up final frame
            if os.path.exists(final_frame_path):
                try:
                    os.remove(final_frame_path)
                except:
                    pass
            
            return result
            
        except Exception as e:
            print(f"Error in _assess_single_video_with_type: {e}")
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
        
        # Assessment output
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Assessment Results:")
        y -= 20
        c.setFont("Helvetica", 10)
        
        assessment_text = None
        if isinstance(assessment, dict) and 'vop_assessment' in assessment:
            assessment_text = assessment['vop_assessment']
        else:
            assessment_text = str(assessment)
        
        # Remove duplicate headings
        import re
        assessment_text = re.sub(r"SUTURING ASSESSMENT RESULTS.*?={10,}\n+", "", assessment_text, flags=re.DOTALL)
        
        # Word wrap assessment text
        max_width = width - 80
        for line in assessment_text.splitlines():
            wrapped = simpleSplit(line.strip(), "Helvetica", 10, max_width)
            for wline in wrapped:
                if y < 60:
                    c.showPage()
                    y = height - 40
                    c.setFont("Helvetica", 10)
                c.drawString(40, y, wline)
                y -= 12
        
        c.save()
        return pdf_path

    def _generate_batch_pdf(self, assessment, video_path, output_folder):
        """Generate PDF for batch processing (legacy method)"""
        return self._generate_batch_pdf_with_type(assessment, video_path, output_folder, self.suture_type.get())

def main():
    root = tk.Tk()
    app = SuturingAssessmentGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 