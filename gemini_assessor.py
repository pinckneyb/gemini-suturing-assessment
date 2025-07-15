import os
import json
from pathlib import Path
from typing import Dict, List, Any
import base64
import time

class SuturingAssessor:
    def __init__(self, api_key: str):
        """Initialize the suturing assessor with Gemini API"""
        from google import genai
        from google.genai import types
        self.client = genai.Client(api_key=api_key)
        self.types = types
        # Use gemini-2.5-pro for video analysis
        self.model = 'models/gemini-2.5-pro'
        
        # Suture types and their assessment criteria
        self.suture_types = {
            "simple_interrupted": "Simple Interrupted Suture",
            "vertical_mattress": "Vertical Mattress Suture", 
            "subcuticular": "Subcuticular Suture"
        }
        
        # VoP Assessment Criteria based on actual checklist
        self.vop_criteria = {
            "simple_interrupted": [
                "Passes needle perpendicular to skin on both sides of skin",
                "Avoids multiple forceps grasps of skin",
                "Instrument ties with square knots",
                "Approximates skin with appropriate tension",
                "Places sutures 0.5 - 1.0 cm apart",
                "Eversion of the skin edges",
                "Economy of Time and Motion",
                "Final Rating / Demonstrates Proficiency"
            ]
        }
    



    
    def _get_mime_type(self, file_path: str) -> str:
        """Determine the correct MIME type based on file extension"""
        import mimetypes
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # Map common video extensions to MIME types
        mime_type_map = {
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.mkv': 'video/x-matroska',
            '.wmv': 'video/x-ms-wmv',
            '.m4v': 'video/x-m4v',
            '.webm': 'video/webm',
            '.flv': 'video/x-flv'
        }
        
        # Try to get MIME type from our map first
        if file_extension in mime_type_map:
            return mime_type_map[file_extension]
        
        # Fallback to Python's mimetypes module
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith('video/'):
            return mime_type
        
        # Default fallback
        return 'video/mp4'



    def assess_video(self, final_image_path: str, ref_image_path: str | None, suture_type: str, video_path: str) -> dict:
        """Wrapper to call assess_vop for compatibility with the rest of the app."""
        return self.assess_vop(video_path, final_image_path, ref_image_path, suture_type)
    


    def assess_vop(self, video_path: str, final_image_path: str, ref_image_path: str | None, suture_type: str) -> dict:
        import json
        import os
        # Enforce suture type must be known
        if not suture_type or suture_type not in ["simple_interrupted", "vertical_mattress", "subcuticular"]:
            return {"error": "Suture type is unknown or not supported. Please select a valid suture type before assessment."}
        
        # Map rubric points to VIDEO or STILL for each suture type
        # Simple interrupted and vertical mattress:
        # 1. Passes needle perpendicular to skin on both sides - VIDEO
        # 2. Avoids multiple forceps grasps of skin - VIDEO  
        # 3. Instrument ties with square knots - VIDEO
        # 4. Approximates skin with appropriate tension - STILL
        # 5. Places sutures 0.5–1.0 cm apart - STILL
        # 6. Eversion of the skin edges - STILL
        # 7. Economy of time and motion - VIDEO
        #
        # Subcuticular (different criteria):
        # 1. Runs the suture, placing appropriate bites into dermal layer - VIDEO
        # 2. Enters the dermal layer directly across from exit site - VIDEO
        # 3. Avoids multiple penetration of the dermis - VIDEO
        # 4. Avoids multiple forceps grasps of skin - VIDEO
        # 5. Instrument ties with square knots - VIDEO
        # 6. Approximates skin with appropriate tension - STILL
        # 7. Economy of time and motion - VIDEO
        rubric_map = {
            "simple_interrupted": ["VIDEO", "VIDEO", "VIDEO", "STILL", "STILL", "STILL", "VIDEO"],
            "vertical_mattress": ["VIDEO", "VIDEO", "VIDEO", "STILL", "STILL", "STILL", "VIDEO"],
            "subcuticular": ["VIDEO", "VIDEO", "VIDEO", "VIDEO", "VIDEO", "STILL", "VIDEO"]
        }
        
        vop_files = {
            "simple_interrupted": "simple_interrupted_VoP_assessment.txt",
            "vertical_mattress": "vertical_mattress_VoP_assessment.txt",
            "subcuticular": "subcuticular_VoP_assessment.txt"
        }
        vop_path = vop_files.get(suture_type)
        if not vop_path or not os.path.exists(vop_path):
            raise FileNotFoundError(f"VoP rubric for {suture_type} not found.")
        with open(vop_path, 'r', encoding='utf-8') as f:
            vop_text = f.read()
        import re
        rubric_points = re.findall(r"\d+\)\s.*", vop_text)
        
        # Prepare results
        results = []
        rating_labels = {1: 'poor', 2: 'substandard', 3: 'competent', 4: 'proficient', 5: 'exemplary'}
        
        # For each rubric point 1-7, assess using the correct modality
        for idx, point in enumerate(rubric_points[:7]):
            # Strip leading number/parenthesis from rubric point
            point_text = re.sub(r'^\d+\)\s*', '', point).strip()
            mode = rubric_map[suture_type][idx]
            
            if mode == "VIDEO":
                # Assess video-based criteria
                prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture. 

Assess this specific rubric point: {idx+1}) {point_text}

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a single clinical, skeptical, actionable justification. 

Most scores should be 3 (competent); use 4 only for clearly above-average, and 5 only for near-perfect. Be clinical and skeptical, avoid superlatives, and always provide actionable advice. 

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Do not add any extra labels or commentary.
"""
                with open(video_path, 'rb') as f:
                    video_bytes = f.read()
                content = self.types.Content(parts=[
                    self.types.Part.from_bytes(data=video_bytes, mime_type=self._get_mime_type(video_path)),
                    self.types.Part.from_text(text=prompt)
                ])
            else:  # STILL
                # Assess still image-based criteria (no reference image comparison)
                prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture. 

Assess this specific rubric point: {idx+1}) {point_text}

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a single clinical, skeptical, actionable justification. 

Most scores should be 3 (competent); use 4 only for clearly above-average, and 5 only for near-perfect. Be clinical and skeptical, avoid superlatives, and always provide actionable advice. 

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Do not add any extra labels or commentary.
"""
                with open(final_image_path, 'rb') as f:
                    img_bytes = f.read()
                content = self.types.Content(parts=[
                    self.types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                    self.types.Part.from_text(text=prompt)
                ])
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=[content]
            )
            response_text = getattr(response, 'text', str(response))
            results.append(response_text.strip())
        
        # Calculate final score as simple average of all 7 rubric scores
        import re
        rubric_scores = []
        for r in results[:7]:
            match = re.search(r"(\d)/(5)\s+(poor|substandard|competent|proficient|exemplary)", r, re.IGNORECASE)
            if match:
                rubric_scores.append(int(match.group(1)))
        
        if len(rubric_scores) == 7:
            # Simple average of all 7 scores
            final_score = sum(rubric_scores) / len(rubric_scores)
            # Rounding: round down below x.5, up at x.5 or above
            if final_score - int(final_score) < 0.5:
                final_score = int(final_score)
            else:
                final_score = int(final_score) + 1
            # Clamp to 1-5
            final_score = max(1, min(5, final_score))
            # Rating label
            label = rating_labels.get(final_score, "")
            final_score_text = f"Final Score: {final_score}/5 {label}"
        else:
            final_score_text = "Final Score: ERROR - Could not calculate"
        
        # Summative comment
        prompt9 = f"""
You are an expert surgical educator. Write a single, readable paragraph labeled 'Summative Comment:' that provides specific, evidence-based, and actionable feedback for this {suture_type.replace('_', ' ')} suture. Do not add any extra labels or commentary.
"""
        with open(video_path, 'rb') as f:
            video_bytes = f.read()
        with open(final_image_path, 'rb') as f:
            img_bytes = f.read()
        content9 = self.types.Content(parts=[
            self.types.Part.from_bytes(data=video_bytes, mime_type=self._get_mime_type(video_path)),
            self.types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
            self.types.Part.from_text(text=prompt9)
        ])
        response9 = self.client.models.generate_content(
            model=self.model,
            contents=[content9]
        )
        response9_text = getattr(response9, 'text', str(response9))
        
        # Combine all results into a single formatted string
        header = f"SUTURING ASSESSMENT RESULTS\nVideo File: {os.path.basename(video_path)}\nSuture Type: {suture_type.replace('_', ' ').title()}\n{'='*50}\n\n"
        assessment = header + "\n\n".join(results) + f"\n\n{final_score_text}\n\n{response9_text.strip()}"

        return {"vop_assessment": assessment, "suture_type": suture_type, "video_file": os.path.basename(video_path)}

from google import genai
from google.genai import types
import os

def wait_for_file_active(client, uploaded_file, timeout=120, poll_interval=2):
    """Wait until the uploaded file is ACTIVE or timeout is reached."""
    start = time.time()
    while time.time() - start < timeout:
        # Check the file state directly from the uploaded file object
        if hasattr(uploaded_file, 'state') and uploaded_file.state == "ACTIVE":
            return
        elif hasattr(uploaded_file, 'state') and uploaded_file.state == "FAILED":
            raise RuntimeError(f"File failed to process.")
        
        # If we can't check state directly, just wait a bit and assume it's ready
        # This is a fallback for when the file object doesn't expose state
        time.sleep(poll_interval)
        
        # After waiting, try to refresh the file info if possible
        try:
            # Try to get updated file info - this might work differently
            if hasattr(client.files, 'list'):
                files = client.files.list()
                for file in files:
                    if hasattr(uploaded_file, 'name') and file.name == uploaded_file.name:
                        if hasattr(file, 'state') and file.state == "ACTIVE":
                            return
                        elif hasattr(file, 'state') and file.state == "FAILED":
                            raise RuntimeError(f"File failed to process.")
        except Exception:
            # If we can't check file status, just continue waiting
            pass
    
    # If we reach here, assume the file is ready (timeout reached)
    print(f"Warning: File status check timed out after {timeout} seconds. Proceeding anyway.")
    return 