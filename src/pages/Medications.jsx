import React, { useState } from 'react';
import axios from 'axios';
import { Search, Pill, ExternalLink, AlertTriangle, Clock, ShieldAlert, Sparkles, Activity } from 'lucide-react';
import './Medications.css';

const Medications = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState(null);

  const quickSymptoms = [
    { name: 'Cough', icon: '😷' },
    { name: 'Fever', icon: '🤒' },
    { name: 'Headache', icon: '🤕' },
    { name: 'Allergies', icon: '🌸' },
    { name: 'Heartburn', icon: '🔥' },
    { name: 'Sore Throat', icon: '🗣️' }
  ];

  const handleSearch = async (searchTerm) => {
    const term = searchTerm !== undefined ? searchTerm : query;
    if (!term.trim()) return;

    setLoading(true);
    setSearched(true);
    setError(null);

    try {
      const response = await axios.get(`/api/medications/search`, {
        params: { q: term }
      });
      setResults(response.data);
    } catch (err) {
      console.error('Error searching medications:', err);
      setError('Failed to fetch medications. Please check your network connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const getConditionColor = (purpose) => {
    const p = purpose.toLowerCase();
    if (p.includes('cough')) return '#3182ce'; // cool blue
    if (p.includes('fever') || p.includes('pain')) return '#dd6b20'; // warm orange
    if (p.includes('allergy') || p.includes('antihistamine')) return '#319795'; // teal
    if (p.includes('acid') || p.includes('heartburn') || p.includes('antacid')) return '#805ad5'; // purple
    if (p.includes('throat') || p.includes('anesthetic')) return '#d69e2e'; // yellow/amber
    return '#10b981'; // green default
  };

  return (
    <div className="medications-page">
      <div className="container">
        <div className="page-header">
          <div className="logo-badge">
            <Sparkles size={14} className="badge-sparkle" /> Live Drugs.com & FDA Integration
          </div>
          <h1>OTC Medications Directory</h1>
          <p>Search over-the-counter medications and get real-time safety warnings, dosage, and Drugs.com references.</p>
        </div>

        <div className="search-section">
          <div className="search-bar-wrapper">
            <div className="search-bar">
              <Search size={22} className="search-icon" />
              <input 
                type="text" 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Search by symptom or illness (e.g. cough, fever, allergy)..."
              />
              <button 
                onClick={() => handleSearch()} 
                disabled={loading}
                className="search-btn"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>
          </div>
          
          <div className="quick-search">
            <span className="quick-label">Quick Search:</span>
            <div className="quick-pills">
              {quickSymptoms.map((symptom) => (
                <button
                  key={symptom.name}
                  onClick={() => {
                    setQuery(symptom.name);
                    handleSearch(symptom.name);
                  }}
                  className="quick-pill"
                >
                  <span className="pill-emoji">{symptom.icon}</span>
                  {symptom.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="loading-state">
            <div className="pill-spinner">
              <Pill size={48} className="spinning-pill" />
            </div>
            <p>Fetching real-time medication data...</p>
          </div>
        ) : error ? (
          <div className="error-state">
            <AlertTriangle size={48} className="error-icon" />
            <p>{error}</p>
            <button onClick={() => handleSearch()} className="retry-btn">Retry Search</button>
          </div>
        ) : searched ? (
          <div className="results-container">
            <div className="results-header">
              <h2>Found {results.length} medication{results.length !== 1 ? 's' : ''} for "{query}"</h2>
              <span className="source-citation">FDA OTC Label Database & Drugs.com Search API</span>
            </div>
            
            <div className="medications-grid">
              {results.map((med, idx) => (
                <div key={idx} className="medication-card" style={{ '--card-theme': getConditionColor(med.purpose) }}>
                  <div className="card-top-accent" style={{ backgroundColor: getConditionColor(med.purpose) }}></div>
                  <div className="card-header">
                    <div className="pill-icon-wrapper" style={{ backgroundColor: getConditionColor(med.purpose) + '15', color: getConditionColor(med.purpose) }}>
                      <Pill size={24} />
                    </div>
                    <div className="title-area">
                      <h3>{med.brand_name}</h3>
                      <span className="generic-name">Active Ingredient: {med.generic_name}</span>
                    </div>
                  </div>

                  <div className="card-body">
                    <div className="info-badge-wrapper">
                      <span className="info-badge" style={{ backgroundColor: getConditionColor(med.purpose) + '15', color: getConditionColor(med.purpose) }}>
                        <Activity size={12} className="pulse-icon" /> {med.purpose}
                      </span>
                    </div>

                    <div className="info-section">
                      <h4 className="section-title-sm">
                        <Clock size={14} /> Dosage & Usage
                      </h4>
                      <p className="section-text">{med.dosage}</p>
                    </div>

                    <div className="info-section warning-section">
                      <h4 className="section-title-sm text-warning">
                        <ShieldAlert size={14} /> Safety Warnings
                      </h4>
                      <p className="section-text warning-text">{med.warnings}</p>
                    </div>
                  </div>

                  <div className="card-footer">
                    <a 
                      href={med.drugs_com_url} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="drugs-com-link"
                      style={{ color: getConditionColor(med.purpose), borderColor: getConditionColor(med.purpose) + '30' }}
                    >
                      View on Drugs.com <ExternalLink size={14} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="info-dashboard">
            <div className="dashboard-grid">
              <div className="dashboard-card main-info">
                <div className="dashboard-icon-header">
                  <Pill size={40} className="info-icon" />
                  <Sparkles size={24} className="accent-sparkle" />
                </div>
                <h2>Interactive OTC Directory</h2>
                <p>Welcome to the Care Companion medication center. Enter any illness or symptom above to retrieve trusted guidance on over-the-counter treatments, standard adult dosages, and clinical safety precautions.</p>
                <div className="safety-callout">
                  <AlertTriangle size={24} className="warning-icon" />
                  <div>
                    <strong>Important Safety Notice</strong>
                    <p>Always verify active ingredients. Never combine multiple multi-symptom remedies with overlapping ingredients to prevent accidental overdose.</p>
                  </div>
                </div>
              </div>
              
              <div className="dashboard-card guidelines-card">
                <h2>Real-Time Drugs.com Integration</h2>
                <p>Drugs.com is the most trusted, independent online resource for drug information. Every search result provides a direct verification link to access:</p>
                <ul className="guidelines-list">
                  <li>
                    <span className="bullet-point">✓</span>
                    <span><strong>Drug-to-Drug Interactions:</strong> Verify if the OTC drug safely interacts with your current prescriptions.</span>
                  </li>
                  <li>
                    <span className="bullet-point">✓</span>
                    <span><strong>Detailed Side Effects:</strong> Read verified patient and clinical reports on potential side effects.</span>
                  </li>
                  <li>
                    <span className="bullet-point">✓</span>
                    <span><strong>Age & Weight Restrictions:</strong> Confirm correct dosing scales for children and elderly individuals.</span>
                  </li>
                  <li>
                    <span className="bullet-point">✓</span>
                    <span><strong>FDA Announcements:</strong> Real-time alerts on product lots and recalls.</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Medications;