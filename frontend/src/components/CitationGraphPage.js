import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './CitationGraphPage.css';

const CitationGraphPage = ({ onLogout }) => {
    const navigate = useNavigate();
    const location = useLocation();
    const iframeRef = useRef(null);
    const [loading, setLoading] = useState(false);
    const [iframeLoaded, setIframeLoaded] = useState(false);
    const [citationsToLoad, setCitationsToLoad] = useState([]);
    const [errorMessage, setErrorMessage] = useState('');
    const timeoutRef = useRef(null);
    
    // Switch to different tabs
    const switchTask = (task) => {
        switch(task) {
            case "chat":
                navigate("/chat");
                break;
            case "arguments":
                navigate("/build-arguments");
                break;
            case "citation-graph":
                navigate("/citation-graph");
                break;
            default:
                navigate("/chat");
        }
    };

    // Process auto-loading citation numbers from URL
    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const autoload = params.get('autoload');
        
        if (autoload) {
            try {
                // Parse the citation numbers from the URL
                const citations = decodeURIComponent(autoload).split(',');
                console.log("Auto-loading citations:", citations);
                
                // Format citation numbers properly for Neo4j
                const formatCitationNumber = (citation) => {
                    if (!citation) return '';
                    
                    // If citation already has brackets, return as is
                    if (citation.match(/^\[\d{4}\]/)) {
                        return citation;
                    }
                    
                    // Match the year at the beginning of the citation
                    const yearMatch = citation.match(/^(\d{4})\s/);
                    if (yearMatch) {
                        // Replace year with bracketed version
                        return citation.replace(/^(\d{4})\s/, '[$1] ');
                    }
                    
                    return citation;
                };
                
                // Format all citations
                const formattedCitations = citations
                    .filter(c => c && c.trim())
                    .map(c => formatCitationNumber(c));
                
                if (formattedCitations.length > 0) {
                    setLoading(true);
                    setErrorMessage('');
                    // Store the citations to be loaded once the iframe is ready
                    setCitationsToLoad(formattedCitations);
                }
            } catch (error) {
                console.error("Error parsing citations from URL:", error);
                setErrorMessage('Error parsing citation numbers from URL');
            }
        }
    }, [location.search]);
    
    // Send citations to iframe when it's loaded
    useEffect(() => {
        if (iframeLoaded && citationsToLoad.length > 0) {
            console.log("Iframe loaded, sending citations:", citationsToLoad);
            
            try {
                // Clear any previous timeout
                if (timeoutRef.current) {
                    clearTimeout(timeoutRef.current);
                }
                
                // Set a timeout to handle case where iframe doesn't respond
                timeoutRef.current = setTimeout(() => {
                    console.error("Timeout waiting for iframe response");
                    setLoading(false);
                    setErrorMessage('Timeout waiting for graph visualization to respond');
                }, 30000); // 30 seconds timeout for slower connections
                
                // Verify the iframe reference exists before using it
                if (iframeRef.current) {
                    // Simplify - use only a single postMessage with wildcard origin
                    console.log("Sending message to iframe");
                    iframeRef.current.contentWindow.postMessage({
                        type: 'ADD_CITATIONS',
                        citations: citationsToLoad,
                        timestamp: Date.now() // Add timestamp to ensure message uniqueness
                    }, '*');
                    
                    // Clear the citations to prevent sending them again
                    setCitationsToLoad([]);
                } else {
                    console.error("Iframe reference not available");
                    setLoading(false);
                    setErrorMessage('Visualization interface is not available');
                    clearTimeout(timeoutRef.current);
                }
            } catch (error) {
                console.error("Error sending message to iframe:", error);
                setLoading(false);
                setErrorMessage(`Error communicating with visualization: ${error.message}`);
                clearTimeout(timeoutRef.current);
            }
        }
    }, [iframeLoaded, citationsToLoad]);
    
    // Cleanup timeout on unmount
    useEffect(() => {
        return () => {
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
            }
        };
    }, []);

    // Handle iframe load event
    const handleIframeLoad = () => {
        console.log("Iframe loaded");
        
        // Wait a bit longer before setting iframe as loaded to ensure it's fully initialized
        setTimeout(() => {
            setIframeLoaded(true);
            
            // After iframe loads, check connection with a longer delay
            setTimeout(() => {
                if (iframeRef.current && iframeRef.current.contentWindow) {
                    try {
                        console.log("Sending connection check to iframe");
                        iframeRef.current.contentWindow.postMessage({
                            type: 'CHECK_CONNECTION',
                            timestamp: Date.now()
                        }, '*');
                    } catch (err) {
                        console.error("Error sending connection check:", err);
                    }
                }
            }, 2000); // Wait 2 seconds after load before checking connection
        }, 1000); // Wait 1 second before setting iframe as loaded
    };
    
    // Listen for messages from the iframe
    useEffect(() => {
        const handleMessage = (event) => {
            // Accept messages from any origin for maximum compatibility
            console.log("Received message from iframe:", event.origin, event.data);
            
            // Clear timeout since we got a response
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
                timeoutRef.current = null;
            }
            
            // Handle different message types
            if (event.data && event.data.type === 'CITATIONS_LOADED') {
                setLoading(false);
                if (!event.data.success) {
                    console.error("Error loading citations:", event.data.error);
                    setErrorMessage(`Error loading citations: ${event.data.error}`);
                } else {
                    setErrorMessage('');
                }
            } else if (event.data && event.data.type === 'VISUALIZATION_READY') {
                console.log("Visualization is ready, API URL:", event.data.apiUrl);
                // If we have citations waiting, send them now
                if (citationsToLoad.length > 0) {
                    console.log("Sending pending citations now that visualization is ready");
                    // Use setTimeout to ensure the visualization is fully initialized
                    setTimeout(() => {
                        try {
                            iframeRef.current?.contentWindow.postMessage({
                                type: 'ADD_CITATIONS',
                                citations: citationsToLoad
                            }, '*');
                        } catch (err) {
                            console.error("Error sending citations after ready:", err);
                        }
                    }, 500);
                }
            } else if (event.data && event.data.type === 'CONNECTION_OK') {
                console.log("Connection to visualization confirmed");
            }
        };
        
        // Add event listener
        window.addEventListener('message', handleMessage);
        
        // Clean up
        return () => {
            window.removeEventListener('message', handleMessage);
        };
    }, [citationsToLoad]);

    // Try reloading the visualization if there's an error
    const handleRetry = () => {
        setErrorMessage('');
        
        // If we have citations to retry
        if (citationsToLoad.length > 0) {
            setLoading(true);
            // The citations will be sent once the iframe reloads
            if (iframeRef.current) {
                iframeRef.current.src = iframeRef.current.src;
            }
        } else {
            // Reload the page to reset everything
            window.location.reload();
        }
    };

    return (
        <div className="citation-graph-page">
            {/* Navigation Header */}
            <div className="tab-navigation">
                <div className="tab-button" onClick={() => switchTask("chat")}>Chat</div>
                <div className="tab-button" onClick={() => switchTask("arguments")}>Build Arguments</div>
                <div className="tab-button active">Citation Graph</div>
                <div className="logout-button" onClick={onLogout}>Log Out</div>
            </div>

            {loading && (
                <div className="loading-overlay">
                    <div className="loading-spinner"></div>
                    <div className="loading-text">Loading citation graph with related cases...</div>
                </div>
            )}
            
            {errorMessage && (
                <div className="error-overlay">
                    <div className="error-icon">❌</div>
                    <div className="error-message">{errorMessage}</div>
                    <div className="error-buttons">
                        <button className="retry-button" onClick={handleRetry}>Retry</button>
                        {citationsToLoad.length > 0 && (
                            <button 
                                className="open-graph-button" 
                                style={{marginLeft: '10px', backgroundColor: '#065F46', color: 'white'}}
                                onClick={() => {
                                    // Open the Neo4j visualizer directly in a new tab with the citations
                                    const citationsParam = encodeURIComponent(citationsToLoad.join(','));
                                    window.open(`http://localhost:5001/visualizer?citations=${citationsParam}`, '_blank');
                                }}
                            >
                                Open in New Window
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Neo4j Visualizer iframe */}
            <div className="iframe-container">
                <iframe 
                    ref={iframeRef}
                    src={`http://localhost:5001/visualizer?hideHeader=true&useApi=true&allowMessages=true&t=${Date.now()}`}
                    title="Neo4j Case Graph Visualizer"
                    className="neo4j-iframe"
                    allow="fullscreen"
                    onLoad={handleIframeLoad}
                />
            </div>
            
            {/* Manual load button - shown when there's a timeout but there are citations to load */}
            {errorMessage && errorMessage.includes('timeout') && citationsToLoad.length > 0 && (
                <div className="manual-load-overlay">
                    <p>Communication with the visualization failed. You have two options:</p>
                    <div className="manual-load-buttons">
                        <button 
                            className="manual-load-button"
                            onClick={() => {
                                // Clear error and try again
                                setErrorMessage('');
                                setLoading(true);
                                
                                // Try to send the message directly
                                try {
                                    if (iframeRef.current && iframeRef.current.contentWindow) {
                                        iframeRef.current.contentWindow.postMessage({
                                            type: 'ADD_CITATIONS',
                                            citations: citationsToLoad,
                                            timestamp: Date.now()
                                        }, '*');
                                        
                                        // Set a new timeout
                                        if (timeoutRef.current) {
                                            clearTimeout(timeoutRef.current);
                                        }
                                        timeoutRef.current = setTimeout(() => {
                                            setLoading(false);
                                            setErrorMessage('Manual load attempt failed. Please refresh the page and try again.');
                                        }, 20000);
                                    }
                                } catch (err) {
                                    console.error("Error in manual load:", err);
                                    setLoading(false);
                                    setErrorMessage('Manual load attempt failed: ' + err.message);
                                }
                            }}
                        >
                            1. Try Again
                        </button>
                        
                        <button 
                            className="new-window-button"
                            style={{marginTop: '10px', backgroundColor: '#2196F3'}}
                            onClick={() => {
                                // Open the Neo4j visualizer directly in a new tab with the citations
                                const citationsParam = encodeURIComponent(citationsToLoad.join(','));
                                window.open(`http://localhost:5001/visualizer?citations=${citationsParam}`, '_blank');
                            }}
                        >
                            2. Open in New Window
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CitationGraphPage; 