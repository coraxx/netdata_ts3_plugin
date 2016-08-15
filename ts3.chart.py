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
# @Version			: 0.1
# @Status			: stable
# @Usage			: automatically processed by netdata
# @Notes			: With default NetData installation put this file under
#					: /usr/libexec/netdata/python.d/
# @Python_version	: 2.7.11
"""
# ======================================================================================================================
from __future__ import print_function
import sys
import os
import re
import time
import telnetlib
from base import SimpleService

## Plugin settings
update_every = 10
priority = 60000
retries = 10


class Service(SimpleService):
	def __init__(self, configuration=None, name=None):
		SimpleService.__init__(self, configuration=configuration, name=name)
		self.writeToLog = True
		# Reconnect settings
		self.maxReconnects = 5
		self.retryCounter = 0
		## Timeout for Telnet commands in seconds
		self.timeout = 1

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

		if self.user == "" or self.passwd == "":
			if self.writeToLog: print(
				"ts3.chart.py [FAIL] Please specify a TeamSpeak Server query user and password inside the ts3.chart.py!",
				file=sys.stderr)
			sys.exit(1)

		## Check if TS3 is running when host is localhost
		if self.host in ['localhost','127.0.0.1']:
			TS3_running = False
			pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
			for pid in pids:
				try:
					if 'ts3server_linux_x86' in open(os.path.join('/proc', pid, 'cmdline'), 'rb').read():
						TS3_running = True
						break
				except IOError:
					pass
			if TS3_running is False:
				if self.writeToLog: print(
					"ts3.chart.py [FAIL] No TeamSpeak server running. Disable plugin...",
					file=sys.stderr)
				sys.exit(1)
			else:
				if self.writeToLog: print(
					"ts3.chart.py [Info] TeamSpeak server process found. Connecting...",
					file=sys.stderr)

		self.users_connected = None

		## Connect to server
		ret = self.connectToServer()
		if ret == 1:
			if self.writeToLog: print(
				"ts3.chart.py [FAIL] Connection to TeamSpeak server failed. Disable plugin...",
				file=sys.stderr)
			sys.exit(1)
		else:
			if self.writeToLog: print("ts3.chart.py [Info] Connected to TeamSpeak server: sid={0} @ {1}:{2}".format(
				self.sid, self.host, self.port), file=sys.stderr)

	def check(self):
		return True

	def create(self):
		self.chart(
			'ts3.users_connected', '', 'User on TeamSpeak Server', 'users',
			'users', 'TeamSpeak Server', 'line', priority, update_every)
		self.dimension('online')
		self.commit()
		return True

	def update(self, interval):
		self.begin("ts3.users_connected", interval)
		self.checkConnection()
		users_connected = self.getTS3activeClients()
		self.set("online", users_connected)
		self.end()
		self.commit()
		return True

	def connectToServer(self):
		self.tn = telnetlib.Telnet(self.host, self.port, self.timeout)
		index, _, msg = self.tn.expect(["information on a specific command"], self.timeout)
		if index == -1:
			if self.writeToLog: print(
				'ts3.chart.py [FAIL] Connection problems. Cannot connect to server',
				file=sys.stderr)
			if self.writeToLog: print(msg, file=sys.stderr)
			return 1
		ret = self.getTnResponse("use sid={0}".format(self.sid))
		if ret is not None:
			ret = self.getTnResponse("login {0} {1}".format(self.user, self.passwd))
			if ret is None:
				if self.writeToLog: print('ts3.chart.py [FAIL] Login unsuccessful', file=sys.stderr)
				return 1
			else:
				return 0
		else:
			if self.writeToLog: print(
				'ts3.chart.py [FAIL] Virtual server with id', self.sid, 'could not be selected.',
				file=sys.stderr)
			return 1

	def getTS3activeClients(self):
		ret = self.getTnResponse("serverinfo")
		if ret is not None:
			reg = re.compile("virtualserver_clientsonline=(\d*)|virtualserver_queryclientsonline=(\d*)")
			users_connected = reg.findall(ret)
			try:
				## clients connected - query clients connected
				users_connected = int(users_connected[0][0]) - int(users_connected[1][1])
				return users_connected
			except Exception as e:
				if self.writeToLog: print(e, file=sys.stderr)
				return -1
		else:
			if self.writeToLog: print('ts3.chart.py [FAIL] Could not retrieve serverinfo', file=sys.stderr)
			return -1

	def checkConnection(self):
		try:
			self.tn.read_very_eager()
			self.tn.write('helo\n')
			index, _, _ = self.tn.expect(['error id=256 msg=command'], self.timeout)
			if index != 0:
				raise Exception('Unexpected answer from server')
			self.tn.read_very_eager()
			self.retryCounter = 0
		except:
			while self.retryCounter < self.maxReconnects:
				ret = self.connectToServer()
				if ret == 1:
					self.retryCounter += 1
				else:
					break
				time.sleep(1)
			if ret == 1:
				if self.writeToLog: print(
					'ts3.chart.py [FAIL] Connection to TeamSpeak server failed. Disable plugin...',
					file=sys.stderr)
				sys.exit(1)

	def getTnResponse(self,command):
		self.tn.write(command+"\n")
		index, _, msg = self.tn.expect(["error id=[0] msg=ok","error id=([1-9]|[0-9]{2,3}) msg=.*"],1)
		if index == 0:
			return msg
		else:
			if self.writeToLog: print(
				"ts3.chart.py [FAIL]",
				"="*15, "ERROR", "="*15 + "\n",
				msg + "\n",
				"="*15, "ERROR", "="*15 + "\n", file=sys.stderr)
			return None
