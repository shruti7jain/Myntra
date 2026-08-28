const { createServer } = require('http');
const { parse } = require('url');
const next = require('next');

const port = Number(process.env.PORT || 3000);
const hostname = '0.0.0.0';
const app = next({
  dev: false,
  hostname,
  port,
});
const handle = app.getRequestHandler();

app.prepare().then(() => {
  createServer((req, res) => {
    const parsedUrl = parse(req.url, true);
    handle(req, res, parsedUrl);
  }).listen(port, hostname, (err) => {
    if (err) throw err;
    console.log(`> Ready on http://${hostname}:${port}`);
  });
});
