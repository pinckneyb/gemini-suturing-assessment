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
    
    def create_assessment_prompt(self, suture_type: str, final_image_path: str, ref_image_path: str) -> str:
        """Create a comprehensive prompt for suturing assessment based on actual VoP checklist, including final product image comparison."""
        suture_name = self.suture_types.get(suture_type, suture_type)
        rubric_text = self._get_final_product_rubric(suture_type)
        
        prompt = f"""
You are an expert surgical educator assessing a {suture_name.upper()} procedure.

IMPORTANT: The user has specified this is a {suture_name}. Base your entire assessment on this specific technique, not on what you think the video shows.

You are provided with:
- A still image of the final product from the student's video (the student's completed suture)
- A reference image of an ideal final product for this suture type
- A detailed text rubric describing what a good final product should look like for this suture type

**Assessment Steps:**
1. Describe the student's final product image in detail.
2. Compare the student's final product image to the reference image and the rubric. Note similarities and differences.
3. Assign a "final product" score (1-5 Likert) based on how closely the student's result matches the reference and rubric. This score should account for 60% of the overall grade.
4. Score the 7 VoP criteria for this suture type (1-5 Likert each), with a specific, actionable, evidence-based comment for each. These scores together account for 40% of the overall grade.
5. Write a summative comment that references specific moments or features in the video, highlights strengths and weaknesses, and gives concrete, actionable suggestions for improvement. Do not give generic advice.
6. Combine the final product score (60%) and the average of the 7 VoP scores (40%) into a single overall score (1-5 Likert). Most scores should be 3s and 4s; 5 is rare, 1 is for dangerous/disastrous results only.

**Rubric for a good final product:**
{rubric_text}

**Output format:**
Respond with ONLY a valid JSON object in this format:
{{
  "final_product_description": "...",
  "final_product_comparison": "...",
  "final_product_score": 3,
  "vop_scores": {{
    "criterion_1": {{"score": 3, "comment": "..."}},
    "criterion_2": {{"score": 3, "comment": "..."}},
    ...
    "criterion_7": {{"score": 3, "comment": "..."}}
  }},
  "overall_score": 3,
  "summative_comment": "..."
}}
REMEMBER: Respond with ONLY the JSON object, no other text.
"""
        return prompt

    def _get_final_product_rubric(self, suture_type: str) -> str:
        rubric_files = {
            "simple_interrupted": "simple_interrupted_final_product_rubric.txt",
            "vertical_mattress": "vertical_mattress_final_product_rubric.txt",
            "subcuticular": "subcuticular_final_product_rubric.txt"
        }
        rubric_path = rubric_files.get(suture_type)
        if rubric_path and os.path.exists(rubric_path):
            with open(rubric_path, 'r', encoding='utf-8') as f:
                return f.read()
        return "(No rubric found)"
    
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

    def generate_image_description(self, image_path: str, suture_type: str) -> dict:
        """Generate a technical JSON description for a given image using Gemini 2.5, covering all rubric points that can be evaluated from a static image."""
        import json
        rubric_text = self._get_final_product_rubric(suture_type)
        prompt = f"""
You are an expert surgical educator. Describe this image of a {suture_type.replace('_', ' ')} suture in purely technical, objective terms, covering every aspect of the rubric that can be evaluated from a static image. Output ONLY a comprehensive JSON object with all relevant features and measurements, suitable for programmatic comparison. Do not include any instructional or second-person language.

Rubric:
{rubric_text}

Respond with ONLY the JSON object, no other text.
"""
        with open(image_path, 'rb') as f:
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
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            raise ValueError("Gemini did not return a valid JSON object for the image description.")
        json_str = json_match.group()
        return json.loads(json_str)

    def compare_image_descriptions(self, ref_json: dict, student_json: dict, suture_type: str) -> dict:
        """Compare the reference and student image JSONs and generate a 9-point VoP assessment for the selected suture type. Output is formatted for clarity and matches the VoP framework."""
        import json
        # Load the correct VoP rubric for the suture type
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
        # Extract the 9 rubric points
        import re
        rubric_points = re.findall(r"\d+\)\s.*", vop_text)
        # Compose the prompt for Gemini
        prompt = f"""
You are an expert surgical educator. Compare the following two technical JSON descriptions of a {suture_type.replace('_', ' ')} suture: one from a reference image, one from a student's final product. Use the 9-point Verification of Proficiency (VoP) framework below. For points 1-7, print the rubric point, the Likert score (1-5/5), and a single technical justification. For point 8, print the overall proficiency Likert score. For point 9, print the summative commentary, which must be concrete, evidence-based, and actionable. Format the output for clarity, with each point clearly separated.

VoP Rubric Points:
"""
        for i, point in enumerate(rubric_points, 1):
            prompt += f"{i}. {point}\n"
        prompt += f"\nReference JSON:\n{json.dumps(ref_json, indent=2)}\n\nStudent JSON:\n{json.dumps(student_json, indent=2)}\n\nRespond with ONLY the formatted 9-point assessment, no extra text."
        # Use only text input for this comparison
        response = self.client.models.generate_content(
            model=self.model,
            contents=[self.types.Content(parts=[self.types.Part.from_text(text=prompt)])]
        )
        response_text = getattr(response, 'text', str(response))
        return {"static_image_assessment": response_text}

    def assess_video(self, final_image_path: str, ref_image_path: str, suture_type: str, video_path: str) -> dict:
        """Wrapper to call assess_vop for compatibility with the rest of the app."""
        return self.assess_vop(video_path, final_image_path, ref_image_path, suture_type)
    
    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract assessment information from text response when JSON parsing fails"""
        assessment = {
            "needle_perpendicular": "ERROR",
            "avoids_multiple_grasps": "ERROR",
            "square_knots": "ERROR",
            "appropriate_tension": "ERROR",
            "suture_spacing": "ERROR",
            "skin_eversion": "ERROR",
            "economy_of_motion": "ERROR",
            "demonstrates_proficiency": "ERROR",
            "summative_comments": text
        }
        
        # Try to extract Yes/No answers from text
        text_lower = text.lower()
        
        # Look for specific patterns
        if "needle perpendicular" in text_lower or "perpendicular" in text_lower:
            if "yes" in text_lower and "no" not in text_lower:
                assessment["needle_perpendicular"] = "Yes"
            elif "no" in text_lower:
                assessment["needle_perpendicular"] = "No"
        
        if "forceps" in text_lower or "grasps" in text_lower:
            if "avoids" in text_lower or "yes" in text_lower:
                assessment["avoids_multiple_grasps"] = "Yes"
            elif "no" in text_lower:
                assessment["avoids_multiple_grasps"] = "No"
        
        if "square knots" in text_lower or "knots" in text_lower:
            if "yes" in text_lower:
                assessment["square_knots"] = "Yes"
            elif "no" in text_lower:
                assessment["square_knots"] = "No"
        
        if "tension" in text_lower or "appropriate" in text_lower:
            if "yes" in text_lower:
                assessment["appropriate_tension"] = "Yes"
            elif "no" in text_lower:
                assessment["appropriate_tension"] = "No"
        
        if "spacing" in text_lower or "0.5" in text_lower or "1.0" in text_lower:
            if "yes" in text_lower:
                assessment["suture_spacing"] = "Yes"
            elif "no" in text_lower:
                assessment["suture_spacing"] = "No"
        
        if "eversion" in text_lower or "skin edges" in text_lower:
            if "yes" in text_lower:
                assessment["skin_eversion"] = "Yes"
            elif "no" in text_lower:
                assessment["skin_eversion"] = "No"
        
        # Economy of motion
        if "maximum economy" in text_lower or "efficiency" in text_lower:
            assessment["economy_of_motion"] = "Maximum economy of movement and efficiency"
        elif "organized" in text_lower and "unnecessary" in text_lower:
            assessment["economy_of_motion"] = "Organized time / motion, some unnecessary movements"
        elif "unnecessary" in text_lower or "disorganized" in text_lower:
            assessment["economy_of_motion"] = "Many unnecessary / disorganized movements"
        
        # Overall proficiency
        if "proficiency" in text_lower or "pass" in text_lower:
            if "yes" in text_lower:
                assessment["demonstrates_proficiency"] = "Yes"
            elif "no" in text_lower:
                assessment["demonstrates_proficiency"] = "No"
        
        return assessment 

    def get_reference_image_description(self, suture_type: str) -> dict:
        """Get or generate the technical JSON description for the reference image of the given suture type."""
        import json
        import os
        # Map suture type to reference image and JSON path
        ref_image_map = {
            "simple_interrupted": "simple_interrupted_final_product.png",
            "vertical_mattress": "vertical_mattress_final_product.png",
            "subcuticular": "subcuticular_final_product.png"
        }
        json_map = {
            "simple_interrupted": "simple_interrupted_reference_description.json",
            "vertical_mattress": "vertical_mattress_reference_description.json",
            "subcuticular": "subcuticular_reference_description.json"
        }
        ref_image_path = ref_image_map.get(suture_type)
        json_path = json_map.get(suture_type)
        if ref_image_path is None or json_path is None:
            raise ValueError(f"No reference image or JSON mapping for suture type: {suture_type}")
        if not os.path.exists(ref_image_path):
            raise FileNotFoundError(f"Reference image for {suture_type} not found.")
        # If JSON exists, load and return
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        # Otherwise, generate using Gemini 2.5
        rubric_text = self._get_final_product_rubric(suture_type)
        prompt = f"""
You are an expert surgical educator. Describe the reference image of an ideal {suture_type.replace('_', ' ')} suture in purely technical, objective terms, covering every aspect of the rubric that can be evaluated from a static image. Output ONLY a comprehensive JSON object with all relevant features and measurements, suitable for programmatic comparison. Do not include any instructional or second-person language.

Rubric:
{rubric_text}

Respond with ONLY the JSON object, no other text.
"""
        with open(ref_image_path, 'rb') as f:
            ref_img_bytes = f.read()
        content = self.types.Content(parts=[
            self.types.Part.from_bytes(data=ref_img_bytes, mime_type='image/png'),
            self.types.Part.from_text(text=prompt)
        ])
        response = self.client.models.generate_content(
            model=self.model,
            contents=[content]
        )
        response_text = getattr(response, 'text', str(response))
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            raise ValueError("Gemini did not return a valid JSON object for the reference image description.")
        json_str = json_match.group()
        ref_json = json.loads(json_str)
        # Save for future use
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(ref_json, f, indent=2)
        return ref_json

    def assess_vop(self, video_path: str, final_image_path: str, ref_image_path: str, suture_type: str) -> dict:
        import json
        import os
        # Enforce suture type must be known
        if not suture_type or suture_type not in ["simple_interrupted", "vertical_mattress", "subcuticular"]:
            return {"error": "Suture type is unknown or not supported. Please select a valid suture type before assessment."}
        # Map rubric points to VIDEO or STILL for each suture type
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
        # For each rubric point 1-7, assess using the correct modality
        rating_labels = {1: 'poor', 2: 'substandard', 3: 'competent', 4: 'proficient', 5: 'exemplary'}
        for idx, point in enumerate(rubric_points[:7]):
            # Strip leading number/parenthesis from rubric point
            import re
            point_text = re.sub(r'^\d+\)\s*', '', point).strip()
            mode = rubric_map[suture_type][idx]
            prompt = f"""
You are an expert surgical educator. For the following {suture_type.replace('_', ' ')} suture, assess the rubric point below. Print the number and rubric point, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a single clinical, skeptical, actionable justification (no label). Most scores should be 3 (competent); use 4 only for clearly above-average, and 5 only for near-perfect. Be clinical and skeptical, avoid superlatives, and always provide actionable advice. Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary. Do not add any extra labels or commentary.

Rubric Point: {idx+1}) {point_text}
"""
            if mode == "VIDEO":
                with open(video_path, 'rb') as f:
                    video_bytes = f.read()
                content = self.types.Content(parts=[
                    self.types.Part.from_bytes(data=video_bytes, mime_type=self._get_mime_type(video_path)),
                    self.types.Part.from_text(text=prompt)
                ])
            else:  # STILL
                with open(final_image_path, 'rb') as f:
                    stu_img_bytes = f.read()
                with open(ref_image_path, 'rb') as f:
                    ref_img_bytes = f.read()
                content = self.types.Content(parts=[
                    self.types.Part.from_bytes(data=stu_img_bytes, mime_type='image/png'),
                    self.types.Part.from_bytes(data=ref_img_bytes, mime_type='image/png'),
                    self.types.Part.from_text(text=prompt)
                ])
            response = self.client.models.generate_content(
                model=self.model,
                contents=[content]
            )
            response_text = getattr(response, 'text', str(response))
            results.append(response_text.strip())
        # Point 8: overall proficiency (final score, labeled, no explanation)
        prompt8 = f"""
You are an expert surgical educator. Based on the video and final product image, assign a single overall proficiency Likert score (1-5/5) for this {suture_type.replace('_', ' ')} suture. The final product image (cosmetic/spacing/tension items) should count for 40% of the total grade, and the process/motion-based (video) measures should count for 60%. Print only the score as 'Final Score: x/5' (no explanation, no label, no extra text).
"""
        with open(video_path, 'rb') as f:
            video_bytes = f.read()
        with open(final_image_path, 'rb') as f:
            stu_img_bytes = f.read()
        content8 = self.types.Content(parts=[
            self.types.Part.from_bytes(data=video_bytes, mime_type=self._get_mime_type(video_path)),
            self.types.Part.from_bytes(data=stu_img_bytes, mime_type='image/png'),
            self.types.Part.from_text(text=prompt8)
        ])
        response8 = self.client.models.generate_content(
            model=self.model,
            contents=[content8]
        )
        response8_text = getattr(response8, 'text', str(response8))
        results.append(response8_text.strip())
        # Point 9: summative comment
        prompt9 = f"""
You are an expert surgical educator. Write a single, readable paragraph labeled 'Summative Comment:' that provides specific, evidence-based, and actionable feedback for this {suture_type.replace('_', ' ')} suture, referencing the video and final product image. Do not add any extra labels or commentary.
"""
        content9 = self.types.Content(parts=[
            self.types.Part.from_bytes(data=video_bytes, mime_type=self._get_mime_type(video_path)),
            self.types.Part.from_bytes(data=stu_img_bytes, mime_type='image/png'),
            self.types.Part.from_text(text=prompt9)
        ])
        response9 = self.client.models.generate_content(
            model=self.model,
            contents=[content9]
        )
        response9_text = getattr(response9, 'text', str(response9))
        results.append(response9_text.strip())
        # Combine all results into a single formatted string
        header = f"SUTURING ASSESSMENT RESULTS\nVideo File: {os.path.basename(video_path)}\nSuture Type: {suture_type.replace('_', ' ').title()}\n{'='*50}\n\n"
        assessment = header + "\n\n".join(results)

        # --- Begin: Calculate final score in code ---
        import re
        # Extract rubric scores (1-5) from the first 7 rubric points
        rubric_scores = []
        for r in results[:7]:
            match = re.search(r"(\d)/(5)\s+(poor|substandard|competent|proficient|exemplary)", r, re.IGNORECASE)
            if match:
                rubric_scores.append(int(match.group(1)))
        # Extract final product score (from rubric point 5 or 6 depending on suture type)
        # For now, use rubric point 5 as final product (cosmetic/spacing/tension) and the rest as process
        # If rubric_map is more complex, adjust accordingly
        if len(rubric_scores) == 7:
            # Cosmetic/spacing/tension = points 4,5,6 (STILL), process = rest (VIDEO)
            if suture_type in ["simple_interrupted", "vertical_mattress"]:
                still_indices = [3,4,5]  # 0-based
            elif suture_type == "subcuticular":
                still_indices = [5]  # Only point 6 is STILL
            else:
                still_indices = []
            still_scores = [rubric_scores[i] for i in still_indices]
            process_scores = [rubric_scores[i] for i in range(7) if i not in still_indices]
            # Average
            if still_scores:
                final_product_avg = sum(still_scores) / len(still_scores)
            else:
                final_product_avg = 0
            if process_scores:
                process_avg = sum(process_scores) / len(process_scores)
            else:
                process_avg = 0
            # Weighting: 40% final product, 60% process
            weighted = 0.4 * final_product_avg + 0.6 * process_avg
            # Rounding: round down below x.5, up at x.5 or above
            if weighted - int(weighted) < 0.5:
                final_score = int(weighted)
            else:
                final_score = int(weighted) + 1
            # Clamp to 1-5
            final_score = max(1, min(5, final_score))
            # Rating label
            rating_labels = {1: 'poor', 2: 'substandard', 3: 'competent', 4: 'proficient', 5: 'exemplary'}
            label = rating_labels.get(final_score, "")
            # Replace or append the final score in the assessment output
            import re
            assessment = re.sub(r"Final Score: \d/5.*", f"Final Score: {final_score}/5 {label}", assessment)
        # --- End: Calculate final score in code ---

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