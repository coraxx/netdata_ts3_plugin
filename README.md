
# Teamspeak 3 netdata Plugin #

This is a [netdata](https://github.com/firehol/netdata/) plugin that polls active
users and bandwidth from TeamSpeak 3 servers.

![TS3 plugin screenshot](http://semper.space/netdata_ts3/screenshot01.png "Netdata TS3 plugin")

## Installation ##

With your default netdata installation copy the ts3.chart.py script to
`/usr/libexec/netdata/python.d/` and the ts3.conf config file to
`/etc/netdata/python.d/`. The location of these directories may vary depending
on your distribution. Read your given release of netdata for more information.

Edit the config file to set the TeamSpeak Server Query user and password. If not
already set, connect to your TeamSpeak server with the TeamSpeak client and go
to menu 'Extras' -> 'ServerQuery Login' and set a user and password.

Restart netdata to activate the plugin after you have made these changes.

To disable the Teamspeak 3 plugin, edit `/etc/netdata/python.d.conf` and add
`ts3: no`.

## Debugging
switch to netdata user:

`sudo su -s /bin/bash netdata`

Run plugin in debug mode:

`/usr/libexec/netdata/plugins.d/python.d.plugin 1 debug trace ts3`

## Version History ##

- v0.8
    - Fixed SocketService import
    - compatibility fix for netdata 1.10 by @arnowelzel
    - formatting and tweaks by @vennekilde and @catlinman
- v0.7
    - Major readability and formatting changes as well as a compatibility fix for Python 3.6.2
- v0.6
    - Bugfix: Default netdata socket service raised an error when decoding non ASCII characters
- v0.5
    - Added packet loss graph and file transfer bandwidth
- v0.4
    - Added bandwidth graph
- v0.3
    - Cleanup and config implementation (Special thanks to @paulfantom)
- v0.2
    - Rewrote plugin to use Netdata's SocketService
- v0.1
    - Initial release

## License ##

This repository is released under the MIT license. For more information please
refer to [LICENSE](https://github.com/catlinman/netdata_ts3_plugin/blob/master/LICENSE)
