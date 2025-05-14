const WebSocket = require('ws');
const sqlite3 = require('sqlite3').verbose();
const express = require('express');
const path = require('path');

// Create and open SQLite database
let db = new sqlite3.Database('ARGUS_DATABASE.db', (err) => {
    if (err) {
        console.error(err.message);
    }
    console.log('Connected to the SQLite database.');
});

// Create table if it doesn't exist
db.run(`CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    message TEXT,
    image BLOB
    status TEXT DEFAULT 'unchecked'
)`);

// Create an Express app
const app = express();

// Serve static files from the "public" folder
app.use(express.static(path.join(__dirname, 'public')));

// Start an HTTP server to serve the frontend (HTML, CSS, JS)
const server = app.listen(3000, () => {
    console.log('HTTP server running on http://localhost:3000');
});

// Fetch unchecked alerts for Notifications
app.get('/alerts/unchecked', (req, res) => {
    const query = "SELECT * FROM alerts WHERE status = 'unchecked'";
    db.all(query, [], (err, rows) => {
        if (err) {
            console.error(err.message);
            res.status(500).json({ error: "Failed to fetch unchecked alerts" });
            return;
        }
        res.json(rows);
    });
});

// Fetch checked alerts for Records
app.get('/alerts/checked', (req, res) => {
    const query = "SELECT * FROM alerts WHERE status = 'checked' ORDER BY id DESC";
    db.all(query, [], (err, rows) => {
        if (err) {
            console.error(err.message);
            res.status(500).json({ error: "Failed to fetch checked alerts" });
            return;
        }
        res.json(rows);
    });
});

// Mark an alert as checked
app.post('/alerts/:id/check', (req, res) => {
    const alertId = req.params.id;
    const query = `UPDATE alerts SET status = 'checked' WHERE id = ?`;
    db.run(query, [alertId], function(err) {
        if (err) {
            console.error(err.message);
            res.status(500).json({ error: "Failed to update alert status" });
            return;
        }
        res.json({ message: "Alert status updated to 'checked'", id: alertId });
    });
});


// Create WebSocket server on top of the HTTP server
const wss = new WebSocket.Server({ server });

// Handle WebSocket connections
wss.on('connection', (ws) => {
    console.log('Client connected.');

    // Handle incoming messages
    ws.on('message', (data) => {
        try {
            // Parse the incoming data
            const parsedData = JSON.parse(data);
            const { message, image } = parsedData;

            // Convert the image (Base64) back to binary
            //const imageBuffer = Buffer.from(image, 'base64');

            // Store message and image in the SQLite database
            const sql = `INSERT INTO alerts (message, image, status) VALUES (?, ?, 'unchecked')`;
            db.run(sql, [message, image], function(err) {
                if (err) {
                    return console.error(err.message);
                }
                console.log(`Alert saved to database with ID: ${this.lastID}`);
            });

            // Broadcast the message and image to all connected clients
            const alertData = JSON.stringify({ message, image });
            wss.clients.forEach(function each(client) {
                if (client.readyState === WebSocket.OPEN) {
                    client.send(alertData);
                }
            });
        } catch (err) {
            console.error('Error processing message:', err);
        }
    });

    ws.on('close', () => {
        console.log('Client disconnected.');
    });
});
