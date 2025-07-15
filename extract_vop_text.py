from docx import Document

doc = Document('Complete_VoP_Evaluations.docx')
 
with open('vop_text.txt', 'w', encoding='utf-8') as f:
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            f.write(text + '\n') 