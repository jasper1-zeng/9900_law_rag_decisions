import logo from './logo.svg';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import React, { useState, useEffect } from "react";

import LoginPage from './components/loginPage';
import SignUp from './components/signUp';
import ForgotPassword from './components/forgotPassword';
import ResetPassword from './components/resetPassword';
import ChatPage from './components/ChatPage';
import SearchPage from './components/SearchPage';
import CitationGraphPage from './components/CitationGraphPage';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check if user is already authenticated on component mount
  useEffect(() => {
    const authStatus = localStorage.getItem('isAuthenticated');
    const token = localStorage.getItem('token');
    if (authStatus === 'true' || token) {
      setIsAuthenticated(true);
    }
  }, []);

  // Handle login by storing auth state in localStorage
  const handleLogin = () => {
    localStorage.setItem('isAuthenticated', 'true');
    setIsAuthenticated(true);
  };

  // Handle logout
  const handleLogout = () => {
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('token');
    setIsAuthenticated(false);
  };

  return (
    <Router>
      <Routes>
        {/* Default route - show login page */}
        <Route path="/" element={isAuthenticated ? <Navigate to="/chat" /> : <LoginPage onLogin={handleLogin} />} />
        
        {/* Sign up route */}
        <Route path="/signup" element={isAuthenticated ? <Navigate to="/chat" /> : <SignUp onLogin={handleLogin} />} />

        {/* Forgot password route */}
        <Route path="/forgot-password" element={isAuthenticated ? <Navigate to="/chat" /> : <ForgotPassword />} />
        
        {/* Reset password route */}
        <Route path="/reset-password" element={isAuthenticated ? <Navigate to="/chat" /> : <ResetPassword />} />

        {/* Redirect to login if not authenticated */}
        <Route path="/chat" element={isAuthenticated ? <ChatPage onLogout={handleLogout} initialTask="chat" /> : <Navigate to="/" />} />
        
        {/* Build Arguments route */}
        <Route path="/build-arguments" element={isAuthenticated ? <ChatPage onLogout={handleLogout} initialTask="arguments" /> : <Navigate to="/" />} />

        {/* Build Arguments with single-call route */}
        <Route path="/build-arguments/single-call" element={isAuthenticated ? <ChatPage onLogout={handleLogout} initialTask="arguments" /> : <Navigate to="/" />} />

        {/* Statement route */}
        <Route path="/statement" element={isAuthenticated ? <ChatPage onLogout={handleLogout} initialTask="statement" /> : <Navigate to="/" />} />
        
        {/* Document route */}
        <Route path="/document" element={isAuthenticated ? <ChatPage onLogout={handleLogout} initialTask="document" /> : <Navigate to="/" />} />

        {/* Citation Graph routes */}
        <Route path="/citation-graph" element={isAuthenticated ? <CitationGraphPage onLogout={handleLogout} /> : <Navigate to="/" />} />
        <Route path="/citation-graph/case/:citation" element={isAuthenticated ? <CitationGraphPage onLogout={handleLogout} /> : <Navigate to="/" />} />

        <Route path="/search" element={<SearchPage />} />
      </Routes>
    </Router>
  );
}

export default App;
