# Suturing Assessment Tools

A comprehensive Python-based toolkit for video analysis and suturing procedure assessment using Google's Gemini 2.5 Pro AI.

## 🎯 **Two Applications in One Toolkit**

### 1. **Video Description Tool** (`suturing_assessment_gui.py`)
- **Purpose**: Simple video analysis and description
- **Features**: 
  - Plain language video descriptions
  - Timestamp references for significant actions
  - Works with videos up to 2GB
  - Fast and lightweight

### 2. **Suturing Assessment Tool** (`suturing_assessment_app.py`)
- **Purpose**: Comprehensive suturing procedure evaluation
- **Features**:
  - VoP (Verification of Proficiency) checklist assessment
  - Multiple suture type support
  - Detailed evaluation criteria
  - Tabbed interface for results
  - Raw API response viewing

## 🚀 **Quick Start**

### **Option 1: Use the Launcher (Recommended)**
```bash
python launcher.py
```
Choose between the two applications from the menu.

### **Option 2: Run Individual Applications**
```bash
# Video Description Tool
python suturing_assessment_gui.py

# Suturing Assessment Tool  
python suturing_assessment_app.py
```

## 📋 **Requirements**

- Python 3.8 or higher
- Google Gemini API key (Ultra subscription recommended)
- Video files in common formats (MP4, AVI, MOV, MKV, WMV)

## 🔧 **Installation**

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get a Gemini API Key:**
   - Visit [Google AI Studio](https://aistudio.google.com/)
   - Create an account and get your API key
   - Ensure you have an Ultra subscription for video analysis

3. **Run the launcher:**
   ```bash
   python launcher.py
   ```

## 🎮 **Usage**

### **Video Description Tool**
1. Enter and save your Gemini API key
2. Select a video file
3. Click "Describe Video"
4. View the plain language description with timestamps

### **Suturing Assessment Tool**
1. Enter and save your Gemini API key
2. Select a video file
3. Choose the suture type being performed
4. Click either:
   - **"Describe Video"** for plain language description
   - **"Assess Suturing"** for comprehensive evaluation
5. View results in the tabbed interface:
   - **Video Description**: Plain language analysis
   - **Suturing Assessment**: Detailed evaluation results
   - **Raw Response**: Complete API response for debugging

## 🔍 **Supported Suture Types**

- **Simple Interrupted**: Basic interrupted suturing technique
- **Vertical Mattress**: Vertical mattress suturing technique  
- **Subcuticular**: Subcuticular suturing technique

## 📊 **Assessment Criteria**

The suturing assessment evaluates:

### **Preparation**
- Proper hand washing and sterile technique
- Correct positioning of patient and operator
- Appropriate selection of suture material and needle
- Proper tissue handling and exposure

### **Technique**
- Correct needle insertion angle and depth
- Proper tissue approximation
- Appropriate suture spacing
- Correct knot tying technique
- Proper suture tension

### **Economy of Motion**
- Efficient hand movements
- Minimal unnecessary motion
- Smooth transitions between steps
- Proper instrument handling

### **Safety**
- Avoidance of needle stick injuries
- Proper disposal of sharps
- Maintenance of sterile field
- Patient safety considerations

## 🛠 **Technical Features**

### **File Handling**
- **Small videos (<20MB)**: Inline processing (no upload delay)
- **Large videos (≥20MB)**: File upload with automatic polling for ACTIVE status
- **Maximum size**: Up to 2GB supported

### **Error Handling**
- Robust polling mechanism for file uploads
- Graceful timeout handling (120 seconds)
- Clear error messages and debugging information
- Fallback mechanisms for API issues

### **User Interface**
- Responsive Tkinter GUI
- Progress indicators
- Tabbed results display
- Threading for non-blocking operations

## 📁 **File Structure**

```
Gemini_suturing_mentor/
├── launcher.py                    # Main launcher (choose your app)
├── suturing_assessment_gui.py     # Video Description Tool
├── suturing_assessment_app.py     # Suturing Assessment Tool
├── gemini_assessor.py            # Core AI integration
├── config.py                     # Configuration management
├── main.py                       # Legacy entry point
├── test_polling.py               # Testing script
├── requirements.txt              # Python dependencies
├── README_NEW.md                 # This file
└── suturing_assessment_config.json  # Saved API key
```

## 🔧 **Troubleshooting**

### **Common Issues**

1. **"Missing required packages" error:**
   - Run `pip install -r requirements.txt`

2. **"API key not valid" error:**
   - Verify your Gemini API key is correct
   - Ensure you have an Ultra subscription for video analysis

3. **"File not in ACTIVE state" error:**
   - The polling mechanism should handle this automatically
   - For very large files, wait a bit longer
   - Check your internet connection

4. **"Video file not supported" error:**
   - Convert video to MP4 format if possible
   - Ensure video file is not corrupted

### **Performance Tips**

- **Video Length**: Shorter videos (1-3 minutes) process faster
- **Video Quality**: Higher quality videos provide better assessment results
- **File Size**: Keep videos under 100MB for optimal performance
- **Network**: Stable internet connection required for API calls

## 🎯 **Use Cases**

### **Video Description Tool**
- Quick video analysis for research
- Content description for accessibility
- Educational video summarization
- General video understanding

### **Suturing Assessment Tool**
- Medical education and training
- Surgical skill evaluation
- Verification of Proficiency (VoP) assessments
- Surgical technique feedback
- Quality assurance in medical training

## 🔮 **Future Enhancements**

- Batch processing of multiple videos
- Custom assessment criteria
- Integration with learning management systems
- Real-time assessment during procedures
- Export to PDF reports
- Integration with medical databases

## 📄 **License**

This project is for educational and research purposes. Please ensure compliance with your institution's policies regarding AI-assisted assessment tools.

## 🆘 **Support**

For issues or questions:
1. Check the troubleshooting section above
2. Review the raw response tab for detailed error information
3. Ensure your API key has sufficient quota for video analysis 