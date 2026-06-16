import React from 'react';
import { useChat } from '../../context/ChatContext';
import { MessageSquare, Trash2, Calendar } from 'lucide-react';
import './ChatHistory.css';

const ChatHistory = () => {
  const { sessions, currentSession, loadSession } = useChat();

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return 'Today';
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  if (sessions.length === 0) {
    return (
      <div className="empty-history">
        <MessageSquare size={48} className="empty-history-icon" />
        <p>No chat history yet</p>
        <span>Start a new conversation to see it here</span>
      </div>
    );
  }

  return (
    <div className="chat-history">
      <div className="history-header">
        <h3>Chat History</h3>
        <span className="history-count">{sessions.length} conversations</span>
      </div>
      
      <div className="sessions-list">
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`session-item ${
              currentSession?.id === session.id ? 'session-active' : ''
            }`}
            onClick={() => loadSession(session.id)}
          >
            <div className="session-icon">
              <MessageSquare size={16} />
            </div>
            <div className="session-content">
              <div className="session-title">{session.title}</div>
              <div className="session-meta">
                <Calendar size={12} />
                <span>{formatDate(session.createdAt)}</span>
              </div>
            </div>
            <button className="delete-session-btn">
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ChatHistory;