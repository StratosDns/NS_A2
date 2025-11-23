/**
 * WebRTC Client Static File Server & Configuration Provider
 * 
 * This server has two main responsibilities:
 * 1. Serve static files (HTML, JS, CSS) for the WebRTC client application
 * 2. Provide runtime configuration to the client via /config endpoint
 */

const express = require('express');
const path = require('path');

// Server Configuration
const app = express();
const PORT = process.env.HTTP_PORT || 3000;

// Middleware for correct MIME type handling
app.use((req, res, next) => {
    if (req.path.endsWith('.js')) {
        res.type('application/javascript');
    }
    next();
});

// Static file serving from the public directory
app.use(express.static(path.join(__dirname, 'public')));

// Runtime Configuration Endpoint
app.get('/config', (req, res) => {
    // Convert internal Docker hostname to browser-accessible host
    const wsHost = "wss://localhost:8443";
    // Provide configuration from environment variables
    res.json({
        SIGNALING_URL: wsHost,
        NAME: process.env.NAME || 'client',
        ROLE: process.env.ROLE || 'caller',
        TOKEN: process.env.REG_TOKEN || null
    });
});

// Start Server
app.listen(PORT, () => {
    console.log(`
🚀 WebRTC Client Server Running
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Port: ${PORT}
• Static Files: ${path.join(__dirname, 'public')}
• Environment: ${process.env.NODE_ENV || 'development'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    `);
});
