import socket
import os
import threading
from datetime import datetime
import time

# Server configuration
HOST = '127.0.0.1'
PORT = 8080
LOG_FILE = 'server.log'
TIMEOUT = 5

def get_mime_type(path):
    """Return MIME type based on file extension"""
    if path.endswith('.html') or path.endswith('.htm'):
        return 'text/html'
    elif path.endswith('.jpg') or path.endswith('.jpeg'):
        return 'image/jpeg'
    elif path.endswith('.png'):
        return 'image/png'
    elif path.endswith('.gif'):
        return 'image/gif'
    elif path.endswith('.css'):
        return 'text/css'
    elif path.endswith('.js'):
        return 'application/javascript'
    else:
        return 'application/octet-stream'

def log_request(ip, filename, code):
    """Write request info to log file"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"{ip} | {now} | {filename} | {code}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line)
    print(f"[LOG] {line.strip()}")

def build_http_response(status_code, body, content_type='text/html', extra_headers=None):
    """
    Build a complete HTTP response.
    
    Parameters:
        status_code: int (200, 304, 400, 403, 404)
        body: bytes (response body, can be empty for HEAD or 304)
        content_type: str (MIME type)
        extra_headers: dict (additional headers like Last-Modified, Connection)
    
    Returns:
        bytes: complete HTTP response
    """
    # Status line mapping
    status_map = {
        200: "200 OK",
        304: "304 Not Modified",
        400: "400 Bad Request",
        403: "403 Forbidden",
        404: "404 Not Found",
        500: "500 Internal Error"
    }
    
    status_line = f"HTTP/1.1 {status_map.get(status_code, '500 Internal Error')}\r\n"
    
    # Build headers
    headers = f"Content-Type: {content_type}\r\n"
    headers += f"Content-Length: {len(body)}\r\n"
    
    # Add extra headers if provided
    if extra_headers:
        for key, value in extra_headers.items():
            headers += f"{key}: {value}\r\n"
    
    # End of headers
    headers += "\r\n"
    
    # Return full response
    return (status_line + headers).encode() + body

def send_response(client, status_code, body, content_type='text/html', extra_headers=None, method='GET'):
    """
    Send HTTP response to client.
    Handles HEAD method by sending headers only.
    """
    response = build_http_response(status_code, body, content_type, extra_headers)
    
    if method == 'HEAD':
        # HEAD: send only headers (strip the body)
        header_end = response.find(b'\r\n\r\n') + 4
        client.send(response[:header_end])
    else:
        client.send(response)

def send_error(client, status_code, conn_type, method):
    """Send error response using the unified build function"""
    if status_code == 400:
        body = b"<h1>400 Bad Request</h1><p>Invalid request format.</p>"
    elif status_code == 403:
        body = b"<h1>403 Forbidden</h1><p>Access denied.</p>"
    elif status_code == 404:
        body = b"<h1>404 Not Found</h1><p>File does not exist.</p>"
    else:
        body = b"<h1>500 Internal Error</h1>"
        status_code = 500
    
    extra = {"Connection": conn_type}
    send_response(client, status_code, body, 'text/html', extra, method)

def parse_request(data):
    """Extract method, filename, connection type, and if-modified-since from HTTP request"""
    lines = data.split('\r\n')
    if not lines:
        return None, None, 'close', None, True
    
    first = lines[0].split()
    if len(first) != 3:
        return None, None, 'close', None, True
    
    method = first[0]
    filename = first[1]
    conn = 'close'
    ims = None
    
    if method not in ['GET', 'HEAD']:
        return method, filename, conn, ims, True
    
    for line in lines[1:]:
        low = line.lower()
        if low.startswith('connection:'):
            conn = line.split(':', 1)[1].strip().lower()
        elif low.startswith('if-modified-since:'):
            ims = line.split(':', 1)[1].strip()
    
    return method, filename, conn, ims, False

def safe_path(path):
    """Prevent directory traversal attacks"""
    norm = os.path.normpath(path)
    if norm.startswith('..') or os.path.isabs(norm):
        return False
    return True

def get_last_modified(path):
    """Get file's last modified time in HTTP format"""
    try:
        mtime = os.path.getmtime(path)
        return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(mtime))
    except:
        return None

def handle_connection(client, addr):
    """Handle a single client connection (may handle multiple requests if keep-alive)"""
    ip = addr[0]
    print(f"[Thread {threading.current_thread().name}] Client connected: {addr}")
    client.settimeout(TIMEOUT)
    
    while True:
        try:
            # Receive request data
            raw = client.recv(4096)
            
            # Handle empty data (client disconnected)
            if not raw:
                print(f"[Thread {threading.current_thread().name}] Client disconnected")
                break
            
            # Try to decode, if fails -> bad request
            try:
                decoded = raw.decode('utf-8', errors='ignore')
            except Exception:
                send_error(client, 400, 'close', 'GET')
                log_request(ip, '/unknown', 400)
                break
            
            if not decoded.strip():
                send_error(client, 400, 'close', 'GET')
                log_request(ip, '/unknown', 400)
                break
            
            print(f"[Thread {threading.current_thread().name}] Request received")
            
            # Parse request
            method, filename, conn_type, ims, bad = parse_request(decoded)
            
            # Bad request (400)
            if bad or method is None:
                send_error(client, 400, conn_type, method or 'GET')
                log_request(ip, filename or '/unknown', 400)
                if conn_type == 'close':
                    break
                continue
            
            # Set default filename
            if filename == '/':
                filename = '/index.html'
            filepath = filename[1:]
            
            # Forbidden path (403)
            if not safe_path(filepath):
                send_error(client, 403, conn_type, method)
                log_request(ip, filename, 403)
                if conn_type == 'close':
                    break
                continue
            
            # File not found (404)
            if not os.path.exists(filepath):
                send_error(client, 404, conn_type, method)
                log_request(ip, filename, 404)
                if conn_type == 'close':
                    break
                continue
            
            # File exists, get modification time
            modified = get_last_modified(filepath)
            
            # Check 304 Not Modified
            if ims and modified and ims == modified:
                extra = {"Connection": conn_type}
                send_response(client, 304, b'', 'text/html', extra, method)
                print(f"[Thread {threading.current_thread().name}] {filepath} (304)")
                log_request(ip, filename, 304)
            else:
                # Read file
                with open(filepath, 'rb') as f:
                    content = f.read()
                
                mime = get_mime_type(filepath)
                extra = {"Connection": conn_type}
                if modified:
                    extra["Last-Modified"] = modified
                
                send_response(client, 200, content, mime, extra, method)
                print(f"[Thread {threading.current_thread().name}] Sent {filepath} (200)")
                log_request(ip, filename, 200)
            
            # Close connection if requested
            if conn_type == 'close':
                print(f"[Thread {threading.current_thread().name}] Closing connection")
                break
                
        except socket.timeout:
            print(f"[Thread {threading.current_thread().name}] Timeout, closing")
            break
        except ConnectionResetError:
            print(f"[Thread {threading.current_thread().name}] Client reset connection")
            break
        except BrokenPipeError:
            print(f"[Thread {threading.current_thread().name}] Broken pipe")
            break
        except Exception as e:
            print(f"[Thread {threading.current_thread().name}] Error: {e}")
            break
    
    try:
        client.close()
    except:
        pass

def start_server():
    """Create socket, bind, listen and accept connections"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    
    print(f"Web server running at http://{HOST}:{PORT}")
    print("Supported: GET, HEAD, keep-alive, 304, logging")
    
    while True:
        try:
            client, addr = server.accept()
            thread = threading.Thread(target=handle_connection, args=(client, addr))
            thread.daemon = True
            thread.start()
        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"Accept error: {e}")

if __name__ == "__main__":
    start_server()