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

DAPP = "\033[1;35m" # Application messages
DGSM = "\033[1;33m" # Radio interface messages
DCTL = "\033[1;37m" # Control interface messages
DMII = "\033[1;34m" # TMSI in IDLE mode
DMIR = "\033[1;31m" # TMSI in RECORDING mode
ENDC = '\033[0m'    # Default style

DINFO = "[i] "
DERROR = "[!] "
DPAGING = "[+] "

def printl(cat, level, msg):
	print cat + level + msg + ENDC
