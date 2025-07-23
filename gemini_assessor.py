import os
import json
import re
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

        # Load rubric definitions from JSON config
        rubric_path = os.path.join(os.path.dirname(__file__), 'rubric_definitions_filled.JSON')
        try:
            with open(rubric_path, 'r', encoding='utf-8') as f:
                self.rubric_definitions = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load rubric definitions: {e}")
            self.rubric_definitions = {}

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
    


    def assess_vop(self, video_path: str, final_image_path: str, ref_image_path: str | None, suture_type: str, progress_callback=None, consensus=False, num_runs=1) -> dict:
        """Assess video using VoP (Verification of Proficiency) criteria with real-time progress updates. Supports consensus mode."""
        import copy
        # Define rubric points based on suture type
        rubric_points = {
            "simple_interrupted": [
                "1) Passes needle perpendicular to skin on both sides of skin",
                "2) Avoids multiple forceps grasps of skin", 
                "3) Instrument ties with square knots",
                "4) Approximates skin with appropriate tension",
                "5) Places sutures 0.5 - 1.0 centimeters apart",
                "6) Eversion of the skin edges",
                "7) Economy of time and motion"
            ],
            "vertical_mattress": [
                "1) Passes needle perpendicular to skin on both sides of skin",
                "2) Avoids multiple forceps grasps of skin",
                "3) Instrument ties with square knots", 
                "4) Approximates skin with appropriate tension",
                "5) Places sutures 0.5 - 1.0 centimeters apart",
                "6) Eversion of the skin edges",
                "7) Economy of time and motion"
            ],
            "subcuticular": [
                "1) Runs the suture, placing appropriate bites into the dermal layer",
                "2) Enters the dermal layer directly across from exit site",
                "3) Avoids multiple penetrations of the dermis",
                "4) Avoids multiple forceps grasps of skin",
                "5) Instrument ties with square knots",
                "6) Approximates skin with appropriate tension", 
                "7) Economy of time and motion"
            ]
        }
        
        # Define which rubric points are assessed from video vs still image
        rubric_map = {
            "simple_interrupted": ["VIDEO", "VIDEO", "VIDEO", "STILL", "STILL", "STILL", "VIDEO"],
            "vertical_mattress": ["VIDEO", "VIDEO", "VIDEO", "STILL", "STILL", "STILL", "VIDEO"],
            "subcuticular": ["VIDEO", "VIDEO", "VIDEO", "VIDEO", "VIDEO", "STILL", "VIDEO"]
        }
        
        # Rating labels
        rating_labels = {
            1: "poor",
            2: "substandard", 
            3: "competent",
            4: "proficient",
            5: "exemplary"
        }
        
        # Process all prompts sequentially with progress updates
        results = []
        rubric_defs = self.rubric_definitions.get(suture_type, [])
        for i, point in enumerate(rubric_points[suture_type][:7]):
            if progress_callback:
                progress_callback(f"Assessing rubric point {i+1}/7: {point.split(')')[1].strip()}")
            
            # Strip leading number/parenthesis from rubric point
            point_text = re.sub(r'^\d+\)\s*', '', point).strip()
            mode = rubric_map[suture_type][i]
            
            # Build definition string if available
            defn = ""
            if i < len(rubric_defs) and isinstance(rubric_defs[i], dict):
                d = rubric_defs[i]
                # For eversion, use new definition (user will have filled in)
                defn_parts = []
                if d.get("what_you_assess"):
                    defn_parts.append(f"What you assess: {d['what_you_assess']}")
                if d.get("ideal_result"):
                    defn_parts.append(f"Ideal result: {d['ideal_result']}")
                defn = "\n".join(defn_parts)
            # Compose prompt
            tension_note = "NOTE: Approximates skin with appropriate tension is difficult to judge on these practice pads and so considerable latitude should be shown on those assessments."
            # Special prompt for subcuticular point 5 (spacing)
            spacing_note = """
NOTE for subcuticular spacing: Assess spacing based on surface clues. Examine for contour irregularities (e.g., bunching, dimpling), and whether skin edges are pulled unevenly or smoothly approximated. Deduct for obvious asymmetry, puckering, or irregular tension. Do NOT penalize for invisible bite spacing if the surface appears clean and symmetric."""
            if suture_type == "subcuticular" and i == 4:
                if defn:
                    prompt_addition = f"\n{defn}\n{spacing_note}"
                else:
                    prompt_addition = f"\n{spacing_note}"
            elif 'tension' in point_text.lower():
                if defn:
                    prompt_addition = f"\n{defn}\n{tension_note}"
                else:
                    prompt_addition = f"\n{tension_note}"
            else:
                if defn:
                    prompt_addition = f"\n{defn}"
                else:
                    prompt_addition = ""

            # Add instruction to avoid repeating rubric/ideal result and require observation
            observation_instruction = "Do not simply repeat the rubric or ideal result. Your comment must describe what is actually observed in the submitted video or image."
            if prompt_addition:
                prompt_addition += f"\n{observation_instruction}"
            else:
                prompt_addition = f"\n{observation_instruction}"

            if mode == "VIDEO":
                # Assess video-based criteria
                prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture.

Assess only this rubric point:

{i+1}) {point_text}{prompt_addition}

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a brief description of what was observed.

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

IMPORTANT: Scores 2-4 are the normal range. Reserve 1/5 for truly disastrous performance and 5/5 for exceptional work that could serve as a teaching example.

Scoring guidance:
- 5/5 exemplary: RARE - only for exceptional technique that could be used as a teaching example
- 4/5 proficient: Good performance with room for minor improvement
- 3/5 competent: Adequate performance, typical for learning students
- 2/5 substandard: Below average performance requiring improvement
- 1/5 poor: RARE - only for truly poor technique that shows fundamental misunderstanding

Keep the description brief and factual. Use neutral, objective language. Describe what is observed without superlatives or heavily inflected language. Simply state the technique characteristics and any issues noted.

Do not add any extra labels or commentary.
"""
                with open(video_path, 'rb') as f:
                    video_bytes = f.read()
                content = self.types.Content(parts=[
                    self.types.Part.from_bytes(data=video_bytes, mime_type=self._get_mime_type(video_path)),
                    self.types.Part.from_text(text=prompt)
                ])
            else:  # STILL
                # Assess still image-based criteria with specialized prompts for tension and eversion
                if "tension" in point_text.lower():
                    # Specialized, more lenient prompt for tension assessment
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture. 

Assess this specific rubric point: {i+1}) {point_text}{prompt_addition}

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a brief description of what was observed.

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

IMPORTANT: Be very lenient on tension assessment for PGY-1 learners. Minor puckering or slight blanching is normal and acceptable.

Scoring guidance for tension:
- 5/5 exemplary: RARE - perfect tension with no visible puckering or blanching
- 4/5 proficient: Good tension with minimal puckering or blanching
- 3/5 competent: Adequate tension, some minor puckering or blanching is acceptable and normal
- 2/5 substandard: Excessive tension causing significant puckering or blanching
- 1/5 poor: RARE - extreme tension causing tissue damage or ischemia

CRITICAL: Only score 2/5 or lower if there is clearly excessive tension causing significant tissue distortion. Minor puckering or slight blanching should be scored 3/5 or higher.

Keep the description brief and factual. Use neutral, objective language.
"""
                elif "eversion" in point_text.lower():
                    # Use new definition for eversion (user will have filled in)
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture. 

Assess this specific rubric point: {i+1}) {point_text}{prompt_addition}

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a brief description of what was observed.

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Keep the description brief and factual. Use neutral, objective language.
"""
                else:
                    # Standard prompt for other still image criteria
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture. 

Assess this specific rubric point: {i+1}) {point_text}{prompt_addition}

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a brief description of what was observed.

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

IMPORTANT: Scores 2-4 are the normal range. Reserve 1/5 for truly disastrous performance and 5/5 for exceptional work that could serve as a teaching example.

Scoring guidance:
- 5/5 exemplary: RARE - only for exceptional technique that could be used as a teaching example
- 4/5 proficient: Good performance with room for minor improvement
- 3/5 competent: Adequate performance, typical for learning students
- 2/5 substandard: Below average performance requiring improvement
- 1/5 poor: RARE - only for truly poor technique that shows fundamental misunderstanding

Keep the description brief and factual. Use neutral, objective language. Describe what is observed without superlatives or heavily inflected language. Simply state the technique characteristics and any issues noted.

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
                contents=[content],
                config={"temperature": 0.1}
            )
            response_text = getattr(response, 'text', str(response))
            results.append(response_text.strip())
        
        # Calculate final score as simple average of all 7 rubric scores
        rubric_scores = []
        rubric_justifications = []
        original_scores = []  # Store original AI scores for comparison
        
        for r in results[:7]:
            # Only keep the first valid score and its associated comment
            match = re.search(r"(\d)/(5)\s+(poor|substandard|competent|proficient|exemplary)", r, re.IGNORECASE)
            if match:
                original_score = int(match.group(1))
                original_scores.append(original_score)
                # Extract the description (everything after the first valid score line)
                lines = r.strip().split('\n')
                # Find the first valid score line
                score_line_idx = None
                for idx, line in enumerate(lines):
                    if re.match(r"^\d/5 ", line):
                        score_line_idx = idx
                        break
                # The comment is the next non-empty line after the score line
                description = "No description provided"
                if score_line_idx is not None:
                    for line in lines[score_line_idx+1:]:
                        if line.strip():
                            description = line.strip()
                            break
                rubric_justifications.append(description)
            else:
                # If we can't find a score, add a default
                original_scores.append(3)  # Default to competent
                rubric_justifications.append("Score parsing error - default description")
        
        if len(original_scores) == 7:
            # Enforce distribution curve on the 7 scores
            rubric_scores = self._enforce_grading_distribution(original_scores)
            
            # Simple average of all 7 scores (now distribution-enforced)
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
            # Set default values when we don't have enough scores
            final_score = 0
            label = "ERROR"
            rubric_scores = []
            final_score_text = "Final Score: ERROR - Could not calculate"
        
        # Generate summative comment programmatically based on individual assessments
        summative_comment = self._generate_summative_comment(
            suture_type, rubric_scores, rubric_justifications, final_score, label
        )
        
        # Update results to show distribution-enforced scores
        updated_results = []
        for i, (original_result, adjusted_score) in enumerate(zip(results[:7], rubric_scores)):
            # Extract the rubric point text and description
            lines = original_result.strip().split('\n')
            if len(lines) >= 1:
                rubric_point = lines[0].strip()
                
                # Get rating label for adjusted score
                adjusted_label = rating_labels.get(adjusted_score, "")
                
                # Try to find the description
                description = "No description provided"
                if len(lines) >= 3:
                    description = lines[2].strip()
                    # If the third line is empty, look for the next non-empty line
                    if not description and len(lines) > 3:
                        for line in lines[3:]:
                            if line.strip():
                                description = line.strip()
                                break
                
                # Format with distribution-enforced score
                updated_result = f"{rubric_point}\n{adjusted_score}/5 {adjusted_label}\n{description}"
                updated_results.append(updated_result)
            else:
                # Fallback for malformed results
                updated_results.append(f"Rubric point {i+1}\n{adjusted_score}/5 {rating_labels.get(adjusted_score, '')}\nNo description available")
        
        # Combine all results into a single formatted string
        header = f"SUTURING ASSESSMENT RESULTS\nVideo File: {os.path.basename(video_path)}\nSuture Type: {suture_type.replace('_', ' ').title()}\n{'='*50}\n\n"
        assessment = header + "\n\n".join(updated_results) + f"\n\n{final_score_text}\n\n{summative_comment}"

        return {"vop_assessment": assessment, "suture_type": suture_type, "video_file": os.path.basename(video_path)}

    def _enforce_grading_distribution(self, original_scores):
        """
        Apply flexible grading distribution that respects actual performance quality.
        Only adjusts scores when necessary to maintain reasonable distribution.
        """
        if len(original_scores) != 7:
            return original_scores  # Can't enforce distribution on wrong number of scores
        
        # Calculate average score to determine overall performance level
        avg_score = sum(original_scores) / len(original_scores)
        
        # If average is 3.5 or higher, this is good performance - don't force poor scores
        if avg_score >= 3.5:
            # For good performance, allow more flexibility
            # Only adjust if there are extreme outliers (e.g., 5s when everything else is 3s)
            score_counts = {}
            for score in original_scores:
                score_counts[score] = score_counts.get(score, 0) + 1
            
            # If we have too many 5s (more than 2), reduce some to 4s
            if score_counts.get(5, 0) > 2:
                adjusted_scores = original_scores.copy()
                five_indices = [i for i, score in enumerate(original_scores) if score == 5]
                # Keep the 2 highest original scores as 5s, reduce others to 4s
                for i in five_indices[2:]:
                    adjusted_scores[i] = 4
                return adjusted_scores
            
            # If we have too many 4s (more than 3), reduce some to 3s
            if score_counts.get(4, 0) > 3:
                adjusted_scores = original_scores.copy()
                four_indices = [i for i, score in enumerate(original_scores) if score == 4]
                # Keep the 3 highest original scores as 4s, reduce others to 3s
                for i in four_indices[3:]:
                    adjusted_scores[i] = 3
                return adjusted_scores
            
            # Otherwise, return original scores for good performance
            return original_scores
        
        # For average performance (2.5-3.4), apply moderate distribution
        elif avg_score >= 2.5:
            # Allow 0-1 scores of each level, with most being 3s
            target_distribution = {
                1: 0,  # Don't force poor scores for average performance
                2: 1,  # Allow 1 substandard score
                3: 4,  # Most should be competent
                4: 1,  # Allow 1 proficient score
                5: 1   # Allow 1 exemplary score
            }
        else:
            # For poor performance (below 2.5), apply stricter distribution
            target_distribution = {
                1: 1,  # Allow 1 poor score
                2: 2,  # Allow 2 substandard scores
                3: 3,  # Most should be competent
                4: 1,  # Allow 1 proficient score
                5: 0   # No exemplary scores for poor overall performance
            }
        
        # Sort scores while preserving original indices
        scored_indices = [(score, i) for i, score in enumerate(original_scores)]
        scored_indices.sort(key=lambda x: x[0], reverse=True)  # Sort by score, highest first
        
        # Initialize adjusted scores
        adjusted_scores = [0] * 7
        
        # Assign scores according to distribution
        score_index = 0
        
        # Assign 5s first
        for _ in range(target_distribution[5]):
            if score_index < len(scored_indices):
                _, original_index = scored_indices[score_index]
                adjusted_scores[original_index] = 5
                score_index += 1
        
        # Assign 4s
        for _ in range(target_distribution[4]):
            if score_index < len(scored_indices):
                _, original_index = scored_indices[score_index]
                adjusted_scores[original_index] = 4
                score_index += 1
        
        # Assign 3s
        for _ in range(target_distribution[3]):
            if score_index < len(scored_indices):
                _, original_index = scored_indices[score_index]
                adjusted_scores[original_index] = 3
                score_index += 1
        
        # Assign 2s
        for _ in range(target_distribution[2]):
            if score_index < len(scored_indices):
                _, original_index = scored_indices[score_index]
                adjusted_scores[original_index] = 2
                score_index += 1
        
        # Assign 1s
        for _ in range(target_distribution[1]):
            if score_index < len(scored_indices):
                _, original_index = scored_indices[score_index]
                adjusted_scores[original_index] = 1
                score_index += 1
        
        # Fill any remaining with 3s
        while score_index < len(scored_indices):
            _, original_index = scored_indices[score_index]
            adjusted_scores[original_index] = 3
            score_index += 1
        
        return adjusted_scores

    def _generate_summative_comment(self, suture_type, rubric_scores, rubric_justifications, final_score, final_label):
        """Generate a summative comment by analyzing scores and sending to Gemini for natural language generation"""
        
        # Get rubric point names for context
        rubric_names = {
            "simple_interrupted": [
                "needle perpendicular to skin",
                "avoiding multiple forceps grasps", 
                "instrument ties with square knots",
                "appropriate skin tension",
                "suture spacing (0.5-1.0 cm)",
                "skin edge eversion",
                "economy of time and motion"
            ],
            "vertical_mattress": [
                "needle perpendicular to skin",
                "avoiding multiple forceps grasps",
                "instrument ties with square knots", 
                "appropriate skin tension",
                "suture spacing (0.5-1.0 cm)",
                "skin edge eversion",
                "economy of time and motion"
            ],
            "subcuticular": [
                "appropriate dermal layer bites",
                "direct entry across from exit site",
                "avoiding multiple dermal penetration",
                "avoiding multiple forceps grasps",
                "instrument ties with square knots",
                "appropriate skin tension", 
                "economy of time and motion"
            ]
        }
        
        names = rubric_names.get(suture_type, [f"criterion {i+1}" for i in range(7)])
        
        # Create structured analysis for Gemini
        analysis_parts = []
        
        # Overall performance summary
        analysis_parts.append(f"Overall Performance: {final_score}/5 ({final_label})")
        
        # Strengths (scores 4-5)
        strengths = []
        for i, (score, justification) in enumerate(zip(rubric_scores, rubric_justifications)):
            if score >= 4:
                strengths.append(f"{names[i]}: {justification}")
        
        if strengths:
            analysis_parts.append("Strengths:")
            analysis_parts.extend([f"- {s}" for s in strengths])
        
        # Areas for improvement (scores 1-2)
        weaknesses = []
        for i, (score, justification) in enumerate(zip(rubric_scores, rubric_justifications)):
            if score <= 2:
                weaknesses.append(f"{names[i]}: {justification}")
        
        if weaknesses:
            analysis_parts.append("Areas for Improvement:")
            analysis_parts.extend([f"- {w}" for w in weaknesses])
        
        # Competent areas (score 3)
        competent = []
        for i, (score, justification) in enumerate(zip(rubric_scores, rubric_justifications)):
            if score == 3:
                competent.append(f"{names[i]}: {justification}")
        
        if competent:
            analysis_parts.append("Competent Areas:")
            analysis_parts.extend([f"- {c}" for c in competent])
        
        # Send to Gemini for natural language generation
        analysis_text = "\n".join(analysis_parts)
        
        prompt = f"""
You are an expert surgical educator. Based on this assessment analysis of a {suture_type.replace('_', ' ')} suture, write a single, natural, narrative paragraph that provides concrete, actionable feedback.

Assessment Analysis:
{analysis_text}

Write a summative comment that:
- Is natural and narrative (not mechanical or repetitive)
- Does NOT repeat the individual scores
- Uses neutral, objective language without superlatives or heavily inflected terms
- Describes technique characteristics and issues in descriptive terms
- Provides concrete, actionable advice for improvement
- Focuses on the most important areas for development
- Includes specific correction strategies and techniques
- Encourages continued development
- Uses professional but accessible language
- Prioritizes technique, knot tying, needle handling, and instrument use over tension assessment
- Focuses on actual technical errors, not technique preferences or variations
- Provides appropriate-level feedback for PGY-1 learners (avoid advanced techniques they haven't mastered yet)

The individual rubric points provide brief score justifications. This summative comment should provide the detailed analysis, correction advice, and actionable guidance.

Start with "Summative Comment:" and write a single flowing paragraph.
"""
        
        try:
            content = self.types.Content(parts=[
                self.types.Part.from_text(text=prompt)
            ])
            response = self.client.models.generate_content(
                model=self.model,
                contents=[content],
                config={"temperature": 0.1}
            )
            response_text = getattr(response, 'text', str(response))
            return response_text.strip()
        except Exception as e:
            # Fallback to simple programmatic comment if Gemini fails
            print(f"Warning: Gemini summative comment generation failed: {e}")
            return self._generate_fallback_comment(suture_type, rubric_scores, final_score, final_label)
    
    def _generate_fallback_comment(self, suture_type, rubric_scores, final_score, final_label):
        """Fallback method for generating summative comment if Gemini fails"""
        if final_score >= 4:
            return f"Summative Comment: This {suture_type.replace('_', ' ')} suture demonstrates {final_label} technique. Continue practicing to maintain this high level of proficiency."
        elif final_score == 3:
            return f"Summative Comment: This {suture_type.replace('_', ' ')} suture shows {final_label} performance with room for improvement. Focus on the areas identified in the individual assessments for enhanced proficiency."
        else:
            return f"Summative Comment: This {suture_type.replace('_', ' ')} suture requires significant improvement to reach {final_label} standards. Dedicated practice and attention to the fundamental techniques will lead to substantial progress."

from google import genai
from google.genai import types
import os
import re

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