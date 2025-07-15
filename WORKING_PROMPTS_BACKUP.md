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

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a single clinical, skeptical, actionable justification. 

Most scores should be 3 (competent); use 4 only for clearly above-average, and 5 only for near-perfect. Be clinical and skeptical, avoid superlatives, and always provide actionable advice. 

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Do not add any extra labels or commentary.
"""
```

### Still Image Assessment Prompt (IDENTICAL to video)
```python
prompt = f"""
You are an expert surgical educator assessing a {suture_type.replace('_', ' ')} suture. 

Assess this specific rubric point: {idx+1}) {point_text}

Print the rubric point number and text, then the score as x/5 plus the rating label (e.g., '3/5 competent'), then a single clinical, skeptical, actionable justification. 

Most scores should be 3 (competent); use 4 only for clearly above-average, and 5 only for near-perfect. Be clinical and skeptical, avoid superlatives, and always provide actionable advice. 

Use these rating labels: 1/5 poor, 2/5 substandard, 3/5 competent, 4/5 proficient, 5/5 exemplary.

Do not add any extra labels or commentary.
"""
```

### Summative Comment Prompt
```python
prompt9 = f"""
You are an expert surgical educator. Write a single, readable paragraph labeled 'Summative Comment:' that provides specific, evidence-based, and actionable feedback for this {suture_type.replace('_', ' ')} suture. Do not add any extra labels or commentary.
"""
```

## Output Format (CRITICAL)

### Expected Rubric Point Output
```
1) passes needle perpendicular to skin on both sides of skin
3/5 competent
Needle entry and exit angles are appropriate for tissue approximation
```

### Expected Final Score Output
```
Final Score: 3/5 competent
```

### Expected Summative Comment Output
```
Summative Comment: [single paragraph with specific, evidence-based, actionable feedback]
```

## What NOT to Do (REGESSION CAUSES)

1. **DO NOT** use `google.generativeai` SDK - it causes different behavior
2. **DO NOT** add timeout handling or post-processing that strips lines
3. **DO NOT** change the prompt format or add "CRITICAL" instructions
4. **DO NOT** make video and still prompts different
5. **DO NOT** add generation config or temperature settings
6. **DO NOT** remove the "Do not add any extra labels or commentary" line

## File Versions (CRITICAL)

- `gemini_assessor.py`: 12KB, 259 lines (restored from GitHub)
- `suturing_assessment_app.py`: 32KB, 669 lines (restored from GitHub)

## Testing Checklist

Before making any changes, verify:
1. All 7 rubric points produce 3-line format
2. Final score calculates correctly
3. Summative comment is a single paragraph
4. No verbose video descriptions
5. No JSON output
6. No duplicate headers

## Reference Images (Updated July 15, 2025)
- `simple_interrupted_example.png` - Reference image for simple interrupted sutures
- `vertical_mattress_example.png` - Reference image for vertical mattress sutures  
- `subcuticular_example.png` - Reference image for subcuticular sutures

## Last Working Date: July 15, 2025
Restored from: https://github.com/pinckneyb/gemini-suturing-assessment 