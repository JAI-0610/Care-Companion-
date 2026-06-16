import React from 'react';
import { Bot, Shield, Heart, Users } from 'lucide-react';
import './About.css';

const About = () => {
  return (
    <div className="about-page">
      <div className="container">
        <div className="page-header">
          <h1>About Care Companion</h1>
          <p>Your trusted AI-powered OTC medication assistant</p>
        </div>

        <div className="about-content">
          <section className="mission-section">
            <h2>Our Mission</h2>
            <p>
              Care Companion is dedicated to making OTC medication information more accessible 
              and understandable. We believe everyone should have access to reliable, 
              easy-to-understand information about over-the-counter medications to make 
              informed decisions about their health.
            </p>
          </section>

          <section className="how-it-works-section">
            <h2>How Care Companion Works</h2>
            <div className="process-steps">
              <div className="step">
                <div className="step-icon">
                  <Users size={32} />
                </div>
                <h3>You Describe Your Symptoms</h3>
                <p>Tell us what you're experiencing in simple, everyday language</p>
              </div>
              <div className="step">
                <div className="step-icon">
                  <Bot size={32} />
                </div>
                <h3>AI Analysis</h3>
                <p>Our system analyzes your symptoms and provides relevant OTC options</p>
              </div>
              <div className="step">
                <div className="step-icon">
                  <Shield size={32} />
                </div>
                <h3>Safety First</h3>
                <p>We include important safety information and disclaimers</p>
              </div>
              <div className="step">
                <div className="step-icon">
                  <Heart size={32} />
                </div>
                <h3>Professional Consultation</h3>
                <p>We always recommend consulting with healthcare professionals</p>
              </div>
            </div>
          </section>

          <section className="disclaimer-section">
            <div className="disclaimer-card">
              <h3>Important Medical Disclaimer</h3>
              <p>
                Care Companion is an AI-powered information tool and does not provide 
                medical advice, diagnosis, or treatment. The information provided is 
                for educational purposes only and is not a substitute for professional 
                medical advice.
              </p>
              <ul>
                <li>Always consult with a qualified healthcare provider</li>
                <li>Never disregard professional medical advice</li>
                <li>Seek immediate medical attention for emergencies</li>
                <li>Read and follow all medication labels and instructions</li>
              </ul>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default About;