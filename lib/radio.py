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

import pmt
import time
import grgsm
import osmosdr

from math import pi
from log import *

from gnuradio.eng_option import eng_option
from gnuradio import eng_notation
from gnuradio.filter import firdes
from gnuradio import blocks
from gnuradio import gr

class RadioInterface(gr.top_block):
	fc = 935e6 # ARFCN 0 (initial setup)
	shiftoff = 400e3

	def __init__(self, phy_device_args, phy_subdev_spec,
				phy_sample_rate, phy_gain, phy_ppm, sock_port):
		printl(DGSM, DINFO, "Init Radio interface")

		self.device_args = phy_device_args
		self.subdev_spec = phy_subdev_spec
		self.samp_rate = phy_sample_rate
		self.gain = phy_gain
		self.ppm = phy_ppm

		gr.top_block.__init__(self, "GR-GSM TMSI sniffer")
		shift_fc = self.fc - self.shiftoff

		##################################################
		# PHY Definition
		##################################################
		self.phy = osmosdr.source(
			args = "numchan=%d %s" % (1, self.device_args))

		self.phy.set_bandwidth(250e3 + abs(self.shiftoff), 0)
		self.phy.set_center_freq(shift_fc, 0)
		self.phy.set_sample_rate(self.samp_rate)
		self.phy.set_freq_corr(self.ppm, 0)
		self.phy.set_iq_balance_mode(2, 0)
		self.phy.set_dc_offset_mode(2, 0)
		self.phy.set_gain_mode(False, 0)
		self.phy.set_gain(self.gain, 0)
		self.phy.set_if_gain(20, 0)
		self.phy.set_bb_gain(20, 0)
		self.phy.set_antenna("", 0)

		##################################################
		# GR-GSM Magic
		##################################################
		self.gsm_bcch_ccch_demapper = grgsm.gsm_bcch_ccch_demapper(
			timeslot_nr = 0)

		self.blocks_rotator = blocks.rotator_cc(
			-2 * pi * self.shiftoff / self.samp_rate)

		self.gsm_input = grgsm.gsm_input(
			ppm = self.ppm, osr = 4, fc = self.fc,
			samp_rate_in = self.samp_rate)

		self.socket_pdu = blocks.socket_pdu(
			"UDP_CLIENT", "127.0.0.1", str(sock_port), 10000, False)

		self.gsm_clck_ctrl = grgsm.clock_offset_control(
			shift_fc, self.samp_rate, osr = 4)

		self.gsm_ccch_decoder = grgsm.control_channels_decoder()
		self.gsm_receiver = grgsm.receiver(4, ([0]), ([]))

		##################################################
		# Connections
		##################################################
		self.connect((self.phy, 0), (self.blocks_rotator, 0))
		self.connect((self.blocks_rotator, 0), (self.gsm_input, 0))
		self.connect((self.gsm_input, 0), (self.gsm_receiver, 0))

		self.msg_connect((self.gsm_receiver, 'C0'),
			(self.gsm_bcch_ccch_demapper, 'bursts'))

		self.msg_connect((self.gsm_receiver, 'measurements'),
			(self.gsm_clck_ctrl, 'measurements'))

		self.msg_connect((self.gsm_clck_ctrl, 'ctrl'),
			(self.gsm_input, 'ctrl_in'))

		self.msg_connect((self.gsm_bcch_ccch_demapper, 'bursts'),
			(self.gsm_ccch_decoder, 'bursts'))

		self.msg_connect((self.gsm_ccch_decoder, 'msgs'),
			(self.socket_pdu, 'pdus'))

	def shutdown(self):
		printl(DGSM, DINFO, "Shutdown Radio interface")
		self.stop()
		self.wait()

	def get_args(self):
		return self.args

	def set_args(self, args):
		self.args = args

	def get_fc(self):
		return self.fc

	def set_fc(self, fc):
		self.phy.set_center_freq(fc - self.shiftoff, 0)
		self.gsm_input.set_fc(fc)
		self.fc_set = True
		self.fc = fc

	def get_gain(self):
		return self.gain

	def set_gain(self, gain):
		self.phy.set_gain(gain, 0)
		self.gain = gain

	def get_ppm(self):
		return self.ppm

	def set_ppm(self, ppm):
		self.rtlsdr_source_0.set_freq_corr(ppm, 0)
		self.ppm = ppm

	def get_samp_rate(self):
		return self.samp_rate

	def set_samp_rate(self, samp_rate):
		self.blocks_rotator.set_phase_inc(
			-2 * pi * self.shiftoff / samp_rate)

		self.gsm_input.set_samp_rate_in(samp_rate)
		self.phy.set_sample_rate(samp_rate)
		self.samp_rate = samp_rate

	def get_shiftoff(self):
		return self.shiftoff

	def set_shiftoff(self, shiftoff):
		self.blocks_rotator.set_phase_inc(
			-2 * pi * shiftoff / self.samp_rate)

		self.phy.set_bandwidth(250e3 + abs(shiftoff), 0)
		self.phy.set_center_freq(self.fc - shiftoff, 0)
		self.shiftoff = shiftoff
