const http = require("http");

const server = http.createServer((req, res) => {
  res.writeHead(200, {
    "Content-Type": "text/html"
  });

  res.end(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>RepoPilot Sandbox</title>
      </head>
      <body>
        <h1>🚀 RepoPilot Sandbox Works!</h1>
        <p>This application is running inside Docker.</p>
      </body>
    </html>
  `);
});

server.listen(3000, "0.0.0.0", () => {
  console.log("Server running on port 3000");
});
