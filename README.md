# README #

[NetData](https://github.com/firehol/netdata/) plugin that polls active users and bandwidth from TeamSpeak 3 servers.

![TS3 plugin screenshot](http://semper.space/netdata_ts3/screenshot01.png "Netdata TS3 plugin")

### Installation ###

With default NetData installation copy the ts3.chart.py script to `/usr/libexec/netdata/python.d/` and the ts3.conf config file to `/etc/netdata/python.d/`.

Edit the config file to set the TeamSpeak Server Query user and password.
If not already set, connect to your TeamSpeak server with the TeamSpeak client and go to menu 'Extras' -> 'ServerQuery Login' and set a user and password.

Then restart NetData to activate the plugin.

To disable the ts3 plugin, edit `/etc/netdata/python.d.conf` and add `ts3: no`.


### License ###

The MIT License (MIT)
Copyright (c) 2016 Jan Arnold

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


### Version ###

v0.5 - added packet loss graph and file transfer bandwidth

v0.4 - added bandwidth graph

v0.3 - cleanup and config implementation - thx for the help @paulfantom

v0.2 - rewrote plugin to use Netdata's SocketService

v0.1 - initial release



### Who do I talk to? ###

* Repo owner or admin
* Other community or team contact
