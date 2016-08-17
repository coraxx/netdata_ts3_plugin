#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NetData plugin for active users on TeamSpeak 3 servers.
Please set user and password for your TeamSpeakQuery login in the ts3.conf.

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
# @Version			: 0.5
# @Status			: stable
# @Usage			: automatically processed by netdata
# @Notes			: With default NetData installation put this file under
#					: /usr/libexec/netdata/python.d/
#					: and the config file under /etc/netdata/python.d/
# @Python_version	: 2.7.11
"""
# ======================================================================================================================
import os
import re
from base import SocketService

## Plugin settings
update_every = 1
priority = 60000
retries = 10

ORDER = ['users','bandwidth_total','bandwidth_filetransfer','packetloss']

CHARTS = {
	'users': {
		'options': [None, 'Users online', 'users', 'Users', 'ts3.connected_user', 'line'],
		'lines': [
			['connected_users', 'online', 'absolute']
		]},
	'bandwidth_total': {
		'options': [None, 'Bandwidth total', 'kb/s', 'Bandwidth', 'ts3.bandwidth_total', 'area'],
		'lines': [
			['bandwidth_total_received', 'received', 'absolute', 1, 1000],
			['bandwidth_total_sent', 'sent', 'absolute', -1, 1000]
		]},
	'bandwidth_filetransfer': {
		'options': [None, 'Bandwidth filetransfer', 'kb/s', 'Bandwidth', 'ts3.bandwidth_filetransfer', 'area'],
		'lines': [
			['bandwidth_filetransfer_received', 'received', 'absolute', 1, 1000],
			['bandwidth_filetransfer_sent', 'sent', 'absolute', -1, 1000]
		]},
	'packetloss': {
		'options': [None, 'Average data packet loss', 'packets', 'Packet Loss', 'ts3.packetloss', 'line'],
		'lines': [
			['packetloss_speech', 'speech', 'absolute'],
			['packetloss_keepalive', 'keepalive', 'absolute'],
			['packetloss_control', 'control', 'absolute'],
			['packetloss_total', 'total', 'absolute']
		]}
}


class Service(SocketService):
	def __init__(self, configuration=None, name=None):
		SocketService.__init__(self, configuration=configuration, name=name)

		## TeamSpeak Server settings
		self.host = "localhost"
		self.port = "10011"

		## Socket settings
		self.unix_socket = None
		self._keep_alive = True
		self.request = "serverinfo\n"

		# Chart
		self.order = ORDER
		self.definitions = CHARTS

	def check(self):
		"""
		Parse configuration and check if local Teamspeak server is running
		:return: boolean
		"""
		self._parse_config()

		try:
			self.user = self.configuration['user']
			if self.user == '': raise KeyError
		except KeyError:
			self.error(
				"Please specify a TeamSpeak Server query user inside the ts3.conf!", "Disabling plugin...")
			return False
		try:
			self.passwd = self.configuration['pass']
			if self.passwd == '': raise KeyError
		except KeyError:
			self.error(
				"Please specify a TeamSpeak Server query password inside the ts3.conf!", "Disabling plugin...")
			return False
		try:
			self.sid = self.configuration['sid']
		except KeyError:
			self.sid = 1
			self.debug("No sid specified. Using: '{0}'".format(self.sid))

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
				self.error("No local TeamSpeak server running. Disabling plugin...")
				return False
			else:
				self.debug("TeamSpeak server process found. Connecting...")

		return True

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

		reg = re.compile(
			"virtualserver_clientsonline=(\d*)|" +
			"virtualserver_queryclientsonline=(\d*)|" +
			"connection_bandwidth_sent_last_second_total=(\d*)|" +
			"connection_bandwidth_received_last_second_total=(\d*)|" +
			"connection_filetransfer_bandwidth_sent=(\d*)|" +
			"connection_filetransfer_bandwidth_received=(\d*)|" +
			"virtualserver_total_packetloss_speech=(\d*)|" +
			"virtualserver_total_packetloss_keepalive=(\d*)|" +
			"virtualserver_total_packetloss_control=(\d*)|" +
			"virtualserver_total_packetloss_total=(\d*)"
			)
		regex = reg.findall(raw)
		self.debug(str(regex))
		if regex == []:
			self.error("Information could not be extracted")
			return None
		try:
			## clients connected - query clients connected
			connected_users = int(regex[0][0]) - int(regex[1][1])
			data["connected_users"] = connected_users
			## bandwidth info from server in bytes/s
			data["bandwidth_total_sent"] = int(regex[8][2])
			data["bandwidth_total_received"] = int(regex[9][3])
			data["bandwidth_filetransfer_sent"] = int(regex[6][4])
			data["bandwidth_filetransfer_received"] = int(regex[7][5])
			## The average packet loss
			data["packetloss_speech"] = float(regex[2][6])
			data["packetloss_keepalive"] = float(regex[3][7])
			data["packetloss_control"] = float(regex[4][8])
			data["packetloss_total"] = float(regex[5][9])
		except Exception as e:
			self.error(str(e))
			return None

		return data

	def _check_raw_data(self, data):
		if data.endswith("msg=ok\n\r"):
			return True
		else:
			return False
