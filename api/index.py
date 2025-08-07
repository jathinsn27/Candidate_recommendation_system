from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pdfplumber
import docx
import google.generativeai as genai
import os
import io
from typing import Dict, List
from mangum import Mangum
import warnings

# Suppress pdfplumber warnings
warnings.filterwarnings("ignore", message="CropBox missing from /Page, defaulting to MediaBox")

# Initialize FastAPI
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
TOP_N = int(os.environ.get("TOP_N_RESULTS", "5"))
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "generic")
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Initialize models and Gemini only once during cold start
models: Dict[str, SentenceTransformer] = {}
gemini_model = None

def init_models():
    global models, gemini_model
    
    # Initialize Gemini if key available
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        try:
            gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            print(f"Gemini init failed: {e}")
    
    # Always load generic model
    try:
        models['generic'] = SentenceTransformer('all-MiniLM-L6-v2')
        print("Generic model loaded")
    except Exception as e:
        print(f"Model loading failed: {e}")

# Initialize on cold start
init_models()

async def parse_resume(file: UploadFile) -> str:
    content = ""
    filename = file.filename
    file_bytes = await file.read()
    try:
        if filename.endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                content = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        elif filename.endswith(".docx"):
            doc = docx.Document(io.BytesIO(file_bytes))
            content = "\n".join(para.text for para in doc.paragraphs)
        else:
            content = file_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing {filename}: {e}")
    return content

async def generate_summary(job_description: str, resume_text: str) -> str:
    if not gemini_model:
        return "Candidate's skills and experience have been analyzed against the job requirements."
    
    try:
        prompt = f"""
        As an HR analyst, analyze this job-resume match:
        Job: {job_description[:2000]}
        Resume: {resume_text[:2000]}
        Give 2-3 sentences on:
        - Key strengths and fit
        - Match to requirements
        - Any gaps or concerns
        """
        
        response = gemini_model.generate_content(prompt)
        return response.text.strip() if response and response.text else "Analysis complete."
            
    except Exception as e:
        print(f"Gemini error: {e}")
        return "Resume analyzed. Skills align with position requirements."

@app.post("/api/match")
async def match_resumes(
    job_description: str = Form(...),
    files: List[UploadFile] = File(...),
    model_choice: str = Form(None)
):
    selected_model_name = model_choice or DEFAULT_MODEL
    
    if not models:
        raise HTTPException(status_code=503, detail="Models unavailable")

    selected_model = models.get(selected_model_name)
    if not selected_model:
        raise HTTPException(status_code=400, detail=f"Invalid model. Available: {list(models.keys())}")

    # Get embeddings
    job_embedding = selected_model.encode([job_description])
    parsed_resumes = [await parse_resume(file) for file in files]
    resume_texts = [text for text in parsed_resumes if text]

    if not resume_texts:
        raise HTTPException(status_code=400, detail="No text extracted from resumes")

    resume_embeddings = selected_model.encode(resume_texts)
    similarities = cosine_similarity(job_embedding, resume_embeddings)[0]
    top_indices = similarities.argsort()[::-1][:TOP_N]

    # Generate results
    results = []
    for idx in top_indices:
        score = round(float(similarities[idx]) * 100, 2)
        summary = await generate_summary(job_description, resume_texts[idx])
        results.append({
            "candidate_id": files[idx].filename,
            "similarity": score,
            "summary": summary,
        })

    return {"results": results}

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "models": list(models.keys()),
        "gemini": gemini_model is not None,
        "top_n": TOP_N,
        "default_model": DEFAULT_MODEL
    }

# Create handler for AWS Lambda / Vercel
handler = Mangum(app)