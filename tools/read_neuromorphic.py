import zipfile
import xml.etree.ElementTree as ET
import os

def get_docx_text(path):
    """
    Take the path of a docx file as argument, return the text in unicode.
    """
    document = zipfile.ZipFile(path)
    xml_content = document.read('word/document.xml')
    document.close()
    tree = ET.fromstring(xml_content)
    
    # Namespaces
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    paragraphs = []
    for paragraph in tree.findall('.//w:p', ns):
        texts = [node.text for node in paragraph.findall('.//w:t', ns) if node.text]
        if texts:
            paragraphs.append("".join(texts))
    
    return "\n".join(paragraphs)

directory = 'neuromorphic'
files = [f for f in os.listdir(directory) if f.endswith('.docx')]

for file in files:
    path = os.path.join(directory, file)
    print(f"--- START OF FILE: {file} ---")
    try:
        print(get_docx_text(path))
    except Exception as e:
        print(f"Error reading {file}: {e}")
    print(f"--- END OF FILE: {file} ---\n")
