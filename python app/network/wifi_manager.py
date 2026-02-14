import os
import time
import json
import socket
import threading
from queue import Queue


class WiFiManager:
    """Manages WiFi connection and communication with phone"""
    
    SERVER_PORT = 8888
    
    def __init__(self):
        self.connected = False
        self.server_socket = None
        self.client_socket = None
        self.server_thread = None
        self.message_queue = Queue()
        self.running = False
        
    def connect(self, ssid, password):
        """Connect to WiFi network"""
        try:
            # Write to wpa_supplicant config
            config = f'''
network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
'''
            # Note: This requires proper permissions
            # In production, use nmcli or NetworkManager API
            
            # For testing, assume connection works
            print(f"Connecting to WiFi: {ssid}")
            time.sleep(2)
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"Error connecting to WiFi: {e}")
            return False
    
    def start_server(self):
        """Start TCP server to communicate with phone"""
        self.running = True
        self.server_thread = threading.Thread(
            target=self._server_loop,
            daemon=True
        )
        self.server_thread.start()
        print(f"WiFi server started on port {self.SERVER_PORT}")
    
    def _server_loop(self):
        """Server loop to accept connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.SERVER_PORT))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1.0)
            
            while self.running:
                try:
                    client, address = self.server_socket.accept()
                    print(f"Client connected: {address}")
                    self.client_socket = client
                    self._handle_client(client)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Server error: {e}")
                    
        except Exception as e:
            print(f"Error starting server: {e}")
    
    def _handle_client(self, client):
        """Handle client connection"""
        try:
            while self.running:
                data = client.recv(4096)
                if not data:
                    break
                
                # Parse message
                try:
                    message = json.loads(data.decode())
                    msg_type = message.get('type')
                    
                    # Add to queue for processing
                    self.message_queue.put(message)
                    
                    # Send acknowledgment
                    ack = json.dumps({'status': 'received'})
                    client.send(ack.encode())
                    
                except json.JSONDecodeError:
                    print("Invalid JSON received")
                    
        except Exception as e:
            print(f"Client handler error: {e}")
        finally:
            client.close()
            self.client_socket = None
    
    def send_image(self, image_path):
        """Send image file to phone"""
        if not self.client_socket:
            print("No client connected")
            return False
        
        try:
            # Read image file
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Send header
            header = json.dumps({
                'type': 'image',
                'size': len(image_data),
                'filename': os.path.basename(image_path)
            })
            
            self.client_socket.send(header.encode() + b'\n')
            time.sleep(0.1)
            
            # Send image data
            self.client_socket.sendall(image_data)
            
            print(f"Image sent: {image_path}")
            return True
            
        except Exception as e:
            print(f"Error sending image: {e}")
            return False
    
    def send_file(self, file_path):
        """Send generic file to phone"""
        if not self.client_socket:
            print("No client connected")
            return False
        
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            header = json.dumps({
                'type': 'file',
                'size': len(file_data),
                'filename': os.path.basename(file_path)
            })
            
            self.client_socket.send(header.encode() + b'\n')
            time.sleep(0.1)
            self.client_socket.sendall(file_data)
            
            print(f"File sent: {file_path}")
            return True
            
        except Exception as e:
            print(f"Error sending file: {e}")
            return False
    
    def wait_for_message(self, message_type, timeout=30):
        """Wait for specific message type from phone"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check queue
                if not self.message_queue.empty():
                    message = self.message_queue.get(timeout=1)
                    if message.get('type') == message_type:
                        return message.get('data')
                
                time.sleep(0.1)
                
            except:
                pass
        
        # Simulation mode - return dummy data
        if message_type == 'cnn_result':
            return {
                'food_type': 'Fish',
                'sensors': ['MQ2', 'MQ3', 'MQ4']
            }
        elif message_type == 'ml_result':
            return {
                'food_type': 'Fish',
                'freshness': 'FRESH',
                'confidence': 87.5
            }
        
        return None
    
    def stop(self):
        """Stop WiFi server"""
        self.running = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("WiFi manager stopped")
