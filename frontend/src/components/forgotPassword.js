import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./loginPage.css"; // Reuse login page CSS
import axios from "axios";
import avatar from "./assets/avatar.svg";

const ForgotPassword = () => {
    const [email, setEmail] = useState("");
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async () => {
        // Validate email
        if (!email) {
            setError("Please enter your email");
            return;
        }

        try {
            setLoading(true);
            setError("");
            
            // Call backend API to send password reset email
            const response = await axios.post(
                `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/users/forgot-password`,
                { email },
                {
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            
            // Show success message
            setSuccess(true);
        } catch (err) {
            console.error("Failed to send password reset email:", err);
            setError(err.response?.data?.detail || "Failed to send password reset email, please try again later");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            <div className="content-container">
                {/* Avatar */}
                <img src={avatar} alt="User Avatar" className="avatar" />

                {/* Title */}
                <h1 className="welcome-title">Forgot Password</h1>

                {success ? (
                    <div>
                        <div className="success-message">Password reset link has been sent to your email, please check your inbox</div>
                        <button className="login-button" onClick={() => navigate("/")}>
                            Back to Login
                        </button>
                    </div>
                ) : (
                    <>
                        {/* Error message */}
                        {error && <div className="error-message">{error}</div>}

                        {/* Email input */}
                        <div className="input-container">
                            <label className="input-label">Email</label>
                            <input
                                type="email"
                                placeholder="Enter your registered email"
                                className="input-field"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                        </div>

                        <div className="instruction-text">
                            We will send a password reset link to your email
                        </div>

                        {/* Submit button */}
                        <button 
                            className="login-button" 
                            onClick={handleSubmit}
                            disabled={loading}
                        >
                            {loading ? "Sending..." : "Send Reset Link"}
                        </button>

                        {/* Back to Login link */}
                        <div className="links-container">
                            <Link to="/" className="link">Back to Login</Link>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default ForgotPassword; 