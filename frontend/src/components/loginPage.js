import React from "react";
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./loginPage.css"; // Import CSS file
import axios from "axios";
import avatar from "./assets/avatar.svg";

const LoginPage = ({ onLogin }) => {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleLogin = async () => {
        // Validate form
        if (!email || !password) {
            setError("Please enter email and password");
            return;
        }

        try {
            setLoading(true);
            setError("");
            
            // Call backend API for login
            const response = await axios.post(
                `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/users/login`, 
                new URLSearchParams({
                    'username': email,
                    'password': password
                }),
                {
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                }
            );
            
            // Save token
            const { access_token } = response.data;
            localStorage.setItem('token', access_token);
            
            // Call login callback
            onLogin();
            
            // Redirect to chat page
            navigate("/chat");
        } catch (err) {
            console.error("Login failed:", err);
            if (err.response) {
                // The request was made and the server responded with a status code
                // that falls out of the range of 2xx
                setError(err.response.data?.detail || "Invalid credentials. Please check your email and password.");
            } else if (err.request) {
                // The request was made but no response was received
                setError("Unable to reach the server. Please try again later.");
            } else {
                // Something happened in setting up the request that triggered an Error
                setError("An error occurred. Please try again.");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            {/* Content container */}
            <div className="content-container">
                {/* Avatar */}
                <img src={avatar} alt="User Avatar" className="avatar" />

                {/* Welcome title */}
                <h1 className="welcome-title">Welcome</h1>

                {/* Error message */}
                {error && <div className="error-message">{error}</div>}

                {/* Email input */}
                <div className="input-container">
                    <label className="input-label">Email</label>
                    <input
                        type="email"
                        placeholder="Enter your email"
                        className="input-field"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />
                </div>

                {/* Password input */}
                <div className="input-container">
                    <label className="input-label">Password</label>
                    <input
                        type="password"
                        placeholder="Enter your password"
                        className="input-field"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                </div>

                {/* Sign Up and Forgot Password links */}
                <div className="links-container">
                    <Link to="/signup" className="link">Sign Up</Link>
                    <Link to="/forgot-password" className="link">Forgot Password?</Link>
                </div>

                {/* Login button */}
                <button 
                    className="login-button" 
                    onClick={handleLogin}
                    disabled={loading}
                >
                    {loading ? "Logging in..." : "Login"}
                </button>
            </div>
        </div>
    );
};

export default LoginPage;