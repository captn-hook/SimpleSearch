const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const multer = require('multer');
const path = require('path');
const pdfParse = require('pdf-parse');

const app = express();
app.use(bodyParser.json());


const storage = multer.memoryStorage();
const upload = multer({ storage });

app.get('/', (req, res) => {
    res.send(fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8'));
});

// Simple Text Search
app.get('/search', async (req, res) => {
    const query = req.query.q;
    if (!query) {
        return res.status(400).send('Query parameter is required');
    }

    try {
        // Search OpenSearch

        res.send('Search results');

    } catch (err) {
        console.error('Error searching documents:', err);
        res.status(500).send('Error searching documents');
    }
});

// View Document
app.get('/doc/:id', async (req, res) => {
    try {
     
        // Find the Doc by ID

        res.send('Document content');

    } catch (err) {
        console.error('Error retrieving document:', err);
        res.status(500).send('Error retrieving document');
    }
});

// View All Documents
app.get('/docs', async (req, res) => {
    try {
     
        // Find all Docs

        res.send('Documents');

    } catch (err) {
        console.error('Error retrieving documents:', err);
        res.status(500).send('Error retrieving documents');
    }
});

// Upload PDF Document
app.post('/upload-pdf', upload.single('pdf'), async (req, res) => {
       
    if (!req.file) {
        return res.status(400).send('PDF file is required');
    }

    try {

        // Parse the PDF
        const dataBuffer = req.file.buffer;
        const data = await pdfParse(dataBuffer);
        const text = data.text;

        // Store the PDF

        res.send('Document uploaded');
        
    } catch (err) {
        console.error('Error uploading pdf:', err);
        res.status(500).send('Error uploading document due to invalid file');
    }
});

app.listen(3000, () => {
    console.log('Server is running on port 3000');
    console.log('_    localhost:3000    _');
});