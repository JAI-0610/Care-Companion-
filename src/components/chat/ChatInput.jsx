import React, { useState } from 'react';
import { Send, Mic } from 'lucide-react';
import './ChatInput.css';

const ChatInput = ({ onSendMessage, isLoading }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-input-container">
      <form onSubmit={handleSubmit} className="chat-input-form">
        <div className="input-wrapper">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Describe your symptoms... (e.g., I have headache and fever)"
            disabled={isLoading}
            rows="1"
            className="chat-input"
          />
          <div className="input-actions">
            <button type="button" className="voice-btn" disabled={isLoading}>
              <Mic size={20} />
            </button>
            <button 
              type="submit" 
              disabled={!message.trim() || isLoading}
              className="send-btn"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
        <div className="input-footer">
          <p className="disclaimer">
            💊 Remember: This is not medical advice. Always consult a healthcare professional.
          </p>
        </div>
      </form>
    </div>
  );
};

export default ChatInput;