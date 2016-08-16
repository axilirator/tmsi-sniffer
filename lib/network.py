#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# GR-GSM based TMSI sniffer
# Networking tools
#
# Research purposes only
# Use at your own risk
#
# Copyright (C) 2016  Vadim Yanitskiy <axilirator@gmail.com>
#
# All Rights Reserved
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import socket
import select

from log import *

class UDPServer:
	udp_rx_size = 1024

	def __init__(self, bind_port, remote_addr=False, remote_port=False):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.bind(('0.0.0.0', bind_port))
		self.sock.setblocking(0)

		self.udp_bind_port = bind_port
		self.udp_remote_addr = remote_addr
		self.udp_remote_port = remote_port

	def close(self):
		self.sock.close();

	def handle_rx_event(self):
		data, addr = self.sock.recvfrom(self.udp_rx_size)
		self.handle_rx_data(data)

	def handle_rx_data(self, data):
		raise NotImplementedError

	def send(self, data):
		if self.udp_remote_addr == False or self.udp_remote_port == False:
			raise Exception("UDP remote addr/port isn't set!")

		self.sock.sendto(data, (self.udp_remote_addr, self.udp_remote_port))

class TCPServer:
	tcp_rx_size = 1024
	connections = []
	max_conn = 10

	def __init__(self):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	def listen(self, bind_port, bind_host = "0.0.0.0"):
		self.sock.bind((bind_host, bind_port))
		self.sock.listen(self.max_conn)
		printl(DCTL, DINFO, "Server started, waiting for connections...")

	def accept(self):
		# Attempt to accept a new connection
		sockfd, addr = self.sock.accept()

		# Register this connection
		self.connections.append(sockfd)
		printl(DCTL, DINFO, "New connection from %s:%s" % addr)

	def handle_rx_event(self, socks):
		# Find all ready to read sockets
		for sock in self.connections:
			# Ok, we found one
			if sock in socks:
				data = sock.recv(self.tcp_rx_size)

				# Detect connection close
				if len(data) == 0:
					self.connections.remove(sock)
					self.handle_close_event()
				else:
					self.handle_rx_data(data)

	def send(self, sock, data):
		try:
			sock.send(data)
		except:
			sock.close()
			self.connections.remove(sock)
			self.handle_close_event()

	def broadcast(self, data):
		for sock in self.connections:
			self.send(sock, data)

	def handle_rx_data(self, data):
		raise NotImplementedError

	def handle_close_event(self):
		raise NotImplementedError

	def close(self):
		self.sock.close();

class TCPClient:
	tcp_rx_size = 1024

	def __init__(self):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	def connect(self, remote_addr, remote_port):
		printl(DCTL, DINFO, "Connecting to %s:%d..."
			% (remote_addr, remote_port))
		try:
			self.sock.connect((remote_addr, remote_port))
			return True
		except:
			printl(DCTL, DERROR, "Connection refused!")
			return False

	def close(self):
		self.sock.close();

	def handle_rx_event(self):
		data = self.sock.recv(self.tcp_rx_size)

		# Detect connection close
		if len(data) == 0:
			self.handle_close_event()
		else:
			self.handle_rx_data(data)

	def handle_rx_data(self, data):
		raise NotImplementedError

	def handle_close_event(self):
		raise NotImplementedError

	def send(self, data):
		self.sock.send(data)
