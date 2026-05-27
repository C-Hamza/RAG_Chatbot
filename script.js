const API_BASE_URL = "http://localhost:8000";

// Initialize elements when DOM is ready
let fileInput, uploadBtn, clearBtn, userInput, sendBtn, chatHistory, uploadStatus;

function initializeElements() {
    fileInput = document.getElementById("fileInput");
    uploadBtn = document.getElementById("uploadBtn");
    clearBtn = document.getElementById("clearBtn");
    userInput = document.getElementById("userInput");
    sendBtn = document.getElementById("sendBtn");
    chatHistory = document.getElementById("chatHistory");
    uploadStatus = document.getElementById("uploadStatus");
    
    // Setup event listeners
    if (uploadBtn) uploadBtn.addEventListener("click", handleFileUpload);
    if (sendBtn) sendBtn.addEventListener("click", handleSendMessage);
    if (userInput) userInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    if (clearBtn) clearBtn.addEventListener("click", handleClearSession);
    
    console.log("✓ Elements initialized");
}

async function handleFileUpload() {
    const files = fileInput.files;
    if (files.length === 0) {
        showStatus("Please select files to upload", "error");
        return;
    }

    const formData = new FormData();
    for (let file of files) {
        formData.append("files", file);
    }

    uploadBtn.disabled = true;
    showStatus("Uploading and processing files...", "loading");

    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || "Upload failed");
        }

        const data = await response.json();
        showStatus(`✓ Successfully processed ${data.files_processed} files!`, "success");
        fileInput.value = "";
        addMessage("assistant", `Uploaded ${data.files_processed} document(s). You can now ask questions about them.`);
    } catch (error) {
        showStatus("Error uploading files: " + error.message, "error");
    } finally {
        uploadBtn.disabled = false;
    }
}

async function handleSendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    addMessage("user", message);
    userInput.value = "";
    sendBtn.disabled = true;
    userInput.focus();

    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ query: message }),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || "Chat request failed");
        }

        const data = await response.json();
        addMessage("assistant", data.response);
    } catch (error) {
        addMessage("assistant", "Error: Could not process your question. " + error.message);
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
}

async function handleClearSession() {
    if (confirm("Clear all documents and chat history? This cannot be undone.")) {
        try {
            const response = await fetch(`${API_BASE_URL}/clear`, {
                method: "POST",
            });

            if (response.ok) {
                chatHistory.innerHTML = "";
                showStatus("Session cleared", "success");
                addMessage("assistant", "Session cleared. Please upload new documents to continue.");
            } else {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || "Clear session failed");
            }
        } catch (error) {
            showStatus("Error clearing session: " + error.message, "error");
        }
    }
}

function addMessage(role, content) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${role}`;

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = role === "user" ? "You" : "Assistant";

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    contentDiv.textContent = content;

    messageDiv.appendChild(label);
    messageDiv.appendChild(contentDiv);

    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function showStatus(message, type) {
    uploadStatus.textContent = message;
    uploadStatus.className = `status-message ${type}`;
}

// Initialize when DOM is fully loaded
document.addEventListener("DOMContentLoaded", () => {
    initializeElements();
    testConnection();
});

// Test connection on load
async function testConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            console.log("✓ Connected to RAG Chatbot API");
            addMessage("assistant", "✓ Connected to backend! Upload documents to get started.");
        }
    } catch (error) {
        console.error("Connection error:", error);
        showStatus("Cannot connect to API. Make sure the server is running.", "error");
        addMessage("assistant", "⚠️ Cannot connect to backend API. Is the server running?");
    }
}
