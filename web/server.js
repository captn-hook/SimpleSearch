const express = require('express');
const mongoose = require('mongoose');
const bodyParser = require('body-parser');
const fs = require('fs');
const multer = require('multer');
const path = require('path');
const pdfParse = require('pdf-parse');
const { MongoClient, GridFSBucket } = require('mongodb');

const app = express();
app.use(bodyParser.json());

const mongoUrl = process.env.MONGO_URL || 'mongodb://localhost:27017/test';
mongoose.connect(mongoUrl)
    .then(() => console.log('MongoDB connected'))
    .catch(err => console.error('MongoDB connection error:', err));

const conn = mongoose.connection;
let gfsBucket;

conn.once('open', () => {
    gfsBucket = new GridFSBucket(conn.db, { bucketName: 'uploads' });
});

const storage = multer.memoryStorage();
const upload = multer({ storage });

const PDFSchema = new mongoose.Schema({
    name: String,
    data: Buffer,
    text: String,
});

PDFSchema.index({ text: 'text' });

const PDF = mongoose.model('PDF', PDFSchema);

app.get('/', (req, res) => {
    res.send(fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8'));
});
app.get('/export', async (req, res) => {
    try {
        const data = await Data.find();
        const filePath = path.join(__dirname, 'data.json');
        fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
        res.download(filePath, 'data.json', (err) => {
            if (err) {
                console.error(err);
            }
            fs.unlinkSync(filePath);
        });
    } catch (err) {
        console.error('Error exporting data:', err);
        res.status(500).send('Error exporting data');
    }
});

app.post('/load', upload.single('file'), async (req, res) => {
    try {
        const filePath = req.file.path;
        const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        await Data.deleteMany({});
        await Data.insertMany(data);
        fs.unlinkSync(filePath);
        res.send('Data loaded!');
    } catch (err) {
        console.error('Error loading data:', err);
        res.status(500).send('Error loading data');
    }
});

// Simple Text Search
app.get('/search', async (req, res) => {
    const query = req.query.q;
    if (!query) {
        return res.status(400).send('Query parameter is required');
    }

    try {
        // Search in MongoDB
        const pdfs = await PDF.find({ $text: { $search: query } }, { name: 1 });

        if (!gfsBucket) {
            return res.status(500).send('GridFS bucket is not initialized');
        }

        // Search in GridFS
        const gridFsFiles = await gfsBucket.find().toArray();
        const gridFsPdfs = [];

        for (const file of gridFsFiles) {
            const downloadStream = gfsBucket.openDownloadStream(file._id);
            const chunks = [];
            downloadStream.on('data', chunk => chunks.push(chunk));
            await new Promise((resolve, reject) => {
                downloadStream.on('end', resolve);
                downloadStream.on('error', reject);
            });

            const buffer = Buffer.concat(chunks);
            const pdfData = await pdfParse(buffer);
            if (pdfData.text.includes(query)) {
                gridFsPdfs.push({ _id: file._id, name: file.filename });
            }
        }

        res.json([...pdfs, ...gridFsPdfs]);
    } catch (err) {
        console.error('Error searching PDFs:', err);
        res.status(500).send('Error searching PDFs');
    }
});

// View Document
app.get('/pdf/:id', async (req, res) => {
    try {
        const pdf = await PDF.findById(req.params.id);
        if (!pdf) {
            return res.status(404).send('Document not found');
        }
        res.contentType('application/pdf');
        res.send(pdf.data);
    } catch (err) {
        console.error('Error retrieving PDF:', err);
        res.status(500).send('Error retrieving PDF');
    }
});

// View All Documents
app.get('/pdfs', async (req, res) => {
    try {
        const pdfs = await PDF.find({}, { name: 1 });

        if (!gfsBucket) {
            return res.status(500).send('GridFS bucket is not initialized');
        }

        const gridFsFiles = await gfsBucket.find().toArray();
        const gridFsPdfs = gridFsFiles.map(file => ({ _id: file._id, name: file.filename }));

        res.json([...pdfs, ...gridFsPdfs]);
    } catch (err) {
        console.error('Error retrieving PDFs:', err);
        res.status(500).send('Error retrieving PDFs');
    }
});

// Upload Document
app.post('/upload-pdf', upload.single('pdf'), async (req, res) => {
    try {
        const pdfBuffer = req.file.buffer;
        const pdfData = await pdfParse(pdfBuffer);

        if (pdfBuffer.length > 16 * 1024 * 1024) {

            if (!gfsBucket) {
                return res.status(500).send('GridFS bucket is not initialized');
            }

            const uploadStream = gfsBucket.openUploadStream(req.file.originalname, {
                contentType: req.file.mimetype
            })
            
            uploadStream.end(pdfBuffer);
            uploadStream.on('finish', () => {
                res.send('PDF uploaded!');
            });
            uploadStream.on('error', (err) => {
                console.error('Error uploading PDF:', err);
                res.status(500).send('Error uploading PDF');
            });
            
        } else {
            const pdf = new PDF({
                name: req.file.originalname,
                data: pdfBuffer,
                text: pdfData.text,
            });
            await pdf.save();
            res.send('PDF uploaded!');
        }
    } catch (err) {
        console.error('Error uploading PDF:', err);
        res.status(500).send('Error uploading PDF due to invalid file');
    }
});

app.listen(3000, () => {
    console.log('Server is running on port 3000');
    console.log('_    localhost:3000    _');
});