# Suturing Assessment Tool

A Python-based GUI application that uses Google's Gemini AI to assess suturing procedures and generate Verification of Proficiency (VoP) reports.

## Features

- **Suturing Assessment**: Upload and analyze suturing procedure videos for comprehensive evaluation
- **Multiple Suture Types**: Support for Simple Interrupted, Vertical Mattress, and Subcuticular sutures
- **VoP Checklists**: Evaluates procedures using Verification of Proficiency criteria for each suture type
- **OSATS Scoring**: Uses 5-point Likert scale with behavioral anchors for objective assessment
- **Clinical Feedback**: Provides evidence-based, actionable feedback with specific recommendations
- **User-Friendly GUI**: Simple Tkinter interface for easy operation

## Requirements

- Python 3.8 or higher
- Google Gemini API key (Ultra subscription recommended)
- Video files in common formats (MP4, AVI, MOV, MKV, WMV, M4V)

## Installation

1. **Clone or download the project files**

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv suturing_env
   ```

3. **Activate the virtual environment:**
   - Windows:
     ```bash
     suturing_env\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source suturing_env/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Setup

1. **Get a Gemini API Key:**
   - Visit [Google AI Studio](https://aistudio.google.com/)
   - Create an account and get your API key
   - Ensure you have an Ultra subscription for video analysis

2. **Run the application:**
   ```bash
   python suturing_assessment_app.py
   ```

3. **Configure API Key:**
   - Enter your Gemini API key in the application
   - Click "Save API Key" to store it securely

## Usage

1. **Select Video File:**
   - Click "Browse" to select your suturing procedure video
   - Supported formats: MP4, AVI, MOV, MKV, WMV, M4V

2. **Choose Suture Type:**
   - Select the type of suture being performed:
     - Simple Interrupted
     - Vertical Mattress
     - Subcuticular

3. **Run Assessment:**
   - Click "Assess Suturing" to analyze the video
   - The analysis may take several minutes depending on video length

4. **Review Results:**
   - **Suturing Assessment Tab**: Comprehensive evaluation with OSATS scoring and detailed feedback
   - **Raw Response Tab**: Complete API response for debugging

## Assessment Criteria

The tool evaluates suturing procedures using VoP checklists specific to each suture type:

### Simple Interrupted Sutures
1. Passes needle perpendicular to skin on both sides of skin
2. Avoids multiple forceps grasps of skin
3. Instrument ties with square knots
4. Approximates skin with appropriate tension
5. Places sutures 0.5 - 1.0 centimeters apart
6. Eversion of the skin edges
7. Economy of time and motion (scale of 1-5):
   - 1: many unnecessary/disorganized movements
   - 2: some unnecessary movements, basic organization
   - 3: organized time/motion, some unnecessary movements
   - 4: good economy, minimal unnecessary movements
   - 5: maximum economy of movement and efficiency
8. Final rating/demonstrates proficiency
9. Other summative comments

### Vertical Mattress Sutures
1. Passes needle perpendicular to skin on both sides of skin
2. Avoids multiple forceps grasps of skin
3. Instrument ties with square knots
4. Approximates skin with appropriate tension
5. Places sutures 0.5 - 1.0 centimeters apart
6. Eversion of the skin edges
7. Economy of time and motion (scale of 1-5):
   - 1: many unnecessary/disorganized movements
   - 2: some unnecessary movements, basic organization
   - 3: organized time/motion, some unnecessary movements
   - 4: good economy, minimal unnecessary movements
   - 5: maximum economy of movement and efficiency
8. Final rating/demonstrates proficiency
9. Other summative comments

### Subcuticular Sutures
1. Runs the suture, placing appropriate bites into dermal layer
2. Enters the dermal layer directly across from exit site
3. Avoids multiple penetrations of the dermis
4. Avoids multiple forceps grasps of skin
5. Instrument ties with square knots
6. Approximates skin with appropriate tension
7. Economy of time and motion (scale of 1-5):
   - 1: many unnecessary/disorganized movements
   - 2: some unnecessary movements, basic organization
   - 3: organized time/motion, some unnecessary movements
   - 4: good economy, minimal unnecessary movements
   - 5: maximum economy of movement and efficiency
8. Final rating/demonstrates proficiency
9. Other summative comments

## Scoring System

The tool uses a 5-point OSATS-style Likert scale:
- **1 - Very Poor / Novice**: Fundamental errors, unsafe technique
- **2 - Poor / Beginner**: Multiple technique errors, needs significant improvement
- **3 - Acceptable / Competent**: Basic proficiency with some areas for improvement
- **4 - Good / Proficient**: Solid technique with minor refinements needed
- **5 - Excellent / Expert**: Mastery of technique, serves as teaching example

## File Structure

```
suturing_assessment_tool/
├── suturing_assessment_app.py   # Main GUI application
├── gemini_assessor.py          # Gemini AI integration and assessment logic
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── suturing_assessment_config.json  # Saved API key (created automatically)
```

## Troubleshooting

### Common Issues

1. **"Missing required packages" error:**
   - Ensure you've activated your virtual environment
   - Run `pip install -r requirements.txt`

2. **"API key not valid" error:**
   - Verify your Gemini API key is correct
   - Ensure you have an Ultra subscription for video analysis
   - Check your API quota and billing status

3. **"Video file not supported" error:**
   - Convert video to MP4 format if possible
   - Ensure video file is not corrupted
   - Check file size (very large files may timeout)

4. **"Assessment failed" error:**
   - Check your internet connection
   - Verify API key is saved correctly
   - Try with a shorter video file first

### Performance Tips

- **Video Length**: Shorter videos (1-3 minutes) process faster
- **Video Quality**: Higher quality videos provide better assessment results
- **File Size**: Keep videos under 100MB for optimal performance
- **Network**: Stable internet connection required for API calls

## API Usage

The application uses Google's Gemini 2.5 Pro model for video analysis. Video files are uploaded directly to the Gemini API for processing. Ensure your API quota can handle the video sizes you plan to analyze.

## Contributing

This is an MVP (Minimum Viable Product) for suturing assessment. Future enhancements may include:

- Support for additional suture types
- Batch processing of multiple videos
- Custom assessment criteria
- Integration with learning management systems
- Real-time assessment during procedures

## License

This project is for educational and research purposes. Please ensure compliance with your institution's policies regarding AI-assisted assessment tools.

## Support

For technical support or questions about the assessment criteria, please refer to your institution's surgical education department or contact the development team. 