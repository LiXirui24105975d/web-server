# Multi-Threaded Web Server
A robust, multi-threaded HTTP server built from scratch using Python's base socket programming.

## How to Run
1. Ensure you have Python 3.x installed.
2. Place your web files (HTML, images, etc.) in the same directory as `server.py`.
3. Run the server:

```bash
python server.py
```

To stop the server, press Ctrl+C.
## Testing
Open your browser and visit:
Default page: http://127.0.0.1:8080/
Specific file: http://127.0.0.1:8080/test.html
Error test (404): http://127.0.0.1:8080/noexist.html

## Supported Features
Multi-threading: Handles multiple concurrent client requests using the threading module.
HTTP Methods: Supports GET for file retrieval and HEAD for header-only requests.
Content Types: Automatically identifies MIME types for HTML, CSS, JS, JPG, PNG, and GIF.
Persistence: Supports keep-alive connections.
Caching: Implements 304 Not Modified using Last-Modified and If-Modified-Since headers.
Logging: Automatically generates server.log containing Client IP, Time, Filename, and Status Code.
Security: Basic directory traversal protection (prevents access to parent directories).

## File Structure
server.py: The core server implementation.
index.html: The default landing page.
test.html: Sample page for testing.
photo.jpg: Sample image for testing.
server.log: Log file (created on the first request).
README.md: Project documentation.

## Author
[Li Xirui] - [24105975D]

## GitHub Repository
[https://github.com/LiXirui24105975d/web-server]