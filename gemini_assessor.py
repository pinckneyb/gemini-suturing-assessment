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
                if idx == 0 and suture_type in ["simple_interrupted", "vertical_mattress"]:
                    # Special prompt for needle perpendicularity
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture.

Assess only this rubric point:

1) Passes needle perpendicular to skin on both sides of skin

Print:

rubric point number and text,

score as x/5 plus rating label (e.g., "3/5 competent"),

brief justification.

Use rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Scoring criteria (angle definitions):

5/5 exemplary → consistently within 5° of perpendicular (85–95°) on both entry and exit.

4/5 proficient → mostly within 10° (80–100°), occasional minor deviation.

3/5 competent → generally within 15° (75–105°), some noticeable deviations.

2/5 substandard → frequent deviation beyond 15°.

1/5 poor → predominantly oblique (>20° deviation), few or no perpendicular passes.

Focus on:

angle of both entry and exit passes,

across all stitches observed (not just one example).

Keep the justification neutral, factual, and concise.
Describe the angle patterns, mention consistency or inconsistency, and avoid value-laden language.
"""
                elif idx == 1 and suture_type in ["simple_interrupted", "vertical_mattress"]:
                    # Special prompt for forceps grasps
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture.

Assess only this rubric point:

2) Avoids multiple forceps grasps of skin

Print:

rubric point number and text,

score as x/5 plus rating label (e.g., "3/5 competent"),

brief justification.

Use rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Scoring criteria:

5/5 exemplary → single, precise forceps grasp per skin edge, no regrasping or repositioning needed.

4/5 proficient → mostly single grasps, occasional minor repositioning (1-2 instances per stitch).

3/5 competent → generally single grasps, some regrasping or repositioning (3-4 instances per stitch).

2/5 substandard → frequent multiple grasps, significant repositioning needed (5+ instances per stitch).

1/5 poor → excessive regrasping, multiple attempts per edge, poor tissue handling.

Focus on:

number of forceps grasps per skin edge,

frequency of regrasping or repositioning,

across all stitches observed.

Keep the justification neutral, factual, and concise.
Describe the grasping patterns and frequency of adjustments.
"""
                elif idx == 2 and suture_type in ["simple_interrupted", "vertical_mattress"]:
                    # Special prompt for square knots
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture.

Assess only this rubric point:

3) Instrument ties with square knots

Print:

rubric point number and text,

score as x/5 plus rating label (e.g., "3/5 competent"),

brief justification.

Use rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Scoring criteria:

5/5 exemplary → consistently perfect square knots, proper tension, no slippage, clean throws.

4/5 proficient → mostly square knots, occasional minor tension issues, rare slippage.

3/5 competent → generally square knots, some tension variation, occasional slippage or granny knots.

2/5 substandard → frequent non-square knots, poor tension control, significant slippage.

1/5 poor → predominantly granny knots or slip knots, poor tension, frequent failures.

Focus on:

knot type (square vs granny vs slip),

tension consistency,

slippage frequency,

across all knots tied.

Keep the justification neutral, factual, and concise.
Describe the knot quality and consistency patterns.
"""
                elif idx == 6 and suture_type in ["simple_interrupted", "vertical_mattress"]:
                    # Special prompt for economy of motion
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture.

Assess only this rubric point:

7) Economy of time and motion

Print:

rubric point number and text,

score as x/5 plus rating label (e.g., "3/5 competent"),

brief justification.

Use rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Scoring criteria:

5/5 exemplary → maximum efficiency, minimal unnecessary movement, smooth transitions, optimal instrument handling.

4/5 proficient → mostly efficient, occasional minor inefficiencies, generally smooth workflow.

3/5 competent → generally organized, some unnecessary movements, acceptable workflow with minor delays.

2/5 substandard → frequent inefficiencies, noticeable unnecessary movements, workflow interruptions.

1/5 poor → disorganized movements, excessive unnecessary motion, poor instrument handling, significant delays.

Focus on:

efficiency of movements,

unnecessary motion frequency,

workflow smoothness,

instrument handling,

across the entire procedure.

Keep the justification neutral, factual, and concise.
Describe the movement patterns and efficiency characteristics.
"""
                else:
                    # Standard prompt for other rubric points
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture. 

Assess this specific rubric point: {idx+1}) {point_text}

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a brief justification for the score.

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Keep the justification brief and descriptive. Use neutral, objective language. Describe what is observed without superlatives or heavily inflected language. Simply state the technique characteristics and any issues noted.

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
                if idx == 3 and suture_type in ["simple_interrupted", "vertical_mattress"]:
                    # Special prompt for skin tension
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture.

Assess only this rubric point:

4) Approximates skin with appropriate tension

Print:

rubric point number and text,

score as x/5 plus rating label (e.g., "3/5 competent"),

brief justification.

Use rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Scoring criteria:

5/5 exemplary → perfect skin approximation, no gaping, no puckering, edges just touching without compression.

4/5 proficient → excellent approximation, minimal gaping or puckering, appropriate tension throughout.

3/5 competent → generally good approximation, some minor gaping or puckering, mostly appropriate tension.

2/5 substandard → poor approximation, significant gaping or puckering, inappropriate tension.

1/5 poor → very poor approximation, excessive gaping or puckering, poor tension control.

Focus on:

skin edge approximation quality,

presence of gaping or puckering,

tension appropriateness,

across all visible sutures.

Keep the justification neutral, factual, and concise.
Describe the approximation patterns and tension characteristics.
"""
                elif idx == 4 and suture_type in ["simple_interrupted", "vertical_mattress"]:
                    # Special prompt for suture spacing
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture.

Assess only this rubric point:

5) Places sutures 0.5 - 1.0 centimeters apart

Print:

rubric point number and text,

score as x/5 plus rating label (e.g., "3/5 competent"),

brief justification.

Use rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Scoring criteria:

5/5 exemplary → consistently 0.5-1.0 cm spacing, uniform distribution, no gaps or crowding.

4/5 proficient → mostly 0.5-1.0 cm spacing, occasional minor variation (±0.2 cm), generally uniform.

3/5 competent → generally 0.5-1.0 cm spacing, some variation (±0.3 cm), mostly appropriate distribution.

2/5 substandard → frequent spacing outside 0.5-1.0 cm range, noticeable gaps or crowding.

1/5 poor → predominantly incorrect spacing, excessive gaps or crowding, poor distribution.

Focus on:

distance between adjacent sutures,

consistency of spacing,

presence of gaps or crowding,

across all visible sutures.

Keep the justification neutral, factual, and concise.
Describe the spacing patterns and distribution characteristics.
"""
                elif idx == 5 and suture_type in ["simple_interrupted", "vertical_mattress"]:
                    # Special prompt for skin edge eversion
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture.

Assess only this rubric point:

6) Eversion of the skin edges

Print:

rubric point number and text,

score as x/5 plus rating label (e.g., "3/5 competent"),

brief justification.

Use rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Scoring criteria:

5/5 exemplary → perfect eversion, skin edges rolled outward, no inversion, optimal healing position.

4/5 proficient → excellent eversion, mostly rolled outward, minimal inversion, very good healing position.

3/5 competent → generally good eversion, some rolling outward, occasional minor inversion.

2/5 substandard → poor eversion, frequent inversion, skin edges not in optimal healing position.

1/5 poor → very poor eversion, predominantly inverted edges, poor healing position.

Focus on:

skin edge orientation (everted vs inverted),

degree of eversion,

consistency across sutures,

healing position quality.

Keep the justification neutral, factual, and concise.
Describe the eversion patterns and edge orientation characteristics.
"""
                else:
                    # Standard prompt for other still image criteria
                    prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture. 

Assess this specific rubric point: {idx+1}) {point_text}

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a brief justification for the score.

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Keep the justification brief and descriptive. Use neutral, objective language. Describe what is observed without superlatives or heavily inflected language. Simply state the technique characteristics and any issues noted.

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
        rubric_justifications = []
        original_scores = []  # Store original AI scores for comparison
        
        for r in results[:7]:
            match = re.search(r"(\d)/(5)\s+(poor|substandard|competent|proficient|exemplary)", r, re.IGNORECASE)
            if match:
                original_score = int(match.group(1))
                original_scores.append(original_score)
                # Extract the justification (everything after the score line)
                lines = r.strip().split('\n')
                if len(lines) >= 3:
                    justification = lines[2].strip()
                    rubric_justifications.append(justification)
                else:
                    rubric_justifications.append("No justification provided")
        
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
            final_score_text = "Final Score: ERROR - Could not calculate"
        
        # Generate summative comment programmatically based on individual assessments
        summative_comment = self._generate_summative_comment(
            suture_type, rubric_scores, rubric_justifications, final_score, label
        )
        
        # Update results to show distribution-enforced scores
        updated_results = []
        for i, (original_result, adjusted_score) in enumerate(zip(results[:7], rubric_scores)):
            # Extract the rubric point text and justification
            lines = original_result.strip().split('\n')
            if len(lines) >= 3:
                rubric_point = lines[0].strip()
                justification = lines[2].strip()
                
                # Get rating label for adjusted score
                adjusted_label = rating_labels.get(adjusted_score, "")
                
                # Format with distribution-enforced score
                updated_result = f"{rubric_point}\n{adjusted_score}/5 {adjusted_label}\n{justification}"
                updated_results.append(updated_result)
            else:
                updated_results.append(original_result)
        
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

The individual rubric points provide brief score justifications. This summative comment should provide the detailed analysis, correction advice, and actionable guidance.

Start with "Summative Comment:" and write a single flowing paragraph.
"""
        
        try:
            content = self.types.Content(parts=[
                self.types.Part.from_text(text=prompt)
            ])
            response = self.client.models.generate_content(
                model=self.model,
                contents=[content]
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