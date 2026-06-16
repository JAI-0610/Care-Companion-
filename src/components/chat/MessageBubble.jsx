import React from 'react';
import { Bot, User, AlertTriangle } from 'lucide-react';
import './MessageBubble.css';

const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';
  const isError = message.isError;

  const formatMessage = (content) => {
    return content.split('\n').map((line, index) => (
      <p key={index}>{line}</p>
    ));
  };

  const renderRecommendations = (recommendations) => {
    if (!recommendations) return null;

    return (
      <div className="recommendations">
        <h4>Recommended Medications:</h4>
        {recommendations.map((med, index) => (
          <div key={index} className="medication-card">
            <h5>{med.name}</h5>
            <p><strong>Reason:</strong> {med.reason}</p>
            <p><strong>Dosage:</strong> {med.dosage}</p>
            {med.warnings && med.warnings.length > 0 && (
              <div className="warnings">
                <strong>Warnings:</strong>
                <ul>
                  {med.warnings.map((warning, i) => (
                    <li key={i}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className={`message ${isUser ? 'user-message' : 'assistant-message'} ${isError ? 'error-message' : ''}`}>
      <div className="message-avatar">
        {isUser ? <User size={20} /> : isError ? <AlertTriangle size={20} /> : <Bot size={20} />}
      </div>
      <div className="message-content">
        <div className="message-text">
          {formatMessage(message.content)}
        </div>
        {message.recommendations && renderRecommendations(message.recommendations)}
        <div className="message-timestamp">
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;