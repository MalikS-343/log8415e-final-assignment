const MODES = Object.freeze({
    DIRECT_HIT: 'd',
    RANDOM: 'r',
    CUSTOMIZED: 'c'
});

const express = require('express');
const axios = require('axios');
const tcpp = require('tcp-ping');

const masterIP = process.argv[2];
const worker1IP = process.argv[3];
const worker2IP = process.argv[4];

const mode = process.argv[5];

const app = express();
const PORT = 80;

let bestWorker = '';

const selectBestWorker = () => {
    tcpp.ping({ address: worker1IP, attempts: 1 }, (err, worker1Res) => {
        tcpp.ping({ address: worker2IP, attempts: 1 }, (err, worker2Res) => {
            bestWorker = worker1Res.avg < worker2Res.avg ? worker1IP : worker2IP;
        });
    });
};

if (mode === MODES.CUSTOMIZED) {
    selectBestWorker();
    setInterval(() => selectBestWorker(), 100);
}

app.get('*', async (req, res) => {
    let ip = '';

    if (mode === MODES.DIRECT_HIT) {
        ip = masterIP;
    } else if (mode === MODES.RANDOM) {
        ip = Math.random() < 0.5 ? worker1IP : worker2IP;
    } else if (mode === MODES.CUSTOMIZED) {
        ip = bestWorker;
    }

    try {
        const response = await axios.get(`http://${ip}:${PORT}/`);
        res.status(200).json(response.data);
    } catch (error) {
        res.status(500).send('Error fetching data');
    }
});

app.post('*', async (req, res) => {
    try {
        const masterResponse = await axios.post(`http://${masterIP}:${PORT}/`, req.body);

        if (masterResponse.status !== 200) {
            return res.status(masterResponse.status).json(masterResponse.data);
        }

        await axios.post(`http://${worker1IP}:${PORT}/`, req.body);
        await axios.post(`http://${worker2IP}:${PORT}/`, req.body);

        res.status(200).json(masterResponse.data);
    } catch (error) {
        res.status(500).send('Error posting data');
    }
});

app.listen(PORT, () => {
    console.log(`Listening on ${PORT}`);
});
