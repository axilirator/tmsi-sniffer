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

import os
import sys
import getopt
import signal

from lib.network import *
from lib.log import *

class CommandLine:
	def handle_rx_event(self):
		cmd = sys.stdin.readline()
		self.handle_cmd(cmd)

	def write(self, data):
		sys.stdout.write(data)
		sys.stdout.flush()

	def print_help(self):
		self.write("\n")
		self.write("  Control interface help\n")
		self.write("  ======================\n\n")
		self.write("  help      this text\n")
		self.write("  clear     clear screen\n")
		self.write("  exit      shutdown server\n")
		self.write("\n")
		self.write("  rxtune    tunes slaves to a given frequency in kHz\n")
		self.write("  paging    TMSI mapping\n")
		self.write("  |  start  start recording\n")
		self.write("  |  stop   stop recording\n")
		self.write("  |  cross  show results\n")
		self.write("  |  flush  reset all recordings\n")
		self.write("\n")

	def print_unknown(self):
		self.write("Unknown command, see help.\n")

	def print_prompt(self):
		self.write("CTRL# ")

	def handle_cmd(self, request):
		# Strip spaces and \0
		request = request.strip().strip("\0")
		# Split into a command and arguments
		request = request.split(" ")
		argv = request[1:]
		argc = len(argv)
		cmd = request[0]

		# Application specific
		if cmd == "exit":
			app.shutdown()
		elif cmd == "help":
			self.print_help()
		elif cmd == "clear":
			os.system("clear")

		# Server specific
		elif cmd == "rxtune" and argc == 1:
			app.server.broadcast("CMD RXTUNE %s\n" % argv[0])
		elif cmd == "paging":
			if argc == 1:
				subcmd = argv[0]
				if subcmd == "start":
					app.server.broadcast("CMD START\n")
				elif subcmd == "stop":
					app.server.broadcast("CMD STOP\n")
				elif subcmd == "cross":
					app.server.broadcast("CMD CROSS\n")
				elif subcmd == "flush":
					app.server.broadcast("CMD FLUSH\n")

		# Unknown command
		elif cmd != "":
			self.print_unknown()

class Server(TCPServer):
	def __init__(self):
		TCPServer.__init__(self)		

	def handle_close_event(self):
		printl(DCTL, DINFO, "A slave node disconnected")

	def handle_rx_data(self, data):
		printl(DCTL, DINFO, "Some slave says:")
		app.ctrl.write(data)

class Application:
	# Application variables
	listen_port = 8888

	def __init__(self):
		self.print_copyright()
		self.parse_argv()

		# Set up signal handlers
		signal.signal(signal.SIGINT, self.sig_handler)

	def run(self):
		self.ctrl = CommandLine()
		self.server = Server()
		self.server.listen(self.listen_port)

		printl(DAPP, DINFO, "Init complete")
		self.ctrl.print_help()

		# Enter main loop
		while True:
			# Keep working
			self.loop()

	def loop(self):
		# Provide prompt
		# TODO: How to save a previous command?
		self.ctrl.print_prompt()

		# Blocking select
		r_list = [sys.stdin, self.server.sock] + self.server.connections
		r_event, w_event, x_event = select.select(r_list, [], [])

		# Check for incoming CTRL commands
		if sys.stdin in r_event:
			self.ctrl.handle_rx_event()

		# Check for incoming data
		elif self.server.sock in r_event:
			self.server.accept()

		# Maybe something from slaves?
		else:
			self.server.handle_rx_event(r_event)

	def shutdown(self):
		printl(DAPP, DINFO, "Shutting down...")
		self.server.close()
		sys.exit(0)

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
			 "  -p --port         Specify a port to listen (default 8888)\n"

		print s

	def parse_argv(self):
		try:
			opts, args = getopt.getopt(sys.argv[1:],
				"p:h", ["help", "port="])
		except getopt.GetoptError as err:
			# Print help and exit
			self.print_help()
			print "[!] " + str(err)
			sys.exit(2)

		for o, v in opts:
			if o in ("-h", "--help"):
				self.print_help()
				sys.exit(2)
			elif o in ("-p", "--port"):
				if int(v) >= 0 and int(v) <= 65535:
					self.listen_port = int(v)
				else:
					print "[!] Port number should be in range [0-65536]"
					sys.exit(2)

	def sig_handler(self, signum, frame):
		print "Signal %d received" % signum
		if signum is signal.SIGINT:
			self.shutdown()

if __name__ == '__main__':
	app = Application()
	app.run()
