#!/usr/bin/env python3
"""
Test if server is running
"""
import socket

def test_port(host, port):
    """Test if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

if __name__ == "__main__":
    host = "localhost"
    port = 5000
    
    if test_port(host, port):
        print(f"✅ Server is running on {host}:{port}")
    else:
        print(f"❌ Server is NOT running on {host}:{port}")
        
    # Also test 127.0.0.1
    if test_port("127.0.0.1", port):
        print(f"✅ Server is running on 127.0.0.1:{port}")
    else:
        print(f"❌ Server is NOT running on 127.0.0.1:{port}")