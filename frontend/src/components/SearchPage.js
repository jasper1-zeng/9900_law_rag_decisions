import React, { useState, useRef } from "react";
import "./SearchPage.css";
import button from "./assets/button.svg";
import addFile from "./assets/addFile.svg";
import avatar from "./assets/avatar.svg";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";

const SearchPage = () => {
    const navigate = useNavigate();
    const fileInputRef = useRef(null);
    const scrollRef = useRef(null);

    const [caseContent, setCaseContent] = useState("");
    const [caseTopic, setCaseTopic] = useState("");
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [displayedBotMessage, setDisplayedBotMessage] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const [conversationId, setConversationId] = useState(null);

    const handleButtonClick = () => {
        fileInputRef.current.click();
    };

    const handleFileChange = (event) => {
        const selectedFile = event.target.files[0];
        if (selectedFile) {
            console.log("File selected:", selectedFile.name);
        }
    };

    const handleApiSubmit = async () => {
        if (!caseContent && !caseTopic) return;

        const userMessage = `Case Content:\n${caseContent}\n\nCase Topic:\n${caseTopic}`;
        setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
        setCaseContent("");
        setCaseTopic("");
        setDisplayedBotMessage("");
        setIsTyping(true);
        setLoading(true);

        try {
            const res = await fetch("http://localhost:8000/api/v1/build-arguments", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer test-token"
                },
                body: JSON.stringify({
                    case_content: caseContent,
                    case_topic: caseTopic,
                    conversation_id: conversationId
                }),
            });

            const data = await res.json();
            const botText = JSON.stringify(data, null, 2);

            if (data.conversation_id) {
                setConversationId(data.conversation_id);
            }

            setMessages((prev) => [...prev, { role: "bot", content: "" }]);

            let index = 0;
            const interval = setInterval(() => {
                setDisplayedBotMessage((prev) => prev + botText.charAt(index));
                index++;
                if (index >= botText.length) {
                    clearInterval(interval);
                    setMessages((prev) => {
                        const updated = [...prev];
                        updated[updated.length - 1] = { role: "bot", content: data };
                        return updated;
                    });
                    setDisplayedBotMessage("");
                    setIsTyping(false);
                }
            }, 20);
        } catch (error) {
            console.error("API error:", error);
            setMessages((prev) => [...prev, { role: "bot", content: { error: "Failed to fetch response." } }]);
            setIsTyping(false);
        } finally {
            setLoading(false);
        }
    };

    const topics = [
        "Guardianship & Administration",
        "Commercial Tenancy",
        "Planning, Development & Valuation",
        "Building & Construction",
        "Strata Titles",
        "Community Titles",
        "Firearms & Security Licences",
        "Vocational Regulation",
        "Local Government (including dog & cat notices)",
        "Residential Parks, Caravan & Camping",
        "Equal Opportunity",
        "Incorporated Associations",
        "Road Traffic & Transport",
        "Mental Health",
        "Retirement Villages",
        "Environment & Resources",
        "Children & Community Services",
        "Voluntary Assisted Dying",
        "Other"
    ];

    // New preprocessing function to fix the numbered list formatting issue
    const preprocessMarkdown = (markdown) => {
        if (!markdown) return '';
        
        // Find the Key Insights section and fix the numbering
        if (markdown.includes('Key Insights')) {
            // Split by lines to process
            const lines = markdown.split('\n');
            let inInsightsSection = false;
            let insightTitle = null;
            
            // Process each line
            for (let i = 0; i < lines.length; i++) {
                // Check if we've entered the Key Insights section
                if (lines[i].includes('Key Insights')) {
                    inInsightsSection = true;
                    continue;
                }
                
                // Exit insight section when we hit the next section
                if (inInsightsSection && lines[i].startsWith('##')) {
                    inInsightsSection = false;
                    continue;
                }
                
                if (inInsightsSection) {
                    // Check if this is a numbered line (starts with a number and period)
                    if (/^\d+\.\s*$/.test(lines[i].trim())) {
                        insightTitle = lines[i].trim();
                        // Remove the number line since we'll merge it
                        lines[i] = '';
                        continue;
                    }
                    
                    // If we have a stored title and the current line starts with a word (likely insight title)
                    if (insightTitle && lines[i].trim() && /^[A-Z]/.test(lines[i].trim())) {
                        // Merge the number with the insight title
                        lines[i] = insightTitle + ' ' + lines[i];
                        insightTitle = null;
                    }
                }
            }
            
            // Rejoin the processed lines
            return lines.filter(line => line !== '').join('\n');
        }
        
        return markdown;
    };

    return (
        <div className="container">
            <div className="top-bar">
                <button className="nav-btn" onClick={() => navigate("/Chat")}>Chat</button>
                <button className="nav-btn">Build Arguments</button>
                <button className="nav-btn">Statement</button>
                <button className="nav-btn">Document</button>
                <img src={avatar} alt="User Avatar" className="avatar" />
            </div>

            <div className="main-container">
                <div className="sidebar">
                    <h2>SATCHAT</h2>
                    <button className="new-chat-btn">+ New Chat</button>
                    <div className="chat-history">
                        <h3>YESTERDAY</h3>
                        <ul>
                            <li>Rental Termination</li>
                            <li>Employment Rights</li>
                            <li>Contract Validity</li>
                        </ul>
                    </div>
                </div>

                <div className="main-content">
                    <header className="header">
                        <h1>SAT</h1>
                        <h2>SEARCH</h2>
                    </header>

                    <div style={{ marginBottom: "1rem" }}>
                        <textarea
                            placeholder="Enter case content..."
                            value={caseContent}
                            onChange={(e) => setCaseContent(e.target.value)}
                            style={{ width: "100%", height: "120px", padding: "10px" }}
                        />
                        <select
                            value={caseTopic}
                            onChange={(e) => setCaseTopic(e.target.value)}
                            style={{ width: "100%", marginTop: "10px", padding: "10px" }}
                        >
                            <option value="">Select a case topic...</option>
                            {topics.map((topic, index) => (
                                <option key={index} value={topic}>{topic}</option>
                            ))}
                        </select>
                        <button onClick={handleApiSubmit} className="nav-btn" style={{ marginTop: "10px" }}>
                            Submit to Build Arguments API
                        </button>
                    </div>

                    <div className="answer-section" ref={scrollRef}>
                        {messages.map((msg, i) => (
                            <div key={i} className={`chat-bubble ${msg.role === "user" ? "user" : "bot"}`}>
                                {typeof msg.content === "string" ? (
                                    <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{msg.content}</pre>
                                ) : msg.content.error ? (
                                    <p>{msg.content.error}</p>
                                ) : (
                                    <div className="formatted-response">
                                        {msg.content.related_cases?.length > 0 && (
                                            <>
                                                <h3>🔍 Related Cases (sorted by relevance)</h3>
                                                <ul>
                                                    {[...msg.content.related_cases]
                                                        .sort((a, b) => b.similarity_score - a.similarity_score)
                                                        .map((item, index) => (
                                                            <li key={index}>
                                                                <a href={item.url} target="_blank" rel="noopener noreferrer">
                                                                    <strong>{item.title}{item.citation_number ? ` (${item.citation_number})` : ''}</strong>
                                                                </a>
                                                                <p>{item.summary}</p>
                                                                <small>Similarity Score: {item.similarity_score}</small>
                                                            </li>
                                                        ))}
                                                </ul>
                                            </>
                                        )}

                                        {msg.content.raw_content && (
                                            <div className="raw-llm-content">
                                                <ReactMarkdown>
                                                    {preprocessMarkdown(msg.content.raw_content)}
                                                </ReactMarkdown>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}
                        {isTyping && (
                            <div className="chat-bubble bot">
                                <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{displayedBotMessage}</pre>
                            </div>
                        )}
                    </div>
                </div>

                <div className="links-window">
                    <h3>Links to Document and Website for this Response</h3>
                    <ul>
                        <li><a href="#">Link to website</a></li>
                        <li><a href="#">Link to document file</a></li>
                    </ul>
                </div>
            </div>
        </div>
    );
};

export default SearchPage;
