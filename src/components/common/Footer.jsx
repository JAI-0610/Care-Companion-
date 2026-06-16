import React from 'react';
import { Link } from 'react-router-dom';
import { Stethoscope, Shield, Heart } from 'lucide-react';
import './Footer.css';

const Footer = () => {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-content">
          <div className="footer-section">
            <div className="footer-logo">
              <Stethoscope className="logo-icon" />
              <span>Care Companion</span>
            </div>
            <p className="footer-description">
              Your trusted AI-powered OTC medication recommendation platform. 
              Always consult with healthcare professionals for medical advice.
            </p>
            <div className="footer-features">
              <div className="feature">
                <Shield size={20} />
                <span>Safe & Secure</span>
              </div>
              <div className="feature">
                <Heart size={20} />
                <span>Health First</span>
              </div>
            </div>
          </div>

          <div className="footer-section">
            <h3>Quick Links</h3>
            <div className="footer-links">
              <Link to="/chat">Get Recommendations</Link>
              <Link to="/medications">Browse Medications</Link>
              <Link to="/about">How It Works</Link>
              <Link to="/disclaimer">Safety Info</Link>
            </div>
          </div>

          <div className="footer-section">
            <h3>Legal</h3>
            <div className="footer-links">
              <Link to="/disclaimer">Medical Disclaimer</Link>
              <a href="#privacy">Privacy Policy</a>
              <a href="#terms">Terms of Service</a>
              <a href="#cookies">Cookie Policy</a>
            </div>
          </div>

          <div className="footer-section">
            <h3>Emergency</h3>
            <div className="emergency-info">
              <p>In case of emergency, contact:</p>
              <div className="emergency-contacts">
                <a href="tel:911" className="emergency-link">911</a>
                <a href="tel:988" className="emergency-link">Suicide Prevention</a>
                <a href="tel:8002221222" className="emergency-link">Poison Control</a>
              </div>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <p>&copy; 2024 Care Companion. This is not medical advice. Consult healthcare professionals.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;