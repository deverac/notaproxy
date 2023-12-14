#!/bin/sh
set -e

# The './www/index.cgi' script can be run under thttpd or tcpsvd.

# Set to 1 to run thttpd.
# Set to 0 to run tcpsvd.
USE_THTTPD=0

if [ "$USE_THTTPD" = "1" ]; then

    SRVR=../thttpd/thttpd-2.29/thttpd
    if [ -x "$SRVR" ]; then
        # Run the thttpd proxy server.
        #  -C config file
        #  -D run in foreground
        $SRVR -C nota-thttpd.cnf
    else
        echo "$SRVR is not executable. Try running ./build.sh to create it."
        exit 1
    fi

else

    cd ./www
        # Run index.cgi (as a shell script) for each request.
        tcpsvd -vE 0.0.0.0 8081 sh ./index.cgi > /dev/null &
    cd ..

fi
