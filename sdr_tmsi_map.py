#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# GR-GSM based TMSI sniffer
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

import sys
import getopt
import signal

from lib.network import *
from lib.radio import *
from lib.queue import *
from lib.log import *

class TMSIManager(UDPServer):
	def __init__(self, local_port):
		printl(DMII, DINFO, "Init TMSI Manager")
		UDPServer.__init__(self, local_port)
		self.flush()

	def shutdown(self):
		printl(DMII, DINFO, "Shutdown TMSI Manager")
		self.close()

	def handle_rx_data(self, data):
		# Convert to a byte array
		data = bytearray(data)
		# Cut GSMTAP header
		l3 = data[16:]

		# We need Paging Requests only
		if l3[1] == 0x06:
			if l3[2] == 0x21:
				self.handle_p1(l3)
			elif l3[2] == 0x22:
				self.handle_p2(l3)
			elif l3[2] == 0x24:
				self.handle_p3(l3)

	def print_tmsi(self, tmsi):
		msg = "Paging Request to 0x"
		for x in tmsi:
			msg += "{:02x}".format(x)

		cat = DMIR if self.recording else DMII
		printl(cat, DPAGING, msg)

	def handle_tmsi(self, tmsi):
		# Yes, print this one first
		self.print_tmsi(tmsi)

		# Determine our current state
		if self.recording:
			# Add every possible TMSI
			self.record.add(tmsi)
		else:
			# Filter outsider TMSIs
			for record in self.records:
				record.remove(tmsi)

	def handle_p1(self, l3):
		# This can contain two MIs
		mi_type = l3[5] & 0x07
		mi_found = False
		msg_len = l3[0]

		# FIXME: What about IMEI and IMEISV???
		if mi_type == 0x04: # TMSI
			self.handle_tmsi(l3[6:10])
			next_mi_index = 10
			mi_found = True
		elif mi_type == 0x01: # IMSI
			next_mi_index = 13
			mi_found = True

		# Check if there is an additional MI
		if mi_found:
			if next_mi_index < (msg_len + 1) and l3[next_mi_index] == 0x17:
				# Extract MI type and length
				mi_type = l3[next_mi_index + 2] & 0x07
				mi2_len = l3[next_mi_index + 1]

				# We only need TMSI
				if mi_type == 0x04:
					a = next_mi_index + 3
					b = next_mi_index + 7
					self.handle_tmsi(l3[a:b])

	def handle_p2(self, l3):
		# This can contain two TMSIs and (optionally) one more MI
		self.handle_tmsi(l3[4:8])
		self.handle_tmsi(l3[8:12])
		
		# Check for optional TMSI
		if l3[14] & 0x07 == 0x04:
			self.handle_tmsi(l3[15:19])

	def handle_p3(self, l3):
		# This one contains four TMSIs
		self.handle_tmsi(l3[4:8])
		self.handle_tmsi(l3[8:12])
		self.handle_tmsi(l3[12:16])
		self.handle_tmsi(l3[16:20])

	def start(self):
		self.record = Queue()
		self.recording = True

	def stop(self):
		self.record.unique() # We don't need any duplicates
		self.records.append(self.record)
		self.recording = False

	def flush(self):
		self.records = []
		self.record = Queue()
		self.recording = False

	def cross(self):
		if len(self.records) > 1:
			result = self.records[0]

			for recod in self.records[1:]:
				result = Queue(result, recod)

			return result
		else:
			return []

class ControlInterface(TCPClient):
	def __init__(self, app):
		printl(DCTL, DINFO, "Init Control interface")
		TCPClient.__init__(self)
		self.app = app

	def shutdown(self):
		printl(DCTL, DINFO, "Shutdown Control interface")
		self.close()

	def verify_req(self, data):
		# Verify command signature
		return data.startswith("CMD")

	def prepare_req(self, data):
		# Strip signature, paddings and \0
		request = data[4:].strip().strip("\0")
		# Split into a command and arguments
		request = request.split(" ")
		# Now we have something like ["RXTUNE", "941600"]
		return request

	def verify_cmd(self, request, cmd, argc):
		# If requested command matches and has enough arguments
		if request[0] == cmd and len(request) - 1 == argc:
			# Check if all arguments are numeric
			for v in request[1:]:
				if not v.isdigit():
					return False

			# Ok, everything is fine
			return True
		else:
			return False

	def parse_cmd(self, request):
		if self.verify_cmd(request, "RXTUNE", 1):
			printl(DCTL, DINFO, "Recv RXTUNE cmd")
			freq = int(request[1]) * 1000

			printl(DCTL, DINFO, "Switching to %d Hz" % freq)
			self.app.radio.set_fc(freq)

		elif self.verify_cmd(request, "START", 0):
			printl(DCTL, DINFO, "Recv START cmd")
			self.app.tmsi_mgr.start()

		elif self.verify_cmd(request, "STOP", 0):
			printl(DCTL, DINFO, "Recv STOP cmd")
			self.app.tmsi_mgr.stop()

		elif self.verify_cmd(request, "CROSS", 0):
			printl(DCTL, DINFO, "Recv CROSS cmd")

			result = self.app.tmsi_mgr.cross()
			response = "CROSS Result:\n"
			for tmsi in result.items:
				response += "0x"
				for x in tmsi:
					response += "{:02x}".format(x)
				response += "\n"

			self.send(response)

		elif self.verify_cmd(request, "FLUSH", 0):
			printl(DCTL, DINFO, "Recv FLUSH cmd")
			self.app.tmsi_mgr.flush()

		# Wrong command
		else:
			printl(DCTL, DERROR, "Wrong command on CTRL interface")

	def handle_rx_data(self, data):
		if self.verify_req(data):
			request = self.prepare_req(data)
			self.parse_cmd(request)
		else:
			printl(DCTL, DERROR, "Wrong data on CTRL interface")

	def handle_close_event(self):
		printl(DCTL, DERROR, "Disconnected from server")
		self.app.quit = True

class Application:
	# Application variables
	master_addr = "127.0.0.1"
	master_port = 8888
	local_port = 4729
	quit = False

	# PHY specific variables
	phy_sample_rate = 2000000
	phy_subdev_spec = ""
	phy_device_args = ""
	phy_gain = 30
	phy_ppm = 0

	def __init__(self):
		self.print_copyright()
		self.parse_argv()

		# Set up signal handlers
		signal.signal(signal.SIGINT, self.sig_handler)

	def run(self):
		# Init Control interface
		self.ctrl = ControlInterface(self)
		if not self.ctrl.connect(self.master_addr, self.master_port):
			sys.exit(1)

		# Init Radio interface
		self.radio = RadioInterface(
			self.phy_device_args, self.phy_subdev_spec,
			self.phy_sample_rate, self.phy_gain,
			self.phy_ppm, self.local_port)
		self.radio.start()

		# Init TMSI manager
		self.tmsi_mgr = TMSIManager(self.local_port)

		# Enter main loop
		printl(DAPP, DINFO, "Init complete, entering main loop...")
		while True:
			# Check if it's time to quit
			if self.quit:
				self.shutdown()
				break

			# Keep working
			self.loop()

	def loop(self):
		# Blocking select
		r_event, w_event, x_event = select.select(
			[self.ctrl.sock, self.tmsi_mgr.sock], [], [])

		# Check for incoming GSM data
		if self.tmsi_mgr.sock in r_event:
			self.tmsi_mgr.handle_rx_event()

		# Check for incoming CTRL commands
		if self.ctrl.sock in r_event:
			self.ctrl.handle_rx_event()

	def shutdown(self):
		printl(DAPP, DINFO, "Shutting down...")
		self.ctrl.shutdown()
		self.radio.shutdown()
		self.tmsi_mgr.shutdown()

	def print_copyright(self):
		s = "Copyright (C) 2016 by Vadim Yanitskiy <axilirator@gmail.com>\n" \
			"License GPLv2+: GNU GPL version 2 or later <http://gnu.org/licenses/gpl.html>\n" \
			"This is free software: you are free to change and redistribute it.\n" \
			"There is NO WARRANTY, to the extent permitted by law.\n"

		print s

	def print_help(self):
		s  = " Usage: " + sys.argv[0] + " [options]\n\n" \
			 " Some help...\n" \
			 "  -h --help         this text\n" \
			 "  -w --write        Write logs into a file\n\n"

		# TRX specific
		s += " Master server specific\n" \
			 "  -i --master-addr  Set IP address of master server\n" \
			 "  -p --master-port  Set port number (default 8888)\n\n"

		# PHY specific
		s += " Radio interface specific\n" \
			 "  -l --local-port   Change a local port (default 8899)\n" \
			 "  -a --device-args  Set device arguments\n" \
			 "  -s --sample-rate  Set PHY sample rate (default 2000000)\n" \
			 "  -S --subdev-spec  Set PHY sub-device specification\n" \
			 "  -g --gain         Set PHY gain (default 30)\n" \
			 "     --ppm          Set PHY frequency correction (default 0)\n"

		print s

	def parse_argv(self):
		try:
			opts, args = getopt.getopt(sys.argv[1:],
				"w:i:p:l:a:s:S:g:h",
				["help", "arfcn=", "gain=", "ppm=", "write=",
				"master-addr=", "master-port=", "local-port=",
				"device-args=", "sample-rate=", "subdev-spec="])
		except getopt.GetoptError as err:
			# Print help and exit
			self.print_help()
			print "[!] " + str(err)
			sys.exit(2)

		for o, v in opts:
			if o in ("-h", "--help"):
				self.print_help()
				sys.exit(2)
			elif o in ("-w", "--write"):
				self.master_addr = v

			# Master interface specific
			elif o in ("-i", "--master-addr"):
				self.master_addr = v
			elif o in ("-p", "--master-port"):
				if int(v) >= 0 and int(v) <= 65535:
					self.master_port = int(v)
				else:
					print "[!] Port number should be in range [0-65536]"
					sys.exit(2)

			# PHY specific
			elif o in ("-a", "--device-args"):
				self.phy_device_args = v
			elif o in ("-g", "--gain"):
				self.phy_gain = int(v)
			elif o in ("-S", "--subdev-spec"):
				self.phy_subdev_spec = v
			elif o in ("-s", "--sample-rate"):
				self.phy_sample_rate = int(v)
			elif o in ("--ppm"):
				self.phy_ppm = int(v)
			elif o in ("-l", "--local-port"):
				if int(v) >= 0 and int(v) <= 65535:
					self.local_port = int(v)
				else:
					print "[!] Port number should be in range [0-65536]"
					sys.exit(2)

	def sig_handler(self, signum, frame):
		print "Signal %d received" % signum
		if signum is signal.SIGINT:
			self.shutdown()
			sys.exit(0)

if __name__ == '__main__':
	Application().run()
