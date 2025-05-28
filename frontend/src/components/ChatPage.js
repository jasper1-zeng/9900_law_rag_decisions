import React, { useState, useRef, useEffect } from "react";
import "./ChatPage.css";
import button from "./assets/button.svg";
import addFile from "./assets/addFile.svg";
import avatar from "./assets/avatar.svg";
import { useNavigate, useLocation } from "react-router-dom";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { getQuestionsByTask } from "../config/sampleQuestions";
// Import PDF.js (browser compatible)
import * as pdfjsLib from 'pdfjs-dist';
import { renderAsync } from 'docx-preview';

// Set PDF.js worker path
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

// Legal topics for the dropdown
const CASE_TOPICS = [
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

const ChatPage = ({ onLogout, initialTask = "chat" }) => {
    const navigate = useNavigate();
    const location = useLocation();
    const fileInputRef = useRef(null);
    const textAreaRef = useRef(null); // Direct reference to the textarea
    const scrollRef = useRef(null);

    const [inputMessage, setInputMessage] = useState("");
    const [messages, setMessages] = useState([]); // chat history
    const [displayedSections, setDisplayedSections] = useState([]);
    const [loading, setLoading] = useState(false);
    const [isTyping, setIsTyping] = useState(false);
    const [currentSection, setCurrentSection] = useState(0);
    const [allSections, setAllSections] = useState([]);
    const [messageId, setMessageId] = useState(null);
    // New state variables for conversation history
    const [conversations, setConversations] = useState([]);
    const [currentConversationId, setCurrentConversationId] = useState(null);
    const [fetchingHistory, setFetchingHistory] = useState(false);
    const [deletingConversation, setDeletingConversation] = useState(false);
    // Current active task (chat, arguments, statement, document)
    const [activeTask, setActiveTask] = useState(initialTask);
    // Sidebar visibility state
    const [isSidebarVisible, setIsSidebarVisible] = useState(() => {
        // Initialize from localStorage or default to visible
        const savedState = localStorage.getItem('sidebarVisible');
        return savedState !== null ? JSON.parse(savedState) : true;
    });
    const [fileUploading, setFileUploading] = useState(false);
    const [uploadedFileName, setUploadedFileName] = useState(null);
    const [uploadedFileSize, setUploadedFileSize] = useState(null);
    const [selectedTopic, setSelectedTopic] = useState("");
    const [selectedModel, setSelectedModel] = useState("deepseek-reasoner");

    // Helper function to add a message to the state
    const addMessageToState = (message) => {
        setMessages(prev => [...prev, message]);
    };

    // Toggle sidebar visibility
    const toggleSidebar = () => {
        const newState = !isSidebarVisible;
        setIsSidebarVisible(newState);
        // Save preference to localStorage
        localStorage.setItem('sidebarVisible', JSON.stringify(newState));
    };

    // Fetch conversation history on component mount and when active task changes
    useEffect(() => {
        fetchConversations();
        // Reset current conversation when task changes
        setCurrentConversationId(null);
        setMessages([]);
        // Reset file upload when switching tasks
        setUploadedFileName(null);
        setUploadedFileSize(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }, [activeTask]);

    // When initialTask changes, update activeTask
    useEffect(() => {
        if (initialTask !== activeTask) {
            setActiveTask(initialTask);
        }
    }, [initialTask]);

    // Fetch messages when conversation is selected
    useEffect(() => {
        if (currentConversationId) {
            fetchMessages(currentConversationId);
            
            // Reset file upload state when selecting a conversation
            setUploadedFileName(null);
            setUploadedFileSize(null);
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
            
            // Clear input message state
            setInputMessage("");
            
            // Reset textarea properly with a slight delay to ensure DOM is ready
            setTimeout(() => {
                resetTextarea();
            }, 50);
        }
    }, [currentConversationId]);

    // Resetting the selected topic when switching tasks or creating a new chat
    useEffect(() => {
        setSelectedTopic("");
    }, [activeTask]);

    // Switch active task with navigation
    const switchTask = (task) => {
        if (task !== activeTask) {
            switch(task) {
                case "chat":
                    navigate("/chat");
                    break;
                case "arguments":
                    navigate("/build-arguments");
                    break;
                case "statement":
                    navigate("/statement");
                    break;
                case "document":
                    navigate("/document");
                    break;
                default:
                    navigate("/chat");
            }
        }
    };

    // Get task title for conversation
    const getTaskTitle = (task) => {
        switch (task) {
            case "chat": return "Chat";
            case "arguments": return "Build Arguments";
            case "statement": return "Statement";
            case "document": return "Document";
            default: return "Chat";
        }
    };

    // Fetch all conversations
    const fetchConversations = async () => {
        try {
            const response = await fetch("http://localhost:8000/api/v1/conversations");
            if (response.ok) {
                const data = await response.json();
                
                // Filter conversations by task type
                const filteredConversations = data.filter(conv => {
                    // If conversation_type matches current task, or if it's undefined/null and current task is chat
                    return (conv.type === activeTask) || 
                           (!conv.type && activeTask === "chat");
                });
                
                setConversations(filteredConversations);
                
                // If there are conversations and no current conversation is selected,
                // select the most recent one (first in the list since they're sorted by updated_at desc)
                if (filteredConversations.length > 0 && !currentConversationId) {
                    setCurrentConversationId(filteredConversations[0].id);
                }
            } else {
                console.error("Failed to fetch conversations:", response.statusText);
            }
        } catch (error) {
            console.error("Error fetching conversations:", error);
        }
    };

    // Fetch messages for a specific conversation
    const fetchMessages = async (conversationId) => {
        setFetchingHistory(true);
        try {
            const response = await fetch(`http://localhost:8000/api/v1/conversations/${conversationId}/messages`);
            if (response.ok) {
                const data = await response.json();
                
                // Format messages for display
                const formattedMessages = data.map(msg => ({
                    id: msg.id,
                    role: msg.role,
                    content: msg.content,
                    isComplete: true // All fetched messages are complete
                }));
                
                setMessages(formattedMessages);
                
                // Scroll to the bottom after messages are loaded
                if (scrollRef.current) {
                    setTimeout(() => {
                        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                    }, 100);
                }
            } else {
                console.error("Failed to fetch messages:", response.statusText);
            }
        } catch (error) {
            console.error("Error fetching messages:", error);
        } finally {
            setFetchingHistory(false);
        }
    };

    // Create a new conversation
    const createNewChat = () => {
        setCurrentConversationId(null);
        setMessages([]);
        setSelectedTopic("");
        // Reset file upload state
        setUploadedFileName(null);
        setUploadedFileSize(null);
        
        // Reset file input value
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
        
        // Reset the input message
        setInputMessage("");
        
        // Reset textarea using our helper
        resetTextarea();
    };

    const handleButtonClick = () => {
        // First clear any previous file input state
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
        
        // Slight delay to ensure the input is cleared before opening the file dialog
        setTimeout(() => {
            fileInputRef.current.click();
        }, 10);
    };

    // Ensure textarea is in a good state
    const resetTextarea = (content = "") => {
        if (textAreaRef.current) {
            textAreaRef.current.value = content;
            setTimeout(() => {
                if (textAreaRef.current) {
                    textAreaRef.current.style.height = "auto";
                    if (content) {
                        textAreaRef.current.style.height = Math.min(400, textAreaRef.current.scrollHeight) + "px";
                        textAreaRef.current.focus();
                        textAreaRef.current.scrollTop = 0;
                    }
                }
            }, 50);
        }
    };

    const handleFileChange = async (event) => {
        const selectedFile = event.target.files[0];
        if (!selectedFile) {
            // If no file was selected (user cancelled), reset the input
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
            return;
        }
        
        // Clear previous content first
        setInputMessage("");
        
        setFileUploading(true);
        setUploadedFileName(selectedFile.name);
        setUploadedFileSize(formatFileSize(selectedFile.size));
        
        try {
            let fileContent = '';
            const fileType = selectedFile.type;
            
            // Process different file types
            if (fileType === 'application/pdf') {
                // For PDF files
                try {
                    const arrayBuffer = await selectedFile.arrayBuffer();
                    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
                    
                    // Extract text from each page
                    let pdfText = '';
                    for (let i = 1; i <= pdf.numPages; i++) {
                        const page = await pdf.getPage(i);
                        const textContent = await page.getTextContent();
                        const textItems = textContent.items.map(item => item.str);
                        pdfText += textItems.join(' ') + '\n\n';
                    }
                    
                    fileContent = pdfText;
                } catch (pdfError) {
                    console.error("PDF parsing error:", pdfError);
                    throw new Error("Could not parse PDF file.");
                }
            } else if (fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
                // For DOCX files
                try {
                    const arrayBuffer = await selectedFile.arrayBuffer();
                    
                    // Create a container to hold the rendered content
                    const container = document.createElement('div');
                    document.body.appendChild(container);
                    
                    // Render the DOCX to HTML
                    await renderAsync(arrayBuffer, container);
                    
                    // Extract text from the rendered HTML
                    fileContent = container.innerText;
                    
                    // Clean up the container
                    document.body.removeChild(container);
                } catch (docxError) {
                    console.error("DOCX parsing error:", docxError);
                    throw new Error("Could not parse DOCX file.");
                }
            } else {
                alert("Unsupported file type. Please upload PDF or Word documents.");
                setFileUploading(false);
                setUploadedFileName(null);
                setUploadedFileSize(null);
                // Reset file input so the same file can be selected again
                if (fileInputRef.current) {
                    fileInputRef.current.value = "";
                }
                return;
            }
            
            // Set the file content as the input message
            setInputMessage(fileContent);
            
            // Directly set the textarea value and adjust height using our ref
            resetTextarea(fileContent);
            
            console.log(`File "${selectedFile.name}" loaded successfully.`);
        } catch (error) {
            console.error("Error processing file:", error);
            alert("Error processing file. Please try again.");
            setUploadedFileName(null);
            setUploadedFileSize(null);
            // Reset file input so the same file can be selected again
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
        } finally {
            setFileUploading(false);
        }
    };

    // Helper function to format file size
    const formatFileSize = (bytes) => {
        if (bytes < 1024) return bytes + " bytes";
        else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
        else return (bytes / 1048576).toFixed(1) + " MB";
    };

    // Preprocessing function to fix numbered list formatting
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

    // Clear uploaded file and input
    const handleClearInput = () => {
        setInputMessage("");
        setUploadedFileName(null);
        setUploadedFileSize(null);
        
        // Reset textarea using our helper
        resetTextarea();
    };

    // Helper function to parse content into logical sections (headings and content)
    const parseMarkdownSections = (text) => {
        // Basic split by headings (h1, h2, h3)
        const headingRegex = /^(#{1,3})\s+(.+)$/gm;
        
        const sections = [];
        let lastIndex = 0;
        let match;

        // Capture text before the first heading
        match = headingRegex.exec(text);
        if (match && match.index > 0) {
            sections.push(text.substring(0, match.index).trim());
        }
        headingRegex.lastIndex = 0; // Reset regex index

        // Split text by headings
        while ((match = headingRegex.exec(text)) !== null) {
            const sectionContent = text.substring(lastIndex, match.index).trim();
            
            // Add heading as its own section if it's a case heading or main heading
            if (match[1].length <= 2 || match[2].includes("Case")) {
                if (sectionContent && sections.length > 0) {
                    // Append preceding content to the last section if it wasn't a heading section
                    sections[sections.length - 1] += '\n' + sectionContent;
                } else if (sectionContent) {
                     sections.push(sectionContent);
                }
                sections.push(match[0]); // Add heading itself
            } else if (sectionContent) {
                // Combine smaller non-case headings/content with previous
                if(sections.length > 0) {
                     sections[sections.length - 1] += '\n' + sectionContent + '\n' + match[0];
                } else {
                     sections.push(sectionContent + '\n' + match[0]);
                }
            }
            lastIndex = headingRegex.lastIndex;
        }

        // Add any remaining text after the last heading
        if (lastIndex < text.length) {
            const remainingText = text.substring(lastIndex).trim();
            if (remainingText) {
                 if(sections.length > 0) {
                     sections[sections.length - 1] += '\n' + remainingText;
                 } else {
                     sections.push(remainingText);
                 }
            }
        }

        // Filter out empty strings just in case
        return sections.filter(s => s.length > 0);
    };

    useEffect(() => {
        // When there are sections to display and we're typing
        if (isTyping && allSections.length > 0 && currentSection < allSections.length) {
            // Display next section
            const timer = setTimeout(() => {
                setDisplayedSections(prev => [...prev, allSections[currentSection]]);
                setCurrentSection(prev => prev + 1);
                
                // Scroll to the bottom with a slight delay to ensure DOM update
                setTimeout(() => {
                    if (scrollRef.current) {
                        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                    }
                }, 50);
                
                // If we've shown all sections, finish typing
                if (currentSection === allSections.length - 1) {
                    finishTyping();
                }
            }, Math.min(200, allSections[currentSection].length < 150 ? 150 : 200)); // Even faster for smaller sections
            
            return () => clearTimeout(timer);
        }
    }, [isTyping, allSections, currentSection]);
    
    const finishTyping = () => {
        setIsTyping(false);
        
        // Join sections, assuming LLM provided correct spacing
        const joinedText = allSections.join("\n");
        
        // Minimal cleanup: Ensure max 2 consecutive newlines
        const finalCleanedText = joinedText.replace(/\n{3,}/g, '\n\n');

        // Add the complete message to history, prepending the stored disclaimer
        setMessages(prev => {
            const newMessages = [...prev];
            if (messageId !== null) {
                const messageIndex = newMessages.findIndex(msg => msg.id === messageId);
                if (messageIndex !== -1) {
                    // Prepend the stored disclaimer (if any) to the final content
                    const prefix = newMessages[messageIndex].transientDisclaimer || '';
                    newMessages[messageIndex].content = prefix + finalCleanedText; 
                    newMessages[messageIndex].isComplete = true;
                    // Remove the temporary disclaimer field
                    delete newMessages[messageIndex].transientDisclaimer;
                }
            }
            return newMessages;
        });
        
        // After displaying the full content, update the conversation list without triggering message fetch
        // This ensures the conversation shows up in the sidebar but doesn't replace our formatted message
        fetchConversationsQuietly();
        
        // Clear variables
        setAllSections([]);
        setDisplayedSections([]);
        setCurrentSection(0);
        setMessageId(null);
    };
    
    // Fetch conversations without triggering message fetching
    const fetchConversationsQuietly = async () => {
        try {
            const response = await fetch("http://localhost:8000/api/v1/conversations");
            if (response.ok) {
                const data = await response.json();
                
                // Filter conversations by task type
                const filteredConversations = data.filter(conv => {
                    return (conv.type === activeTask) || 
                           (!conv.type && activeTask === "chat");
                });
                
                // Update conversations list without changing the current conversation ID
                // This prevents triggering the useEffect that would fetch messages
                setConversations(filteredConversations);
            }
        } catch (error) {
            console.error("Error fetching conversations:", error);
        }
    };

    const handleSendMessage = async () => {
        if (!inputMessage.trim() && !uploadedFileName) return;
        
        try {
            // Disable send button
            setLoading(true);
            
            // Determine the endpoint and payload based on the active task
            let endpoint = "";
            let payload = {};
            
            // Add the message to the local state immediately for better UX
            setMessages(prev => [...prev, { 
                id: Date.now().toString(),
                role: "user", 
                content: uploadedFileName ? `${inputMessage} [File: ${uploadedFileName}]` : inputMessage
            }]);
            
            // Clear input after sending, but save for history
            const messageToSend = inputMessage;
            setInputMessage("");
            
            // Reset textarea height
            resetTextarea();
            
            // Scroll to bottom after adding user message with enough delay for DOM update
            setTimeout(() => {
                if (scrollRef.current) {
                    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                }
            }, 100);
            
            // Additional scroll to make sure loading indicator is visible
            setTimeout(() => {
                if (scrollRef.current) {
                    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                }
            }, 300);
            
            if (activeTask === "chat") {
                endpoint = "http://localhost:8000/api/v1/chat";
                payload = {
                    message: messageToSend,
                    conversation_id: currentConversationId
                };
            } else if (activeTask === "arguments") {
                // Check if the URL has the single-call parameter
                const useSingleCall = window.location.pathname.includes("/single-call");
                
                endpoint = useSingleCall 
                    ? "http://localhost:8000/api/v1/build-arguments/single-call"
                    : "http://localhost:8000/api/v1/build-arguments";
                    
                payload = {
                    case_content: messageToSend,
                    case_topic: selectedTopic || null,
                    llm_model: selectedModel || "deepseek-reasoner",  // Change default back to DeepSeek
                    conversation_id: currentConversationId  // Add conversation_id for continuity
                };
                
                // Add detailed logging
                console.log(`Current URL path: ${window.location.pathname}`);
                console.log(`Single-call mode detected: ${useSingleCall}`);
                console.log(`Using endpoint: ${endpoint}`);
                console.log(`Selected model: ${selectedModel || 'deepseek-reasoner'}`);
            }
            
            const res = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer test-token",
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            let fullText = '';
            
            // Initialize variables at the function scope level, before the if/else block
            let contentToParse = '';
            let disclaimerBlock = '';
            
            // Different response format based on task
            if (activeTask === 'arguments') {
                // For arguments, get the raw content from the response
                disclaimerBlock = data.disclaimer || `> **DISCLAIMER:** *Analysis generated by ${selectedModel}. For informational purposes only.*\n\n`;
                
                // Use the raw content directly, maintaining LLM's original structured format
                contentToParse = data.raw_content || "";
                
                // If there are related cases, add them at the end
                const relatedCases = data.related_cases || [];
                
                if (relatedCases.length > 0) {
                    contentToParse += `\n\n## Related Cases\n\n`;
                    relatedCases.forEach((c, index) => {
                        // Clean up summary more aggressively
                        let cleanSummary = c.summary || '';
                        let caseTitle = c.title;
                        
                        // If the case doesn't have a proper title, create one from the first part
                        if (cleanSummary.startsWith("Introduction") || !caseTitle || caseTitle.trim() === "") {
                            // Extract a title from the first line if possible
                            const firstLineMatch = cleanSummary.match(/^Introduction\s*(.*?)\.?$/m);
                            if (firstLineMatch && firstLineMatch[1]) {
                                caseTitle = `Case ${index + 1}: ${firstLineMatch[1].trim()}`;
                            } else {
                                caseTitle = `Case ${index + 1}`;
                            }
                        }
                        
                        // Display the full case summary with proper title
                        contentToParse += `### [${caseTitle}${c.citation_number ? ` (${c.citation_number})` : ''}](${c.url})\n`;
                        contentToParse += `${cleanSummary}\n\n`;
                    });
                    
                    // Add a View in Citation Graph button after related cases - style it to look like a button
                    contentToParse += `\n\n---\n\n**[🔍 VISUALIZE: View All Related Cases in Citation Graph](#citation-graph-view)**\n\n---\n`;
                    
                    // Store citation numbers in a global variable for later use
                    window.relatedCasesCitations = relatedCases
                        .filter(c => c.citation_number)
                        .map(c => c.citation_number);
                }
                
                fullText = contentToParse; // Keep fullText for non-argument tasks if needed
                
            } else {
                // Standard chat response - reuse the variables declared above
                fullText = data.response;
                contentToParse = fullText; // Reuse variable from higher scope
                disclaimerBlock = ''; // Reuse variable from higher scope
            }
            
            // If this is a new conversation, set the conversation ID from the response
            if (!currentConversationId) {
                // For arguments, make sure to get the conversation_id from the response
                if (activeTask === 'arguments' && data.conversation_id) {
                    setCurrentConversationId(data.conversation_id);
                } else if (data.conversation_id) {
                    setCurrentConversationId(data.conversation_id);
                }
                // Only update the conversations list after the typing animation is complete
                // This prevents premature fetching of message history which would overwrite our formatted content
            }
            
            // Parse only the main content into sections
            const sections = parseMarkdownSections(contentToParse);
            
            // Create a unique ID for this message
            const newMessageId = Date.now().toString();
            
            // Add placeholder message, storing the disclaimer block separately
            setMessages(prev => [...prev, { 
                id: newMessageId,
                role: "bot", 
                content: "", 
                transientDisclaimer: disclaimerBlock, // Use a temporary field
                isComplete: false
            }]);
            
            // Set up the progressive section display
            setAllSections(sections);
            setDisplayedSections([]);
            setCurrentSection(0);
            setIsTyping(true);
            setMessageId(newMessageId);
            
            // Scroll to the new message with increased delay to ensure DOM update
            setTimeout(() => {
                if (scrollRef.current) {
                    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                }
            }, 150);
            
        } catch (error) {
            console.error("API error:", error);
            setLoading(false);
            setIsTyping(false);
        } finally {
            setLoading(false);
        }
    };

    // Delete a conversation
    const deleteConversation = async (conversationId, event) => {
        event.stopPropagation(); // Prevent selecting the conversation when clicking delete
        
        if (deletingConversation) return; // Prevent multiple delete requests
        
        setDeletingConversation(true);
        
        try {
            const response = await fetch(`http://localhost:8000/api/v1/conversations/${conversationId}`, {
                method: "DELETE",
                headers: {
                    "Authorization": "Bearer test-token",
                }
            });
            
            if (response.ok) {
                // First update the conversations list
                const updatedConversations = conversations.filter(conv => conv.id !== conversationId);
                setConversations(updatedConversations);
                
                // If the deleted conversation was the current one
                if (currentConversationId === conversationId) {
                    if (updatedConversations.length > 0) {
                        // Select the first conversation in the updated list
                        setCurrentConversationId(updatedConversations[0].id);
                    } else {
                        // No conversations left, create a new chat
                        createNewChat();
                    }
                }
            } else {
                console.error("Failed to delete conversation:", response.statusText);
            }
        } catch (error) {
            console.error("Error deleting conversation:", error);
        } finally {
            setDeletingConversation(false);
        }
    };

    // Sidebar conversation click handler
    const selectConversation = (conversationId) => {
        // Don't reload if it's the same conversation
        if (conversationId === currentConversationId) return;
        
        // Clear input and uploaded file state
        setInputMessage("");
        setUploadedFileName(null);
        setUploadedFileSize(null);
        
        // Reset textarea using our helper
        resetTextarea();
        
        // Reset file input value
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
        
        // Set the new conversation
        setCurrentConversationId(conversationId);
    };

    // Function to toggle between single-call and regular mode
    const toggleSingleCallMode = () => {
        const isSingleCallMode = location.pathname.includes("/single-call");
        if (isSingleCallMode) {
            navigate("/build-arguments");
        } else {
            navigate("/build-arguments/single-call");
        }
    };

    // Function to open the citation visualization with the given citations
    const openCitationVisualization = (citations) => {
        if (!citations || citations.length === 0) {
            addMessageToState({ content: "No citations available to visualize.", role: "assistant" });
            return;
        }

        // Normalize citations to ensure proper format
        const normalizedCitations = citations.map(normalizeCitationNumber);

        // Use the direct citations parameter format - the square brackets need to be preserved
        const neo4jBaseUrl = process.env.REACT_APP_NEO4J_VISUALIZATION_URL || 'http://localhost:5001';
        
        // Don't use encodeURIComponent - it encodes the square brackets which breaks the visualization
        // Instead, join with commas but keep the square brackets intact
        const citationsParam = normalizedCitations.join(',');
        const visualizationUrl = `${neo4jBaseUrl}/visualizer?citations=${citationsParam}&hideHeader=true`;
        
        // Open the visualization in a new window
        window.open(visualizationUrl, '_blank');
        
        // Show a confirmation message
        const citationsList = normalizedCitations.map(c => `"${c}"`).join(", ");
        const message = `
Opening citation graph visualization for ${citationsList} in a new tab.

If the window doesn't open, please check your browser's popup blocker.
`;
        
        addMessageToState({ content: message, role: "assistant" });
    };

    // Helper function to normalize citation number format
    const normalizeCitationNumber = (citation) => {
        if (!citation) return '';
        
        // Log original citation for debugging
        console.log('Normalizing citation:', citation);
        
        // Ensure year is in square brackets
        let normalized = citation;
        
        // If citation starts with 4 digits (year) but no brackets, add them
        if (/^\d{4}\s/.test(normalized)) {
            normalized = normalized.replace(/^(\d{4})(\s)/, '[$1]$2');
        }
        
        // Clean up spaces around brackets and ensure space follows closing bracket
        normalized = normalized.replace(/\[\s+/g, '[')
                              .replace(/\s+\]/g, ']')
                              .replace(/\](?!\s)/g, '] ');
        
        console.log('Normalized citation:', normalized);
        return normalized;
    };

    // Fix for the onClick handlers to pass citations
    const handleCitationGraphClick = (e) => {
        e.preventDefault();
        
        // Get stored citation numbers
        const citations = window.relatedCasesCitations || [];
        
        if (citations.length === 0) {
            addMessageToState({ content: "No citation numbers found to display in graph!", role: "assistant" });
            return;
        }
        
        // Open the visualization with these citations
        openCitationVisualization(citations);
    };

    return (
        <div className="container">
            <div className="top-bar">
                <button 
                    className={`nav-btn ${activeTask === 'chat' ? 'active' : ''}`}
                    onClick={() => switchTask('chat')}
                >
                    Chat
                </button>
                <button 
                    className={`nav-btn ${activeTask === 'arguments' ? 'active' : ''}`}
                    onClick={() => switchTask('arguments')}
                >
                    Build Arguments
                </button>
                <button 
                    className="nav-btn"
                    onClick={() => navigate('/citation-graph')}
                >
                    Citation Graph
                </button>
                {/* Commented out for future implementation
                <button 
                    className={`nav-btn ${activeTask === 'statement' ? 'active' : ''}`}
                    onClick={() => switchTask('statement')}
                >
                    Statement
                </button>
                <button 
                    className={`nav-btn ${activeTask === 'document' ? 'active' : ''}`}
                    onClick={() => switchTask('document')}
                >
                    Document
                </button>
                */}
                <div className="user-section">
                    <img src={avatar} alt="User Avatar" className="avatar" />
                    <button className="logout-btn" onClick={onLogout}>Logout</button>
                </div>
            </div>

            <div className="main-container">
                {/* Sidebar */}
                <div className={`sidebar ${isSidebarVisible ? 'visible' : 'hidden'}`}>
                    <h2>{getTaskTitle(activeTask)}</h2>
                    <button className="new-chat-btn" onClick={createNewChat}>+ New {activeTask === 'chat' ? 'Chat' : activeTask}</button>
                    <div className="chat-history">
                        <h3>RECENT</h3>
                        <ul>
                            {conversations.length > 0 ? (
                                conversations.map((conversation) => (
                                    <li 
                                        key={conversation.id}
                                        className={conversation.id === currentConversationId ? "active" : ""}
                                    >
                                        <div 
                                            className="conversation-title"
                                            onClick={() => selectConversation(conversation.id)}
                                        >
                                            {conversation.title}
                                        </div>
                                        <button 
                                            className="delete-conversation-btn"
                                            onClick={(e) => deleteConversation(conversation.id, e)}
                                            disabled={deletingConversation}
                                            title="Delete conversation"
                                            aria-label="Delete conversation"
                                            onMouseDown={(e) => e.stopPropagation()}
                                            onTouchStart={(e) => e.stopPropagation()}
                                        >
                                            ×
                                        </button>
                                    </li>
                                ))
                            ) : (
                                <li>No {activeTask} history yet</li>
                            )}
                        </ul>
                    </div>
                </div>
                
                {/* Toggle Button - positioned absolutely relative to main-container */}
                <button 
                    className={`sidebar-toggle ${!isSidebarVisible ? 'highlight' : ''}`}
                    onClick={toggleSidebar}
                    aria-label={isSidebarVisible ? "Hide sidebar" : "Show sidebar"}
                    title={isSidebarVisible ? "Hide sidebar" : "Show sidebar"}
                    style={{ left: isSidebarVisible ? '250px' : '0' }}
                >
                    {isSidebarVisible ? "◀" : "▶"}
                </button>

                {/* Main Content and Links Window Container */}
                <div className="content-wrapper">
                    <div className={`main-content ${!isSidebarVisible ? 'expanded' : ''}`}>
                        <header className="header">
                            <h1>SAT <span>{getTaskTitle(activeTask).toUpperCase()}</span>
                            {/* Add indicator for single-call mode */}
                            {activeTask === 'arguments' && window.location.pathname.includes("/single-call") && (
                                <span style={{
                                    fontSize: '14px',
                                    backgroundColor: '#065F46',
                                    color: 'white',
                                    padding: '3px 8px',
                                    borderRadius: '4px',
                                    marginLeft: '10px',
                                    verticalAlign: 'middle'
                                }}>SINGLE-CALL MODE</span>
                            )}
                            </h1>
                            
                            {/* Topic selection for Arguments task */}
                            {activeTask === 'arguments' && (
                                <div className="topic-selection">
                                    <label htmlFor="case-topic">Filter by Case Topic:</label>
                                    <select 
                                        id="case-topic"
                                        value={selectedTopic}
                                        onChange={(e) => setSelectedTopic(e.target.value)}
                                        className="topic-dropdown"
                                    >
                                        <option value="">All Topics</option>
                                        {CASE_TOPICS.map((topic, index) => (
                                            <option key={index} value={topic}>
                                                {topic}
                                            </option>
                                        ))}
                                    </select>
                                    
                                    {/* Add Single-Call Mode Toggle Button */}
                                    <button 
                                        onClick={toggleSingleCallMode}
                                        style={{
                                            marginLeft: '15px',
                                            padding: '5px 10px',
                                            backgroundColor: window.location.pathname.includes("/single-call") ? '#065F46' : '#e0e0e0',
                                            color: window.location.pathname.includes("/single-call") ? 'white' : 'black',
                                            border: 'none',
                                            borderRadius: '4px',
                                            cursor: 'pointer',
                                            fontSize: '12px'
                                        }}
                                    >
                                        {window.location.pathname.includes("/single-call") 
                                            ? "Switch to Multi-Step Mode" 
                                            : "Switch to Single-Call Mode"}
                                    </button>
                                </div>
                            )}
                        </header>

                        {/* 🧠 Chat display */}
                        <div className="answer-section" ref={scrollRef}>
                            {fetchingHistory && (
                                <div className="loading-history">Loading conversation history...</div>
                            )}
                            
                            {/* Complete messages */}
                            {messages.map((msg, idx) => (
                                msg.role === "user" ? (
                                    <div key={idx} className="chat-bubble user">
                                        {msg.content}
                                    </div>
                                ) : msg.isComplete ? (
                                    <div key={idx} className="chat-bubble bot">
                                        <ReactMarkdown 
                                            remarkPlugins={[remarkGfm]}
                                            rehypePlugins={[rehypeRaw]}
                                            components={{
                                                a: ({node, ...props}) => (
                                                    <a {...props} 
                                                      onClick={handleCitationGraphClick} 
                                                      target="_blank" 
                                                      rel="noopener noreferrer"
                                                      className={props.href === '#citation-graph-view' ? 'citation-graph-link' : ''} 
                                                    />
                                                ),
                                                li: ({node, ...props}) => (
                                                    <li className="markdown-list-item" {...props} />
                                                ),
                                                ul: ({node, ...props}) => (
                                                    <ul className="markdown-list" {...props} />
                                                ),
                                                p: ({node, ...props}) => (
                                                    <p className="markdown-paragraph" {...props} />
                                                ),
                                                h2: ({node, ...props}) => (
                                                    <h2 className="markdown-h2" style={{margin: "1.5em 0 0.5em", color: "#065F46"}} {...props} />
                                                ),
                                                h3: ({node, ...props}) => (
                                                    <h3 className="markdown-h3" style={{margin: "1.2em 0 0.3em", color: "#065F46"}} {...props} />
                                                ),
                                                strong: ({node, ...props}) => (
                                                    <strong style={{color: "#065F46"}} {...props} />
                                                )
                                            }}
                                        >
                                            {preprocessMarkdown(msg.content)}
                                        </ReactMarkdown>
                                        
                                        {/* Add a direct button component if the message contains related cases */}
                                        {msg.content && msg.content.includes('## Related Cases') && window.relatedCasesCitations && window.relatedCasesCitations.length > 0 && (
                                            <div className="citation-graph-container">
                                                <button 
                                                    className="citation-graph-button"
                                                    onClick={handleCitationGraphClick}
                                                    style={{
                                                        display: 'block',
                                                        width: '100%',
                                                        padding: '12px',
                                                        backgroundColor: '#065F46',
                                                        color: 'white',
                                                        border: 'none',
                                                        borderRadius: '5px',
                                                        fontWeight: 'bold',
                                                        cursor: 'pointer',
                                                        margin: '15px 0',
                                                        fontSize: '14px'
                                                    }}
                                                >
                                                    🔍 Visualize All Related Cases in Citation Graph
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                ) : null
                            ))}
                            
                            {/* Currently typing message */}
                            {isTyping && (
                                <div className="chat-bubble bot">
                                    <ReactMarkdown 
                                        remarkPlugins={[remarkGfm]}
                                        rehypePlugins={[rehypeRaw]}
                                        components={{
                                            a: ({node, ...props}) => (
                                                <a {...props} 
                                                  target="_blank" 
                                                  rel="noopener noreferrer"
                                                  className={props.href === '#citation-graph-view' ? 'citation-graph-link' : ''} 
                                                />
                                            ),
                                            li: ({node, ...props}) => (
                                                <li className="markdown-list-item" {...props} />
                                            ),
                                            ul: ({node, ...props}) => (
                                                <ul className="markdown-list" {...props} />
                                            ),
                                            p: ({node, ...props}) => (
                                                <p className="markdown-paragraph" {...props} />
                                            ),
                                            h2: ({node, ...props}) => (
                                                <h2 className="markdown-h2" style={{margin: "1.5em 0 0.5em", color: "#065F46"}} {...props} />
                                            ),
                                            h3: ({node, ...props}) => (
                                                <h3 className="markdown-h3" style={{margin: "1.2em 0 0.3em", color: "#065F46"}} {...props} />
                                            ),
                                            strong: ({node, ...props}) => (
                                                <strong style={{color: "#065F46"}} {...props} />
                                            )
                                        }}
                                    >
                                        {preprocessMarkdown(displayedSections.join(""))}
                                    </ReactMarkdown>
                                </div>
                            )}

                            {/* Loading indicator */}
                            {loading && !isTyping && (
                                <div className="chat-bubble bot loading-bubble">
                                    <span className="loading-text">Generating</span>
                                    <span className="loading-animation"></span>
                                </div>
                            )}
                        </div>

                        {/* Only show suggested questions when there's no conversation history */}
                        {messages.length === 0 && (
                            <div className="questions-section">
                                <ul>
                                    {getQuestionsByTask(activeTask).map((question, index) => (
                                        <li 
                                            key={index}
                                            onClick={() => {
                                                setInputMessage(question);
                                                document.querySelector('.text-input').focus();
                                            }}
                                        >
                                            {question}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Input box */}
                        <div className="message-input-container">
                            {uploadedFileName && (
                                <div className="uploaded-file-info">
                                    <div className="file-details">
                                        <span className="file-name">{uploadedFileName}</span>
                                        <span className="file-size">({uploadedFileSize})</span>
                                    </div>
                                    <button 
                                        className="clear-file-btn" 
                                        onClick={handleClearInput}
                                        title="Clear uploaded content"
                                    >
                                        ×
                                    </button>
                                </div>
                            )}
                            <div className="message-input">
                                <button 
                                    className={`file-upload-btn ${fileUploading ? 'uploading' : ''}`} 
                                    onClick={handleButtonClick}
                                    disabled={fileUploading}
                                    title={fileUploading ? "Processing file..." : "Upload document"}
                                >
                                    {fileUploading ? (
                                        <span className="file-upload-spinner"></span>
                                    ) : (
                                        <img src={addFile} alt="Add File" className="file-icon" />
                                    )}
                                </button>
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    style={{ display: "none" }}
                                    onChange={handleFileChange}
                                    accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                    disabled={fileUploading}
                                />
                                <textarea
                                    className="text-input"
                                    placeholder="Send a message..."
                                    value={inputMessage}
                                    ref={textAreaRef}
                                    onChange={(e) => {
                                        setInputMessage(e.target.value);
                                        // Auto-adjust height
                                        e.target.style.height = "auto";
                                        e.target.style.height = Math.min(400, e.target.scrollHeight) + "px";
                                    }}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter" && !e.shiftKey) {
                                            e.preventDefault();
                                            handleSendMessage();
                                        }
                                    }}
                                    rows="1"
                                />
                                {inputMessage.trim() && (
                                    <button className="clear-input-btn" onClick={handleClearInput} title="Clear input">
                                        ×
                                    </button>
                                )}
                                
                                {/* Model selection dropdown - only show for arguments task */}
                                {activeTask === 'arguments' && (
                                    <select 
                                        className="model-selector"
                                        title="Select AI model"
                                        style={{
                                            padding: '5px',
                                            fontSize: '12px',
                                            backgroundColor: '#f0f4f8',
                                            border: '1px solid #cad5e0',
                                            borderRadius: '4px',
                                            marginRight: '8px',
                                            color: '#065F46',
                                            width: '140px',
                                            minWidth: '140px'
                                        }}
                                        onChange={(e) => setSelectedModel(e.target.value)}
                                        defaultValue="deepseek-reasoner"
                                    >
                                        <option value="deepseek-reasoner">DeepSeek R1</option>
                                        <option value="claude-3-7-sonnet-20250219">Claude 3.7 Sonnet</option>
                                    </select>
                                )}
                                
                                <button className="send-btn" onClick={handleSendMessage}>
                                    <svg className="send-arrow-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M12 5V19M12 5L6 11M12 5L18 11" stroke="#065F46" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                    </svg>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatPage;
