const express = require('express');
const mysql = require('mysql2');

const app = express();

const PORT = 80;

const connection = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: 'password',
    database: 'sakila',
});

app.get('*', (req, res, next) => {
    connection.query(
        'SELECT * from film LIMIT 1;',
        (err, results, fields) => {
            if (err) throw err;
            res.status(200).json(results);
        }
    );
});

app.post('*', (req, res, next) => {
    connection.query(
        'INSERT INTO actor(first_name, last_name) VALUES(UUID(), UUID());',
        (err, results, fields) => {
            if (err) throw err;
            res.status(200).json(results);
        }
    );
});

app.listen(PORT, () => {
    console.log(`Listening on ${PORT}`);
});
