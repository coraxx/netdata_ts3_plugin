#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NetData plugin for active users on TeamSpeak 3 servers.
Please set user and password for your TeamSpeakQuery login.

Copyright (C) 2016  Jan Arnold

	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.

# @Title			: ts3.chart
# @Project			:
# @Description		: NetData plugin for active users on TeamSpeak 3 servers
# @Author			: Jan Arnold
# @Email			: jan.arnold (at) coraxx.net
# @Copyright		: Copyright (C) 2016  Jan Arnold
# @License			: GPLv3
# @Credits			:
# @Maintainer		: Jan Arnold
# @Date				: 2016/08/15
# @Version			: 0.2
# @Status			: stable
# @Usage			: automatically processed by netdata
# @Notes			: With default NetData installation put this file under
#					: /usr/libexec/netdata/python.d/
# @Python_version	: 2.7.11
"""
# ======================================================================================================================
import sys
import os
import re
from base import SocketService

## Plugin settings
update_every = 1
priority = 60000
retries = 10

ORDER = ['users']

CHARTS = {
	'users': {
		'options': [None, 'Users online', 'users', 'TeamSpeak Server', 'ts3.connected_user', 'line'],
		'lines': [
			['connected_users', 'online', 'absolute']
		]}
}


class Service(SocketService):
	def __init__(self, configuration=None, name=None):
		SocketService.__init__(self, configuration=configuration, name=name)

		########################## CUSTOMIZE ME ##########################
		## TeamSpeak Server settings
		self.host = "localhost"  # default
		self.port = 10011  # default
		self.sid = 1  # default. This script can only check one single virtual server atm

		## TS3 Query user and password. If not set already, connect to your TS server
		#  with the TS client and go to the menu 'Extras'->'ServerQuery Login'

		self.user = ""  # <=== ADD LOGIN CREDENTIALS
		self.passwd = ""  # <=== ADD LOGIN CREDENTIALS

		#####################  END OF CUSTOMIZATION ######################

		## Socket settings
		self.unix_socket = None
		self._keep_alive = True
		# self.request = "login {0} {1}\nuse sid={2}\nserverinfo\n".format(self.user, self.passwd, self.sid)
		self.request = "serverinfo\n"

		# Chart
		self.order = ORDER
		self.definitions = CHARTS

		# Reconnect settings
		self.maxReconnects = 5
		self.retryCounter = 0

		self.connected_users = 0

		if self.user == "" or self.passwd == "":
			self.error(
				"Please specify a TeamSpeak Server query user and password inside the ts3.chart.py!",
				"Disable plugin...")
			sys.exit(1)

		## Check once if TS3 is running when host is localhost
		if self.host in ['localhost','127.0.0.1']:
			TS3_running = False
			pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
			for pid in pids:
				try:
					if 'ts3server' in open(os.path.join('/proc', pid, 'cmdline'), 'rb').read():
						TS3_running = True
						break
				except IOError:
					pass
			if TS3_running is False:
				self.error("No TeamSpeak server running. Disabling plugin...")
				sys.exit(1)
			else:
				self.debug("TeamSpeak server process found. Connecting...")

	def _send(self):
		"""
		Send request.
		:return: boolean
		"""
		# Send request if it is needed
		if self.request != "".encode():
			try:
				self._sock.send("login {0} {1}\n".format(self.user, self.passwd).encode())
				self._receive()
				self._sock.send("use sid={0}\n".format(self.sid).encode())
				self._receive()
				self._sock.send(self.request)
			except Exception as e:
				self._disconnect()
				self.error(
					str(e),
					"used configuration: host:", str(self.host),
					"port:", str(self.port),
					"socket:", str(self.unix_socket))
				return False
		return True

	def _get_data(self):
		"""
		Format data received from socket
		:return: dict
		"""
		data = {}
		try:
			raw = self._get_raw_data()
		except (ValueError, AttributeError):
			self.error("no data received")
			return None

		reg = re.compile("virtualserver_clientsonline=(\d*)|virtualserver_queryclientsonline=(\d*)")
		connected_users = reg.findall(raw)
		self.debug(str(connected_users))
		if connected_users == []:
			self.error("Information could not be extacted")
			return None
		try:
			## clients connected - query clients connected
			connected_users = int(connected_users[0][0]) - int(connected_users[1][1])
			data["connected_users"] = connected_users
		except Exception as e:
			self.error(str(e))
			return None

		return data

	def _check_raw_data(self, data):
		if data.endswith("msg=ok\n\r"):
			return True
		else:
			return False
