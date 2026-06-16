import React from 'react';
import { AlertTriangle, Shield, Phone, Heart } from 'lucide-react';
import './Disclaimer.css';

const Disclaimer = () => {
  return (
    <div className="disclaimer-page">
      <div className="container">
        <div className="page-header">
          <h1>Medical Disclaimer & Safety Information</h1>
          <p>Important information about using Care Companion</p>
        </div>

        <div className="disclaimer-content">
          <div className="warning-banner">
            <AlertTriangle size={32} />
            <div>
              <h3>Important Safety Notice</h3>
              <p>Care Companion is not a substitute for professional medical advice</p>
            </div>
          </div>

          <section className="disclaimer-section">
            <h2>Medical Disclaimer</h2>
            <p>
              The information provided by Care Companion, including but not limited to 
              OTC medication recommendations, dosage information, and symptom analysis, 
              is for informational and educational purposes only. It is not intended 
              to be a substitute for professional medical advice, diagnosis, or treatment.
            </p>
          </section>

          <section className="limitations-section">
            <h2>Limitations of the Service</h2>
            <div className="limitations-grid">
              <div className="limitation-card">
                <Shield size={24} />
                <h3>Not Medical Advice</h3>
                <p>We provide information, not medical advice. Always consult healthcare professionals.</p>
              </div>
              <div className="limitation-card">
                <AlertTriangle size={24} />
                <h3>Emergency Situations</h3>
                <p>In case of emergency, call emergency services immediately.</p>
              </div>
              <div className="limitation-card">
                <Heart size={24} />
                <h3>Individual Variations</h3>
                <p>Medication effects vary by individual. We cannot account for all personal factors.</p>
              </div>
            </div>
          </section>

          <section className="emergency-section">
            <h2>Emergency Contacts</h2>
            <div className="emergency-contacts">
              <a href="tel:911" className="emergency-contact primary">
                <Phone size={20} />
                <div>
                  <span>Emergency Services</span>
                  <span>911</span>
                </div>
              </a>
              <a href="tel:988" className="emergency-contact">
                <Heart size={20} />
                <div>
                  <span>Suicide & Crisis Lifeline</span>
                  <span>988</span>
                </div>
              </a>
              <a href="tel:8002221222" className="emergency-contact">
                <AlertTriangle size={20} />
                <div>
                  <span>Poison Control</span>
                  <span>800-222-1222</span>
                </div>
              </a>
            </div>
          </section>

          <section className="user-responsibility">
            <h2>Your Responsibility</h2>
            <p>
              By using Care Companion, you acknowledge and agree that:
            </p>
            <ul>
              <li>You will consult with a healthcare professional before taking any medication</li>
              <li>You will read and follow all medication labels and instructions</li>
              <li>You will disclose all medications and health conditions to your healthcare provider</li>
              <li>You understand the risks associated with self-medication</li>
              <li>You will seek immediate medical attention for serious symptoms</li>
            </ul>
          </section>

          <section className="acceptance-section">
            <div className="acceptance-card">
              <h3>Acceptance of Terms</h3>
              <p>
                By using the Care Companion service, you acknowledge that you have read, 
                understood, and agree to this medical disclaimer. You understand that 
                Care Companion and its creators are not liable for any decisions made 
                based on the information provided.
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Disclaimer;