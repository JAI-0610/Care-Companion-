import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useChat } from '../context/ChatContext';
import ChatInterface from '../components/chat/ChatInterface';
import './Chat.css';

const Chat = () => {
  const { user } = useAuth();
  const { messages, sendMessage, startNewSession, currentSession } = useChat();

  const [selectedPrimary, setSelectedPrimary] = useState('');
  const [selectedSecondary, setSelectedSecondary] = useState([]);
  const [duration, setDuration] = useState('');
  const [durationUnit, setDurationUnit] = useState('days');
  const [showForm, setShowForm] = useState(!currentSession || messages.length === 0);

  // Sample symptom data
  const primarySymptoms = [
    'Headache',
    'Fever',
    'Cough',
    'Stomach Pain',
    'Sore Throat',
    'Chest Pain',
    'Joint Pain',
    'Skin Rash'
  ];

  const secondarySymptoms = [
    'Nausea',
    'Dizziness',
    'Fatigue',
    'Muscle Aches',
    'Runny Nose',
    'Sneezing',
    'Shortness of Breath',
    'Loss of Appetite',
    'Swelling',
    'Itching'
  ];

  const handleSecondarySymptomToggle = (symptom) => {
    if (selectedSecondary.includes(symptom)) {
      setSelectedSecondary(selectedSecondary.filter(s => s !== symptom));
    } else {
      setSelectedSecondary([...selectedSecondary, symptom]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const formattedMessage = `I am experiencing a primary symptom of ${selectedPrimary}.${
      selectedSecondary.length > 0 ? ' I also have: ' + selectedSecondary.join(', ') + '.' : ''
    } These symptoms have lasted for ${duration} ${durationUnit}. What OTC medications or steps do you recommend?`;
    
    // Start a new session and send prompt to backend
    startNewSession();
    setShowForm(false);
    await sendMessage(formattedMessage);
  };

  const handleReset = () => {
    setSelectedPrimary('');
    setSelectedSecondary([]);
    setDuration('');
    setDurationUnit('days');
  };

  if (!user) {
    return (
      <div className="auth-required">
        <div className="auth-message">
          <h2>Authentication Required</h2>
          <p>Please log in to access the symptom checker and get personalized medication recommendations.</p>
          <div className="auth-actions">
            <a href="/login" className="cta-button primary">Login</a>
            <a href="/register" className="cta-button secondary">Sign Up</a>
          </div>
        </div>
      </div>
    );
  }

  // Transition to full chat interface once form is submitted or if user resumes
  if (!showForm && currentSession) {
    return (
      <div className="chat-interface-wrapper">
        <div className="chat-top-bar">
          <button className="back-to-form-btn" onClick={() => setShowForm(true)}>
            ← Back to Symptom Checker
          </button>
        </div>
        <ChatInterface />
      </div>
    );
  }

  return (
    <div className="symptom-checker-page">
      <div className="symptom-checker-container">
        <h1>Symptom Checker</h1>
        <p className="subtitle">Select your symptoms to get personalized medication recommendations</p>
        
        {messages.length > 0 && (
          <div className="resume-chat-banner">
            <button type="button" onClick={() => setShowForm(false)}>
              Resume Existing Chat ({(currentSession?.title || 'Active Session').slice(0, 35)}) →
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="symptom-form">
          {/* Primary Symptom Selection */}
          <div className="symptom-section">
            <h2>Primary Symptom</h2>
            <p className="section-description">Select your main concern</p>
            <div className="symptoms-grid">
              {primarySymptoms.map(symptom => (
                <div 
                  key={symptom}
                  className={`symptom-card ${selectedPrimary === symptom ? 'selected' : ''}`}
                  onClick={() => setSelectedPrimary(symptom)}
                >
                  {symptom}
                </div>
              ))}
            </div>
          </div>

          {/* Secondary Symptoms Selection */}
          <div className="symptom-section">
            <h2>Additional Symptoms</h2>
            <p className="section-description">Select any other symptoms you're experiencing</p>
            <div className="symptoms-grid">
              {secondarySymptoms.map(symptom => (
                <div 
                  key={symptom}
                  className={`symptom-card ${selectedSecondary.includes(symptom) ? 'selected' : ''}`}
                  onClick={() => handleSecondarySymptomToggle(symptom)}
                >
                  {symptom}
                </div>
              ))}
            </div>
          </div>

          {/* Duration Selection */}
          <div className="symptom-section">
            <h2>Duration</h2>
            <p className="section-description">How long have you been experiencing these symptoms?</p>
            <div className="duration-input">
              <input
                type="number"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                placeholder="Enter duration"
                min="1"
                className="duration-field"
                required
              />
              <select 
                value={durationUnit} 
                onChange={(e) => setDurationUnit(e.target.value)}
                className="duration-unit"
              >
                <option value="hours">Hours</option>
                <option value="days">Days</option>
                <option value="weeks">Weeks</option>
                <option value="months">Months</option>
              </select>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="form-actions">
            <button 
              type="button" 
              onClick={handleReset}
              className="cta-button secondary"
            >
              Reset
            </button>
            <button 
              type="submit" 
              disabled={!selectedPrimary || !duration}
              className="cta-button primary"
            >
              Get Recommendations
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Chat;