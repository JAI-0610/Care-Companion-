import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Bot, Shield, Zap, Users, ArrowRight } from 'lucide-react';
import './Home.css';

const Home = () => {
  const { user } = useAuth();

  const features = [
    {
      icon: <Bot size={32} />,
      title: 'AI-Powered Recommendations',
      description: 'Get personalized OTC medication suggestions based on your symptoms'
    },
    {
      icon: <Shield size={32} />,
      title: 'Safety First',
      description: 'Comprehensive safety checks and medical disclaimers'
    },
    {
      icon: <Zap size={32} />,
      title: 'Instant Results',
      description: 'Quick responses to help you make informed decisions'
    },
    {
      icon: <Users size={32} />,
      title: 'User-Friendly',
      description: 'Easy-to-use interface designed for everyone'
    }
  ];

  return (
    <div className="home">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <h1 className="hero-title">
            Your AI-Powered
            <span className="highlight"> OTC Medication </span>
            Assistant
          </h1>
          <p className="hero-description">
            Get safe, personalized over-the-counter medication recommendations based on your symptoms. 
            Always remember to consult with healthcare professionals for medical advice.
          </p>
          <div className="hero-actions">
            {user ? (
              <Link to="/chat" className="cta-button primary">
                Start Chat <ArrowRight size={20} />
              </Link>
            ) : (
              <>
                <Link to="/register" className="cta-button primary">
                  Get Started <ArrowRight size={20} />
                </Link>
                <Link to="/about" className="cta-button secondary">
                  Learn More
                </Link>
              </>
            )}
          </div>
          <div className="safety-notice">
            <Shield size={20} />
            <span>This is not a substitute for professional medical advice</span>
          </div>
        </div>
        <div className="hero-image">
          <div className="chat-preview">
            <div className="chat-message user">
              <span>I have a headache and mild fever</span>
            </div>
            <div className="chat-message assistant">
              <span>Based on your symptoms, I recommend acetaminophen or ibuprofen. Remember to stay hydrated!</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features">
        <div className="container">
          <h2 className="section-title">Why Choose Care Companion?</h2>
          <div className="features-grid">
            {features.map((feature, index) => (
              <div key={index} className="feature-card">
                <div className="feature-icon">
                  {feature.icon}
                </div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="how-it-works">
        <div className="container">
          <h2 className="section-title">How It Works</h2>
          <div className="steps">
            <div className="step">
              <div className="step-number">1</div>
              <h3>Describe Your Symptoms</h3>
              <p>Tell me about what you're experiencing in simple terms</p>
            </div>
            <div className="step">
              <div className="step-number">2</div>
              <h3>AI Analysis</h3>
              <p>Our system analyzes your symptoms and medical context</p>
            </div>
            <div className="step">
              <div className="step-number">3</div>
              <h3>Get Recommendations</h3>
              <p>Receive safe OTC medication suggestions with dosage info</p>
            </div>
            <div className="step">
              <div className="step-number">4</div>
              <h3>Consult Professional</h3>
              <p>Always verify with a healthcare provider before taking medications</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="container">
          <h2>Ready to Get Started?</h2>
          <p>Join thousands of users who trust Care Companion for OTC medication guidance</p>
          {user ? (
            <Link to="/chat" className="cta-button primary large">
              Start New Chat <ArrowRight size={20} />
            </Link>
          ) : (
            <Link to="/register" className="cta-button primary large">
              Create Free Account <ArrowRight size={20} />
            </Link>
          )}
        </div>
      </section>
    </div>
  );
};

export default Home;