// frontend/src/App.js

import React, { useState, useCallback } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [jobDescription, setJobDescription] = useState('');
  const [resumeFiles, setResumeFiles] = useState([]);
  const [modelChoice, setModelChoice] = useState('finetuned');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileChange = (event) => {
    const files = Array.from(event.target.files);
    // Filter for valid file types
    const validFiles = files.filter(file => {
      const validTypes = ['.pdf', '.docx', '.txt'];
      const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
      return validTypes.includes(fileExtension);
    });
    
    if (validFiles.length !== files.length) {
      setError('Some files were skipped. Only PDF, DOCX, and TXT files are supported.');
    }
    
    setResumeFiles(prev => [...prev, ...validFiles]);
    setError('');
  };

  const onDrop = useCallback((event) => {
    event.preventDefault();
    setIsDragOver(false);
    const files = Array.from(event.dataTransfer.files);
    
    // Filter for valid file types
    const validFiles = files.filter(file => {
      const validTypes = ['.pdf', '.docx', '.txt'];
      const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
      return validTypes.includes(fileExtension);
    });
    
    if (validFiles.length !== files.length) {
      setError('Some files were skipped. Only PDF, DOCX, and TXT files are supported.');
    }
    
    setResumeFiles(prev => [...prev, ...validFiles]);
    setError('');
  }, []);

  const onDragOver = (event) => {
    event.preventDefault();
    setIsDragOver(true);
  };

  const onDragLeave = (event) => {
    event.preventDefault();
    setIsDragOver(false);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!jobDescription.trim() || resumeFiles.length === 0) {
      setError('Please provide a job description and at least one resume.');
      return;
    }

    setIsLoading(true);
    setError('');
    setResults([]);

    const formData = new FormData();
    formData.append('job_description', jobDescription);
    formData.append('model_choice', modelChoice);
    resumeFiles.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await axios.post('http://127.0.0.1:8000/match/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setResults(response.data.results);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'An unexpected error occurred.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const getFileIcon = (fileName) => {
    if (fileName.toLowerCase().endsWith('.pdf')) return '📄';
    if (fileName.toLowerCase().endsWith('.docx')) return '📝';
    if (fileName.toLowerCase().endsWith('.txt')) return '📄';
    return '📁';
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const removeFile = (index) => {
    setResumeFiles(resumeFiles.filter((_, i) => i !== index));
  };

  const clearAllFiles = () => {
    setResumeFiles([]);
  };

  const selectAllFiles = () => {
    document.getElementById('file-input').click();
  };

  return (
    <div className="container">
      <div className="app-header">
        <h1 className="app-title">Resume-Job Matcher</h1>
        <p className="app-subtitle">Powered by Generalist and Specialist AI Models</p>
        <p className="app-description">
          Upload job descriptions and candidate resumes to find the best matches using advanced AI technology
        </p>
      </div>

      <div className="main-card">
        <form onSubmit={handleSubmit} className="form-section">
          <div className="form-group">
            <label htmlFor="job-description" className="form-label">
              Job Description
            </label>
            <textarea
              id="job-description"
              className="textarea-field"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the full job description here... Include requirements, responsibilities, and desired qualifications for better matching."
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Upload Resumes</label>
            <div
              className={`file-upload-area ${isDragOver ? 'dragover' : ''}`}
              onDrop={onDrop}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onClick={() => document.getElementById('file-input').click()}
            >
              <div className="file-upload-icon">📁</div>
              <div className="file-upload-text">Drag & drop multiple files here, or click to select files</div>
              <div className="file-upload-hint">Supports PDF, DOCX, and TXT files • You can select multiple files at once</div>
              <input
                type="file"
                id="file-input"
                className="file-input"
                multiple
                onChange={handleFileChange}
                accept=".pdf,.docx,.txt"
              />
            </div>
            
            {resumeFiles.length > 0 && (
              <div className="file-list">
                <div className="file-list-header">
                  <div className="file-list-title">
                    📎 Selected Files ({resumeFiles.length})
                  </div>
                  <div className="file-list-actions">
                    <button
                      type="button"
                      onClick={selectAllFiles}
                      className="file-action-btn add-btn"
                    >
                      ➕ Add More
                    </button>
                    <button
                      type="button"
                      onClick={clearAllFiles}
                      className="file-action-btn clear-btn"
                    >
                      🗑️ Clear All
                    </button>
                  </div>
                </div>
                {resumeFiles.map((file, index) => (
                  <div key={index} className="file-item">
                    <span className="file-icon">{getFileIcon(file.name)}</span>
                    <div className="file-info">
                      <span className="file-name">{file.name}</span>
                      <span className="file-size">{formatFileSize(file.size)}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="file-remove-btn"
                      title="Remove file"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="model-choice" className="form-label">
              Select AI Model
            </label>
            <select
              id="model-choice"
              className="model-select"
              value={modelChoice}
              onChange={(e) => setModelChoice(e.target.value)}
            >
              <option value="finetuned">🤖 Specialist (Fine-Tuned for Recruitment)</option>
              <option value="generic">🧠 Generalist (Standard Model)</option>
            </select>
          </div>

          <button 
            type="submit" 
            className="submit-button" 
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="loading-spinner"></span>
                Analyzing {resumeFiles.length} resume{resumeFiles.length !== 1 ? 's' : ''} with {modelChoice === 'finetuned' ? 'Specialist' : 'Generalist'} model...
              </>
            ) : (
              `🚀 Find Top Candidates (${resumeFiles.length} resume${resumeFiles.length !== 1 ? 's' : ''})`
            )}
          </button>
        </form>

        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        {isLoading && (
          <div className="loading-indicator">
            <span className="loading-spinner"></span>
            Processing {resumeFiles.length} resume{resumeFiles.length !== 1 ? 's' : ''} and finding the best matches...
          </div>
        )}

        {results.length > 0 && (
          <div className="results-section">
            <div className="results-header">
              <h2 className="results-title">Top Matches</h2>
              <p className="results-subtitle">
                Using {modelChoice === 'finetuned' ? 'Specialist' : 'Generalist'} AI model • 
                Analyzed {resumeFiles.length} resume{resumeFiles.length !== 1 ? 's' : ''}
              </p>
            </div>
            
            <div className="results-grid">
              {results.map((result, index) => (
                <div key={index} className="result-card">
                  <div className="result-header">
                    <span className="candidate-name">{result.candidate_id}</span>
                    <span className="similarity-score">{result.similarity}% Match</span>
                  </div>
                  <p className="summary">{result.summary}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;