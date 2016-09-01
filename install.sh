#!/bin/sh
#
# cpanel-whm-mail-outgoing-ips installer
# macklus@debianitas.net
#

echo "Installing cpanel-whm-mail-authentication-check plugin"

mkdir -p /usr/local/cpanel/whostmgr/docroot/cgi/cprocks/cmac
chmod 700 /usr/local/cpanel/whostmgr/docroot/cgi/cprocks
chmod 700 /usr/local/cpanel/whostmgr/docroot/cgi/cprocks/cmac

cp -avf cmac.cgi cmac-check.cgi cmac.conf /usr/local/cpanel/whostmgr/docroot/cgi/cprocks/cmac
chmod -v 755 /usr/local/cpanel/whostmgr/docroot/cgi/cprocks/cmac/cmac.cgi
chmod -v 755 /usr/local/cpanel/whostmgr/docroot/cgi/cprocks/cmac/cmac-check.cgi
chmod -v 644 /usr/local/cpanel/whostmgr/docroot/cgi/cprocks/cmac/cmac.conf

if [ ! -e "/etc/cpanel-whm-mail-authentication-check" ]
then
	touch /etc/cpanel-whm-mail-authentication-check
fi
if [ ! -e "/etc/cpanel-whm-mail-authentication-check-excludes" ]
then
	touch /etc/cpanel-whm-mail-authentication-check-excludes
fi

if [ -e "/usr/local/cpanel/bin/register_appconfig" ]; then
    /usr/local/cpanel/bin/register_appconfig  /usr/local/cpanel/whostmgr/docroot/cgi/cprocks/cmac/cmac.conf
fi

echo "Done."
exit
