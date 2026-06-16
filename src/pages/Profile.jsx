import React from 'react';
import { useAuth } from '../context/AuthContext';
import { User, Mail, Calendar, Shield } from 'lucide-react';
import './Profile.css';

const Profile = () => {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="auth-required">
        <div className="auth-message">
          <h2>Authentication Required</h2>
          <p>Please log in to view your profile.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="container">
        <div className="page-header">
          <h1>Your Profile</h1>
          <p>Manage your account information and preferences</p>
        </div>

        <div className="profile-content">
          <div className="profile-card">
            <div className="profile-header">
              <div className="avatar">
                <User size={32} />
              </div>
              <div className="profile-info">
                <h2>{user.firstName} {user.lastName}</h2>
                <p className="member-since">
                  Member since {new Date().toLocaleDateString()}
                </p>
              </div>
            </div>

            <div className="profile-details">
              <div className="detail-item">
                <Mail size={20} />
                <div>
                  <label>Email Address</label>
                  <p>{user.email}</p>
                </div>
              </div>

              <div className="detail-item">
                <Calendar size={20} />
                <div>
                  <label>Date of Birth</label>
                  <p>{user.dateOfBirth ? new Date(user.dateOfBirth).toLocaleDateString() : 'Not provided'}</p>
                </div>
              </div>

              <div className="detail-item">
                <Shield size={20} />
                <div>
                  <label>Account Type</label>
                  <p>Standard User</p>
                </div>
              </div>
            </div>
          </div>

          <div className="coming-soon-section">
            <h3>Additional Features Coming Soon</h3>
            <div className="features-grid">
              <div className="feature-card">
                <h4>Medical History</h4>
                <p>Store your medical conditions and allergies for better recommendations</p>
              </div>
              <div className="feature-card">
                <h4>Chat History</h4>
                <p>Review your previous conversations and recommendations</p>
              </div>
              <div className="feature-card">
                <h4>Preferences</h4>
                <p>Customize your experience and notification settings</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;