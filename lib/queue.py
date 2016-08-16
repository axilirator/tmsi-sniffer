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

class Queue:
	def __init__(self, a = False, b = False):
		self.items = []

		if a != False and b != False:
			for item in a.items:
				if item in b.items:
					self.add(item)

	def add(self, item):
		self.items.append(item)

	def find(self, item):
		return item in self.items
