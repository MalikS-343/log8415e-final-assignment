const express = require('express');
const axios = require('axios');

const trustedHostIP = process.argv[2];
const PORT = 80;

const app = express();

app.use(express.json());

app.get('*', async (req, res, next) => {
    try {
        const response = await axios.get(`http://${trustedHostIP}:${PORT}/`);
        res.status(200).json(response.data);
    } catch (error) {
        res.status(500).send('Error fetching data');
    }
});

app.post('*', async (req, res, next) => {
    try {
        const response = await axios.post(`http://${trustedHostIP}:${PORT}/`, req.body);
        res.status(200).json(response.data);
    } catch (error) {
        res.status(500).send('Error posting data');
    }
});

app.listen(PORT, () => {
    console.log(`Listening on ${PORT}`);
});
