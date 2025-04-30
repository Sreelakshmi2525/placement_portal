# jobs/ml_utils.py
import torch
from transformers import BertTokenizer, BertModel
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re
import spacy
import os
from django.conf import settings


# Load pre-trained models
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')
nlp = spacy.load('en_core_web_sm')

# Skill extraction from text
def extract_skills(text):
    """Extract skills from text using spaCy NER and pattern matching"""
    # Common skills to look for
    tech_skills = [
        "python", "java", "javascript", "c++", "c#", "ruby", "php", "swift", "kotlin",
        "html", "css", "react", "angular", "vue", "node.js", "django", "flask", "spring",
        "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git", "terraform",
        "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "graphql",
        "machine learning", "deep learning", "neural networks", "nlp", "computer vision",
        "data analysis", "data science", "statistics", "r", "tableau", "power bi", 
        "excel", "powerpoint", "word", "project management", "agile", "scrum", "jira",
        "hadoop", "spark", "kafka", "tensorflow", "pytorch", "scikit-learn", "pandas"
    ]
    
    # Normalize text
    text = text.lower()
    
    # Extract skills using pattern matching
    found_skills = []
    for skill in tech_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', text):
            found_skills.append(skill)
    
    # Use spaCy for additional entities
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ["ORG", "PRODUCT"] and ent.text.lower() not in found_skills:
            found_skills.append(ent.text.lower())
    
    return found_skills

# Function to get BERT embeddings
def get_bert_embedding(text):
    """Get BERT embeddings for text"""
    # Tokenize and encode the text
    encoded_input = tokenizer(text, return_tensors='pt', truncation=True, max_length=512, padding='max_length')
    
    # Get model output
    with torch.no_grad():
        output = model(**encoded_input)
    
    # Use CLS token embedding (represents the entire sentence)
    sentence_embedding = output.last_hidden_state[:, 0, :].numpy()
    return sentence_embedding[0]

# Function to calculate semantic similarity
def calculate_semantic_similarity(text1, text2):
    """Calculate cosine similarity between two text embeddings"""
    embedding1 = get_bert_embedding(text1)
    embedding2 = get_bert_embedding(text2)
    
    # Reshape for sklearn cosine_similarity
    embedding1 = embedding1.reshape(1, -1)
    embedding2 = embedding2.reshape(1, -1)
    
    # Calculate cosine similarity
    similarity = cosine_similarity(embedding1, embedding2)[0][0]
    return similarity

# Function to extract text from resume
def extract_text_from_resume(resume_path):
    """Extract text from a resume file"""
    file_ext = os.path.splitext(resume_path)[1].lower()
    
    # Full path to the file
    full_path = os.path.join(settings.MEDIA_ROOT, resume_path)
    
    if file_ext == '.pdf':
        try:
            import PyPDF2
            with open(full_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    elif file_ext in ['.docx', '.doc']:
        try:
            import docx
            doc = docx.Document(full_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except Exception as e:
            print(f"Error extracting text from DOCX: {e}")
            return ""
    
    return ""

# Job matching function
def match_resume_to_job(resume_text, job_description, job_requirements):
    """
    Match a resume to a job using BERT embeddings and cosine similarity.
    Returns a score (0-100) and missing skills.
    """
    # Combine job description and requirements
    job_text = job_description + " " + job_requirements
    
    # Calculate semantic similarity
    similarity_score = calculate_semantic_similarity(resume_text, job_text)
    
    # Convert to percentage (0-100)
    match_percentage = int(similarity_score * 100)
    
    # Extract skills from resume and job
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_text)
    
    # Find missing skills
    missing_skills = [skill for skill in job_skills if skill not in resume_skills]
    
    return match_percentage, missing_skills[:5]  # Return top 5 missing skills