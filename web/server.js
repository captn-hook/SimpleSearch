const express = require('express');
const mongoose = require('mongoose');
const bodyParser = require('body-parser');
const fs = require('fs');
const multer = require('multer');
const path = require('path');
const pdfParse = require('pdf-parse');

const app = express();
app.use(bodyParser.json());

const mongoUrl = process.env.MONGO_URL || 'mongodb://localhost:27017/test';
mongoose.connect(mongoUrl);

const PDFSchema = new mongoose.Schema({
    name: String,
    data: Buffer,
    text: String,
});

const PDF = mongoose.model('PDF', PDFSchema);

app.get('/', (req, res) => {
    res.send(fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8'));
});

app.get('/export', async (req, res) => {
    const data = await Data.find();
    const filePath = path.join(__dirname, 'data.json');
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
    res.download(filePath, 'data.json', (err) => {
        if (err) {
            console.error(err);
        }
        fs.unlinkSync(filePath);
    });
});

const upload = multer({ dest: 'uploads/' });

app.post('/load', upload.single('file'), async (req, res) => {
    const filePath = req.file.path;
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    await Data.deleteMany({});
    await Data.insertMany(data);
    fs.unlinkSync(filePath);
    res.send('Data loaded!');
});



// Simple Text Search
app.get('/search-pdf', async (req, res) => {
    const searchText = req.query.searchText;
    const results = await PDF.find({ text: new RegExp(searchText, 'i') });
    res.json(results);
});

// View Document
app.get('/pdf/:id', async (req, res) => {
    const pdf = await PDF.findById(req.params.id);
    if (!pdf) {
        return res.status(404).send('Document not found');
    }
    res.contentType('application/pdf');
    res.send(pdf.data);
});

// View All Documents
app.get('/pdfs', async (req, res) => {
    // Only return the name and id of each document
    const pdfs = await PDF.find({}, { name: 1 });
    res.json(pdfs);
});

// Upload Document
app.post('/upload-pdf', upload.single('pdf'), async (req, res) => {
    const filePath = req.file.path;
    const dataBuffer = fs.readFileSync(filePath);
    const pdfData = await pdfParse(dataBuffer);
    const pdf = new PDF({
        name: req.file.originalname,
        data: dataBuffer,
        text: pdfData.text,
    });
    await pdf.save();
    fs.unlinkSync(filePath);
    res.send('PDF uploaded!');
});

app.listen(3000, () => {
    console.log('Server is running on port 3000');
    console.log('_    localhost:3000    _');
});