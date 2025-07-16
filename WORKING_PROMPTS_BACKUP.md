# WORKING PROMPTS AND API STRUCTURE - LOCKED DOWN

## CRITICAL: DO NOT MODIFY THESE PROMPTS OR API STRUCTURE

This document contains the exact working prompts and API structure that produces structured VoP assessment output. Any changes to these will cause regressions.

## API Structure (CRITICAL)

```python
# Use this exact import and initialization
from google import genai
from google.genai import types
self.client = genai.Client(api_key=api_key)
self.types = types
self.model = 'models/gemini-2.5-pro'

# Use this exact content structure for API calls
content = self.types.Content(parts=[
    self.types.Part.from_bytes(data=video_bytes, mime_type=self._get_mime_type(video_path)),
    self.types.Part.from_text(text=prompt)
])

# Use this exact API call
response = self.client.models.generate_content(
    model=self.model,
    contents=[content]
)
```

## Working Prompts (CRITICAL - DO NOT CHANGE)

### Video Assessment Prompt
```python
prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture. 

Assess this specific rubric point: {idx+1}) {point_text}

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a brief justification for the score.

Use this strict grading distribution: 80% of scores should be 3 (competent), 7% should be 4 (proficient), 3% should be 5 (exemplary), 7% should be 2 (substandard), and 3% should be 1 (poor). Be conservative - 3 is the default for adequate performance, 4 for clearly exceptional work, and 5 for near-perfect technique that could serve as a teaching example.

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Keep the justification brief and descriptive. Use neutral, objective language. Describe what is observed without superlatives or heavily inflected language. Simply state the technique characteristics and any issues noted.

Do not add any extra labels or commentary.
"""
```

### Still Image Assessment Prompt (IDENTICAL to video)
```python
prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture. 

Assess this specific rubric point: {idx+1}) {point_text}

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a brief justification for the score.

Use this strict grading distribution: 80% of scores should be 3 (competent), 7% should be 4 (proficient), 3% should be 5 (exemplary), 7% should be 2 (substandard), and 3% should be 1 (poor). Be conservative - 3 is the default for adequate performance, 4 for clearly exceptional work, and 5 for near-perfect technique that could serve as a teaching example.

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Keep the justification brief and descriptive. Use neutral, objective language. Describe what is observed without superlatives or heavily inflected language. Simply state the technique characteristics and any issues noted.

Do not add any extra labels or commentary.
"""
```

## Summative Comment Generation (UPDATED - Hybrid Approach)

The summative comment is now generated using a hybrid approach that combines programmatic analysis with Gemini's natural language generation:

```python
def _generate_summative_comment(self, suture_type, rubric_scores, rubric_justifications, final_score, final_label):
    """Generate a summative comment by analyzing scores and sending to Gemini for natural language generation"""
    # 1. Creates structured analysis from individual rubric scores
    # 2. Sends analysis to Gemini for natural, narrative generation
    # 3. Ensures consistency while avoiding mechanical repetition
```

### Hybrid Approach Benefits:
- **Consistency**: Based on actual rubric scores and justifications
- **Natural Language**: Gemini generates flowing, narrative text
- **No Repetition**: Avoids mechanical listing of scores
- **Actionable**: Provides concrete, specific advice
- **Professional**: Uses appropriate medical terminology
- **Fallback**: Simple programmatic comment if Gemini fails

### Process:
1. **Analysis**: Programmatically categorizes scores into strengths (4-5), weaknesses (1-2), and competent areas (3)
2. **Structured Input**: Sends organized analysis to Gemini with specific instructions
3. **Natural Output**: Gemini generates narrative paragraph without repeating scores
4. **Quality Control**: Ensures professional, actionable, and encouraging tone

### Streamlined Format Benefits:
- **Individual Points**: Brief, focused justifications that explain the score
- **Summative Comment**: Detailed analysis, correction strategies, and actionable guidance
- **No Repetition**: Eliminates redundancy between individual and summative sections
- **Cleaner Readability**: More concise individual assessments with comprehensive final analysis

### Language Style (UPDATED):
- **Neutral and Objective**: Uses descriptive language without superlatives or heavily inflected terms
- **Descriptive Focus**: Describes technique characteristics and issues in objective terms
- **Professional Tone**: Maintains clinical accuracy while being accessible
- **Balanced Assessment**: Avoids overly emphatic or opinionated language

## Output Format (CRITICAL)

### Expected Rubric Point Output
```
1) passes needle perpendicular to skin on both sides of skin
3/5 competent
Needle entry and exit angles are appropriate for tissue approximation

2) avoids multiple forceps grasps of skin
4/5 proficient
Single, stable forceps grasps minimize tissue trauma

3) instrument ties with square knots
2/5 substandard
Inconsistent square knot formation observed
```

### Expected Final Score Output
```
Final Score: 3/5 competent
```

### Expected Summative Comment Output
```
Summative Comment: This simple interrupted suture demonstrates competent overall technique with strengths in forceps control and suture spacing. The forceps handling minimizes tissue trauma, while spacing within the target range shows appropriate technical planning. Two areas require attention: square knot formation needs practice for consistency, and skin edge eversion is insufficient, which may affect wound healing. The needle angles and tension control are adequate but could be refined. Practice on knot tying technique and skin edge manipulation will improve proficiency. Continue developing strengths while addressing these technical areas.
```

## Distribution Enforcement (NEW - Hybrid Approach)

The system now uses a hybrid approach for scoring:

1. **AI Assessment**: Gemini 2.5 Pro assesses each rubric point and provides clinical judgment
2. **Distribution Enforcement**: Code enforces the strict grading curve: 1: 3%, 2: 7%, 3: 80%, 4: 7%, 5: 3%
3. **Score Adjustment**: Original AI scores are adjusted to match the distribution while preserving relative ordering
4. **Final Calculation**: Final score is calculated as simple average of the 7 distribution-enforced scores

### Distribution Enforcement Logic:
- For 7 scores: 1 one (14.3%) + 1 two (14.3%) + 5 threes (71.4%) + 0 fours (0%) + 0 fives (0%) = closest approximation to 3% + 7% + 80% + 7% + 3%
- Preserves relative ordering: highest original scores get highest adjusted scores
- Ensures consistent grading curve across all assessments

## What NOT to Do (REGESSION CAUSES)

1. **DO NOT** use `google.generativeai` SDK - it causes different behavior
2. **DO NOT** add timeout handling or post-processing that strips lines
3. **DO NOT** change the prompt format or add "CRITICAL" instructions
4. **DO NOT** make video and still prompts different
5. **DO NOT** add generation config or temperature settings
6. **DO NOT** remove the "Do not add any extra labels or commentary" line
7. **DO NOT** revert to separate API call for summative comment - use programmatic generation
8. **DO NOT** remove distribution enforcement - this ensures consistent grading curve

## File Versions (CRITICAL)

- `gemini_assessor.py`: Updated with programmatic summative comment generation
- `suturing_assessment_app.py`: 32KB, 669 lines (restored from GitHub)

## Testing Checklist

Before making any changes, verify:
- 7 rubric points in 3-line format with brief justifications
- Correct final score calculation
- Natural narrative summative comment (not mechanical repetition)
- No verbose descriptions or JSON output
- No duplicate headers
- Summative comment aligns with individual rubric scores
- Summative comment provides detailed analysis and actionable advice
- Individual justifications are concise and focused 