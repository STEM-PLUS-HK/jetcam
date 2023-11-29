from .camera import Camera
import atexit
import cv2
import numpy as np
import threading
import traitlets
import os
import socket


class CSICamera(Camera):
    
    capture_device = traitlets.Integer(default_value=0)
    capture_fps = traitlets.Integer(default_value=30)
    capture_width = traitlets.Integer(default_value=640)
    capture_height = traitlets.Integer(default_value=480)
    
    def __init__(self, *args, **kwargs):
        super(CSICamera, self).__init__(*args, **kwargs)
        self.sock_addr = '/tmp/csi_socket'
        try:
            self._init_csi()
        except:
            self._remote_close()
            try:
                self._init_csi()
            except:
                raise RuntimeError('Could not initialize camera.  Please see error trace.')
        try:
            os.remove(self.sock_addr)
        except OSError:
            pass
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.sock_addr)
        self.sock.listen(1)
        self.sock.settimeout(1)
        self.sock_recv_thread_run = True
        self.sock_recv_thread = threading.Thread(target=self._sock_recv)
        self.sock_recv_thread.start()

        atexit.register(self.cap.release)
        atexit.register(self._end_sock_recv_thread)
                
    def _gst_str(self):
        return 'nvarguscamerasrc sensor-id=%d ! video/x-raw(memory:NVMM), width=%d, height=%d, format=(string)NV12, framerate=(fraction)%d/1 ! nvvidconv ! video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! videoconvert ! appsink' % (
                self.capture_device, self.capture_width, self.capture_height, self.capture_fps, self.width, self.height)
    
    def _read(self):
        re, image = self.cap.read()
        if re:
            return image
        else:
            raise RuntimeError('Could not read image from camera')
            
    def _init_csi(self):
        self.cap = cv2.VideoCapture(self._gst_str(), cv2.CAP_GSTREAMER)
        re, image = self.cap.read()
        if not re:
            raise RuntimeError('Could not read image from camera.')
            
    def _sock_recv(self):
        while self.sock_recv_thread_run
            conn, addr = self.sock.accept()
            while True:
                recv_data = conn.recv(1024).decode()
                if recv_data == "kill":
                    self.cap.release()
                    conn.sendall("is all yours".encode())
                    conn.close()
                    self.sock.close()
                    break
    
    def _end_sock_recv_thread(self):
        self.sock_recv_thread_run = False
        self.sock_recv_thread.join()
            
    def _remote_close(self):
        # try to connect other
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.sock.connect(self.sock_addr)
        except:
            raise RuntimeError('Could not connect to other python kernel that using the CSI camera')
        self.sock.settimeout(30)
        try:
            self.sock.sendall("kill".encode())
        except:
            raise RuntimeError("Failed to send kill signal to other python kernel")
        try:
            recv_data = self.sock.recv(1024).decode()
        except:
            raise RuntimeError("Failed to receive reply from other python kernel")
        if recv_data != "is all yours":
            raise RuntimeError("Failed to close other, message: " + recv_data)
        self.sock.close()
