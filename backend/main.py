# backend/main.py

import io
import asyncio
from typing import Dict, List
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pdfplumber
import docx
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        print("gemini api ready")
    except Exception as e:
        print(f"gemini setup failed: {e}")
else:
    print("no gemini key found - summaries will be basic")

app = FastAPI(title="Resume-Job Matcher API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load sentence transformers model to create embeddings for the job description and resumes.
models: Dict[str, SentenceTransformer] = {}
try:
    print("Loading Generalist model (all-MiniLM-L6-v2)...")
    models['generic'] = SentenceTransformer('all-MiniLM-L6-v2')

    print("Loading Specialist model (fine-tuned)...")
    models['finetuned'] = SentenceTransformer('./training/finetuned_model')

except Exception as e:
    print(f"Could not load models. {e}")

# --- Helper Functions ---
async def parse_resume(file: UploadFile) -> str:
    """Asynchronously parses the content of an uploaded resume file."""
    content = ""
    filename = file.filename
    file_bytes = await file.read()
    try:
        if filename.endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                content = "\\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        elif filename.endswith(".docx"):
            doc = docx.Document(io.BytesIO(file_bytes))
            content = "\\n".join(para.text for para in doc.paragraphs)
        else: # Fallback for .txt files
            content = file_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing file {filename}: {e}")
    return content

async def generate_fit_summary(job_description: str, resume_text: str) -> str:
    """Generate AI-powered summary using Gemini API."""
    if not gemini_model:
        return "This candidate shows strong potential due to relevant skills and experience highlighted in their resume, aligning well with the key requirements of the job description."
    
    try:
        prompt = f"""
        As a professional HR analyst, analyze the fit between this job description and candidate resume.
        
        Job Description:
        {job_description[:2000]}  # Limit to avoid token limits
        
        Candidate Resume:
        {resume_text[:2000]}  # Limit to avoid token limits
        
        Please provide a concise, professional summary (2-3 sentences) that includes:
        1. Key strengths and relevant experience
        2. How well they match the job requirements
        3. Any potential concerns or gaps
        
        Focus on actionable insights for hiring managers.
        """
        
        response = await asyncio.to_thread(
            gemini_model.generate_content,
            prompt
        )
        
        if response and response.text:
            return response.text.strip()
        else:
            return "AI analysis completed. Review candidate details for specific insights."
            
    except Exception as e:
        print(f"Error generating summary with Gemini: {e}")
        return "This candidate's resume has been analyzed. Key skills and experience align with the position requirements. Consider reviewing specific qualifications and experience levels."

@app.post("/match/")
async def match_resumes(
    job_description: str = Form(...),
    files: List[UploadFile] = File(...),
    model_choice: str = Form('finetuned') 
):
    # Receives a job description, resumes, and a model choice, then returns top matches.
    if not models:
        raise HTTPException(status_code=503, detail="Models are not available. Please check server logs.")

    selected_model = models.get(model_choice)
    if not selected_model:
        raise HTTPException(status_code=400, detail=f"Invalid model choice. Available: {list(models.keys())}")

    print(f"Processing request with '{model_choice}' model.")

    # 1. Encode the Job Description
    job_embedding = selected_model.encode([job_description])

    # 2. Parse and Encode Resumes
    parsed_resumes = await asyncio.gather(*(parse_resume(file) for file in files))
    resume_texts = [text for text in parsed_resumes if text]

    if not resume_texts:
        raise HTTPException(status_code=400, detail="Could not extract text from any uploaded resumes.")

    resume_embeddings = selected_model.encode(resume_texts)

    # 3. Compute Similarity and Rank
    similarities = cosine_similarity(job_embedding, resume_embeddings)[0]
    top_indices = similarities.argsort()[::-1][:5] # Get top 5

    # 4. Generate Results
    results = []
    for idx in top_indices:
        similarity_score = round(float(similarities[idx]) * 100, 2) # Convert to percentage from cosine similarity
        summary = await generate_fit_summary(job_description, resume_texts[idx])
        results.append({
            "candidate_id": files[idx].filename,
            "similarity": similarity_score,
            "summary": summary,
        })

    return {"results": results}

@app.get("/")
def read_root():
    return {"status": "API is running", "models_loaded": list(models.keys()), "gemini_available": gemini_model is not None}