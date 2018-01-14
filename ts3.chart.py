#!/usr/bin/env python

"""
NetData plugin for active users on TeamSpeak 3 servers.
Please set user and password for your TeamSpeakQuery login in the 'ts3.conf'.

The MIT License (MIT)
Copyright (c) 2016-2017 Jan Arnold

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# @Title            : ts3.chart
# @Description      : NetData plugin for active users on TeamSpeak 3 servers
# @Author           : Jan Arnold
# @Email            : jan.arnold (at) coraxx.net
# @Copyright        : Copyright (C) 2016-2017 Jan Arnold
# @License          : MIT
# @Maintainer       : Jan Arnold
# @Date             : 2017/09/12
# @Version          : 0.7
# @Status           : stable
# @Usage            : Automatically processed by netdata
# @Notes            : With default NetData installation put this file under
#                   : /usr/libexec/netdata/python.d/ and the config file under
#                   : /etc/netdata/python.d/
# @Python_version   : 3.6.2
"""

import os
import re
import select

from base import SocketService

# Basic plugin settings for netdata.
update_every = 1
priority = 60000
retries = 10

ORDER = ['users', 'bandwidth_total', 'bandwidth_filetransfer', 'packetloss']

CHARTS = {
    'users': {
        'options': [None, 'Users online', 'users', 'Users', 'ts3.connected_user', 'line'],
        'lines': [
            ['connected_users', 'online', 'absolute']
        ]
    },
    'bandwidth_total': {
        'options': [None, 'Bandwidth total', 'kb/s', 'Bandwidth', 'ts3.bandwidth_total', 'area'],
        'lines': [
            ['bandwidth_total_received', 'received', 'absolute', 1, 1000],
            ['bandwidth_total_sent', 'sent', 'absolute', -1, 1000]
        ]
    },
    'bandwidth_filetransfer': {
        'options': [None, 'Bandwidth filetransfer', 'kb/s', 'Bandwidth', 'ts3.bandwidth_filetransfer', 'area'],
        'lines': [
            ['bandwidth_filetransfer_received', 'received', 'absolute', 1, 1000],
            ['bandwidth_filetransfer_sent', 'sent', 'absolute', -1, 1000]
        ]
    },
    'packetloss': {
        'options': [None, 'Average data packet loss', 'packets loss %', 'Packet Loss', 'ts3.packetloss', 'line'],
        'lines': [
            ['packetloss_speech', 'speech', 'absolute', 1, 1000],
            ['packetloss_keepalive', 'keepalive', 'absolute', 1, 1000],
            ['packetloss_control', 'control', 'absolute', 1, 1000],
            ['packetloss_total', 'total', 'absolute', 1, 1000],
        ]
    }
}


class Service(SocketService):
    def __init__(self, configuration=None, name=None):
        SocketService.__init__(self, configuration=configuration, name=name)

        # Default TeamSpeak Server connection settings.
        self.host = "localhost"
        self.port = "10011"

        # Connection socket settings.
        self.unix_socket = None
        self._keep_alive = True
        self.request = "serverinfo\n"

        # Chart information handled by netdata.
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

            if self.user == '':
                raise KeyError

        except KeyError:
            self.error(
                "Please specify a TeamSpeak Server query user inside the ts3.conf!", "Disabling plugin...")

            return False

        try:
            self.passwd = self.configuration['pass']

            if self.passwd == '':
                raise KeyError

        except KeyError:
            self.error(
                "Please specify a TeamSpeak Server query password inside the ts3.conf!", "Disabling plugin...")

            return False

        try:
            self.sid = self.configuration['sid']

        except KeyError:
            self.sid = 1
            self.debug("No sid specified. Using: '{0}'".format(self.sid))

        # Check once if TS3 is running when host is localhost.
        if self.host in ['localhost', '127.0.0.1']:
            TS3_running = False

            pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]

            for pid in pids:
                try:
                    if b'ts3server' in open(os.path.join('/proc', pid, 'cmdline').encode(), 'rb').read():
                        TS3_running = True

                        break

                except IOError as e:
                    self.error(e)

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
                self._sock.send(b"whoami\n")
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
                    "socket:", str(self.unix_socket)
                )

                return False

        return True

    def _receive(self):
        """
        Receive data from socket
        :return: str
        """
        data = ""

        while True:
            try:
                ready_to_read, _, in_error = select.select([self._sock], [], [], 5)

            except Exception as e:
                self.debug("SELECT", str(e))
                self._disconnect()

                break

            if len(ready_to_read) > 0:
                buf = self._sock.recv(4096)

                if len(buf) == 0 or buf is None:  # handle server disconnect
                    break

                self.debug(str(buf))
                data += buf.decode("utf-8")

                if self._check_raw_data(data):
                    break
            else:
                self.error("Socket timed out.")
                self._disconnect()

                break

        return data

    def _get_data(self):
        """
        Format data received from socket
        :return: dict
        """
        data = {}

        try:
            raw = self._get_raw_data()

        except (ValueError, AttributeError):
            self.error("No data received.")

            return None

        reg = re.compile(
            "virtualserver_clientsonline=(\d*)|" +
            "virtualserver_queryclientsonline=(\d*)|" +
            "connection_bandwidth_sent_last_second_total=(\d*)|" +
            "connection_bandwidth_received_last_second_total=(\d*)|" +
            "connection_filetransfer_bandwidth_sent=(\d*)|" +
            "connection_filetransfer_bandwidth_received=(\d*)|" +
            "virtualserver_total_packetloss_speech=(\d+\.\d+)|" +
            "virtualserver_total_packetloss_keepalive=(\d+\.\d+)|" +
            "virtualserver_total_packetloss_control=(\d+\.\d+)|" +
            "virtualserver_total_packetloss_total=(\d+\.\d+)"
        )

        regex = reg.findall(raw)

        self.debug(str(regex))

        if regex == []:
            self.error("Information could not be extracted")
            return None

        try:
            # Clients and query clients connected.
            connected_users = int(regex[0][0]) - int(regex[1][1])
            data["connected_users"] = connected_users

            # Bandwidth info from server in bytes/s.
            data["bandwidth_total_sent"] = int(regex[8][2])
            data["bandwidth_total_received"] = int(regex[9][3])
            data["bandwidth_filetransfer_sent"] = int(regex[6][4])
            data["bandwidth_filetransfer_received"] = int(regex[7][5])

            # The average packet loss.
            data["packetloss_speech"] = float(regex[2][6]) * 100000
            data["packetloss_keepalive"] = float(regex[3][7]) * 100000
            data["packetloss_control"] = float(regex[4][8]) * 100000
            data["packetloss_total"] = float(regex[5][9]) * 100000

        except Exception as e:
            self.error(str(e))

            return None

        return data

    def _check_raw_data(self, data):
        if data.endswith("msg=ok\n\r"):
            return True

        elif "virtualserver_status=unknown" in data:
            # Perform login
            self._sock.send("login {0} {1}\n".format(self.user, self.passwd).encode())
            self._receive()

        else:
            return False
