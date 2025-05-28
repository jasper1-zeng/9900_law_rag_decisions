import React, { useState, useEffect } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import "./loginPage.css"; // Reuse login page CSS
import axios from "axios";
import avatar from "./assets/avatar.svg";

const ResetPassword = () => {
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    
    // Use useLocation to get token parameter from URL
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    const token = queryParams.get("token");

    useEffect(() => {
        // Check if token parameter exists in URL
        if (!token) {
            setError("Password reset link is invalid or expired");
        }
    }, [token]);

    const handleSubmit = async () => {
        // Validate password
        if (!password) {
            setError("Please enter a new password");
            return;
        }
        
        if (password !== confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        if (password.length < 8) {
            setError("Password must be at least 8 characters long");
            return;
        }

        try {
            setLoading(true);
            setError("");
            
            // Call backend API to reset password
            const response = await axios.post(
                `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/users/reset-password`,
                { 
                    token: token,
                    new_password: password 
                },
                {
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            
            // Show success message
            setSuccess(true);
        } catch (err) {
            console.error("Failed to reset password:", err);
            setError(err.response?.data?.detail || "Failed to reset password, the link may have expired");
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
                <h1 className="welcome-title">Reset Password</h1>

                {success ? (
                    <div>
                        <div className="success-message">Password has been successfully reset</div>
                        <button className="login-button" onClick={() => navigate("/")}>
                            Back to Login
                        </button>
                    </div>
                ) : (
                    <>
                        {/* Error message */}
                        {error && <div className="error-message">{error}</div>}

                        {!token ? (
                            <div className="error-message">Password reset link is invalid or expired</div>
                        ) : (
                            <>
                                {/* Password input */}
                                <div className="input-container">
                                    <label className="input-label">New Password</label>
                                    <input
                                        type="password"
                                        placeholder="Enter new password"
                                        className="input-field"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                    />
                                </div>

                                {/* Confirm Password input */}
                                <div className="input-container">
                                    <label className="input-label">Confirm Password</label>
                                    <input
                                        type="password"
                                        placeholder="Re-enter new password"
                                        className="input-field"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                    />
                                </div>

                                {/* Submit button */}
                                <button 
                                    className="login-button" 
                                    onClick={handleSubmit}
                                    disabled={loading}
                                >
                                    {loading ? "Resetting..." : "Reset Password"}
                                </button>
                            </>
                        )}

                        {/* Back to Login link */}
                        <div className="links-container">
                            <a href="/" className="link">Back to Login</a>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default ResetPassword; 