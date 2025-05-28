import React from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./signUp.css"; // Import CSS file
import axios from "axios";
import avatar from "./assets/avatar.svg";

const SignUp = ({ onLogin }) => {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSignUp = async () => {
        // Validate form
        if (!email || !password || !confirmPassword) {
            setError("Please fill in all fields");
            return;
        }

        if (password !== confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        try {
            setLoading(true);
            setError("");
            
            // Call backend API to register user
            await axios.post(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/users/register`, {
                email,
                password
            });
            
            // Auto login after successful registration
            const loginResponse = await axios.post(
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
            const { access_token } = loginResponse.data;
            localStorage.setItem('token', access_token);
            
            // Call login callback
            onLogin();
            
            // Redirect to chat page
            navigate("/chat");
        } catch (err) {
            console.error("Registration failed:", err);
            if (err.response) {
                // The request was made and the server responded with a status code
                // that falls out of the range of 2xx
                setError(err.response.data?.detail || "Registration failed. This email may already be in use.");
            } else if (err.request) {
                // The request was made but no response was received
                setError("Unable to reach the server. Please try again later.");
            } else {
                // Something happened in setting up the request that triggered an Error
                setError("An error occurred during registration. Please try again.");
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
                <h1 className="welcome-title">Create Account</h1>

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
                <div className="input-container">
                    <label className="input-label">Confirm Password</label>
                    <input
                        type="password"
                        placeholder="Enter your password again"
                        className="input-field"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                </div>

                {/* Back to login */}
                <div className="links-container">
                    <a href="/" className="link">Back to Login</a>
                </div>

                {/* Sign Up button */}
                <button 
                    className="login-button" 
                    onClick={handleSignUp}
                    disabled={loading}
                >
                    {loading ? "Signing up..." : "Sign Up"}
                </button>
            </div>
        </div>
    );
};

export default SignUp;