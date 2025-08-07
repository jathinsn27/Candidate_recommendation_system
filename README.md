# Candidate recommendation system

An application that matches job descriptions with candidate resumes. Built using FastAPI backend and React frontend.

## What it does

You upload a job description and a bunch of resumes, and it tells you which candidates are the best fit. Two models - a generic sentence transformer model and a fine tuned model trained on recruitement dataset.

## How it works

### The embedding part
Both the job description and resumes get converted into vectors using sentence transformers.

### The matching part
Used cosine similarity to see how close the job description vector is to each resume vector. 

### The fine-tuning part

**Dataset**: Used a public dataset from Hugging Face with real job descriptions and resumes that were manually labeled as "good match" or "bad match".

**Method**: Only used the "good match" pairs to train the model. The idea is that if a human recruiter said these go together, the model should learn to put similar job resume pairs close together in that vector space.

**Training**: Used Multiple Negatives Ranking Loss - basically, for each good job-resume pair, we randomly pick other resumes as "negative examples" and teach the model to push the good pair closer together while pushing the bad pairs further apart.

## Tech stack

- **Backend**: FastAPI, sentence-transformers, scikit-learn
- **Frontend**: ReactJS
- **AI**: Sentence transformers for embeddings, Gemini for summary generation
- **File parsing**: pdfplumber, python-docx

## Setup

1. Clone the repo:
```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```
2. Install backend deps: 
```bash
cd backend
pip install -r requirements.txt
```
3. Create a .env file and add Gemini API key 
3. Train the model: 
```bash
cd backend/training
python training/train_model.py
```

5. Run backend: 
```bash
cd backend
uvicorn main:app --reload
```
6. Run frontend: 
```bash
cd frontend
npm install
npm start
```