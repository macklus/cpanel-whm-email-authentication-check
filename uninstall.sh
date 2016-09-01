#!/bin/sh

cd /
/usr/local/cpanel/bin/unregister_appconfig cmac

/bin/rm -Rfv /usr/local/cpanel/whostmgr/docroot/cgi/cprocks/cmac
/bin/rm -f /etc/cpanel-whm-mail-authentication-check
/bin/rm -f /etc/cpanel-whm-mail-authentication-check-excludes

echo "Done."
exit
