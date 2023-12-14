#!/bin/sh
# Be careful when setting these.
#set -e
#set -x
#set -v
# Some commands will exit with a non-zero status even when they complete
# normally (e.g. echo abc | grep -v abc; echo $?). If 'set -e' is used
# the script will exit.
# 'set -x' and 'set -v' will output additional text which might interfere
# with processing.


# Set to 0 to delete temporary files.
# Set to 1 to keep temporary files.
KEEP_FILES=0


# If defined and the User-Agent HTTP header is received from client, the
# the header will be modified to use UAGENT.
#UAGENT="Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0"


# If defined, responses returned to client will have the HTTP version modified.
# This does nothing more than alter the version string; it does not modify the
# returned content to conform to the specified version.
# Setting HTTPVER might work for a client that ignores unrecognized HTTP versions.
#HTTPVER=1.1


# The directory to store temp files in.
TMP_DIR=../tmp
if [ ! -e "$TMP_DIR" ]; then
    mkdir -p "$TMP_DIR"
fi

RID=$RANDOM
if [ -z "$RID" ]; then
    RID=$(date +%s-%N)
else
    RID=$RID-$RANDOM
fi

if [ ${#RID} -lt 3 ]; then
    echo "Failed to generate random value."
    exit 1
fi

DAT=$TMP_DIR/tmp$RID          # Unique prefix

HOST_FILE=$TMP_DIR/ahost.txt  # Holds current host name (and port number)
PROT_FILE=$TMP_DIR/aprot.txt  # Holds current protocol
POST_FILE=$TMP_DIR/apost.txt  # Holds POSTed data

LOG_FILE=$TMP_DIR/alog.txt    # For ad-hoc logging when developing


# The method and url requested by browser.
REQ_METH=
REQ_URL=

# The protocol, host, path.
APROT=
AHOST=
APATH=

# Accepts any number of args; each arg is a filename; deletes the file
# if KEEP_FILES is 0.
rm_files() {
    if [ "$KEEP_FILES" = "0" ]; then
        while [ ! -z "$1" ]; do
            rm -f "$1"
            shift
        done
    fi
}

# Change URLs in supplied file to qq-encoded URLs.
# All qq-encoded URLs begin with two question marks.
# qq-encoded URLs that include the domain begin with a digit.
#   HREF URLs
#      ??1   //
#      ??2   http://
#      ??3   https://
#   Non-HREF URLs. (e.g. src, action, URL in CSS files, LINK elements.)
#      ??4   //
#      ??5   http://
#      ??6   https://
# qq-encoded URLs that do not include the domain begin with a '/'.
#      ??/some/file.html       # a path
#      ??/?a-query-string      # a query string
#      ??/#an-anchor           # an anchor
# In theory, an HREF URL is one that a user would click, while the other types
# of URLs fetch resources needed by the page. In practice, thanks to Javascript,
# there are no guarantees.
qq_encode_file() {
    FIL="$1"
    sed \
        -e "s|\\(<link\\s[^>]*\\shref='\\)//|\\1??4|g" \
        -e 's|\(<link\s[^>]*\shref="\)//|\1??4|g' \
        -e "s|\\(<link\\s[^>]*\\shref='\\)http://|\\1??5|g" \
        -e 's|\(<link\s[^>]*\shref="\)http://|\1??5|g' \
        -e 's|\(<link\s[^>]*\shref=\)http://|\1??5|g' \
        -e "s|\\(<link\\s[^>]*\\shref='\\)https://|\\1??6|g" \
        -e 's|\(<link\s[^>]*\shref="\)https://|\1??6|g' \
        -e 's|\(<link\s[^>]*\shref=\)https://|\1??6|g' \
        \
        -e "s|action='//|action='??1|g" \
        -e 's|action="//|action="??1|g' \
        -e "s|action='http://|action='??2|g" \
        -e 's|action="http://|action="??2|g' \
        -e 's|action=http://|action=??2|g' \
        -e "s|action='https://|action='??3|g" \
        -e 's|action="https://|action="??3|g' \
        -e 's|action=https://|action=??3|g' \
        \
        -e "s|href='//|href='??1|g" \
        -e 's|href="//|href="??1|g' \
        -e "s|href='http://|href='??2|g" \
        -e "s|href=http://|href=??2|g" \
        -e 's|href="http://|href="??2|g' \
        -e "s|href='https://|href='??3|g" \
        -e 's|href="https://|href="??3|g' \
        -e 's|href=https://|href=??3|g' \
        \
        -e "s|'//|'??4|g" \
        -e 's|"//|"??4|g' \
        -e 's|(//|(??4|g' \
        -e "s|'http://|'??5|g" \
        -e 's|"http://|"??5|g' \
        -e 's|(http://|(??5|g' \
        -e 's|=http://|=??5|g' \
        -e "s|'https://|'??6|g" \
        -e 's|"https://|"??6|g' \
        -e 's|(https://|(??6|g' \
        -e 's|=https://|=??6|g' \
        "$FIL"
}


# Convert a qq-encoded URL to a non-encoded URL.
# The query-string (if any) will be included as part of the path.
# The qq-encoded URL must start with '/' and any text between that
# and '??' will be removed. This helps extract the desired data from URLs such as:
#    /search??3www.somewhere.com/path/to/file.html
decode_qq_url() {
    local METH="$1"
    local ENC_URL="$2"
    if [ "${ENC_URL#/*\?\?}" != "$ENC_URL" ]; then
        # Decode qq-encoded URL that includes a domain name.
        EU="${ENC_URL#/*\?\?}"               # Remove shortest match of '/*??' from head.
        if [ "${EU#1}" != "$EU" ]; then
            # href //
            MOD="${EU#1}"                     # Remove '1' from head.
            AHOST="${MOD%%/*}"                # Remove longest match of '/*' from tail.
            APATH="${MOD#$AHOST}"             # Remove Host from front (includes query string, if any)
            if [ "$METH" = "GET" ]; then
                echo "$AHOST" > "$HOST_FILE"  # Save host
            fi
        elif [ "${EU#2}" != "$EU" ]; then
            # href http://
            MOD="${EU#2}"                     # Remove '2' from head.
            APROT="http"
            AHOST="${MOD%%/*}"                # Remove longest match of '/*' from tail.
            APATH="${MOD#$AHOST}"             # Remove Host from front
            if [ "$METH" = "GET" ]; then
                echo "$AHOST" > "$HOST_FILE"  # Save host
                echo "$APROT" > "$PROT_FILE"  # Save protocol
            fi
        elif [ "${EU#3}" != "$EU" ]; then
            # href https://
            MOD="${EU#3}"                     # Remove '3' from head.
            APROT="https"
            AHOST="${MOD%%/*}"                # Remove longest match of '/*' from tail.
            APATH="${MOD#$AHOST}"             # Remove Host from front
            if [ "$METH" = "GET" ]; then
                echo "$AHOST" > "$HOST_FILE"  # Save host
                echo "$APROT" > "$PROT_FILE"  # Save protocol
            fi
        elif [ "${EU#4}" != "$EU" ]; then
            # non-href //
            MOD="${EU#4}"                     # Remove '4' from head.
            AHOST="${MOD%%/*}"                # Remove longest match of '/*' from tail.
            APATH="${MOD#$AHOST}"             # Remove Host from front
        elif [ "${EU#5}" != "$EU" ]; then
            # non-href http://
            MOD="${EU#5}"                     # Remove '5' from head.
            AHOST="${MOD%%/*}"                # Remove longest match of '/*' from tail.
            APATH="${MOD#$AHOST}"             # Remove Host from front
            APROT="http"
        elif [ "${EU#6}" != "$EU" ]; then
            # non-href https://
            MOD="${EU#6}"                     # Remove '6' from head.
            AHOST="${MOD%%/*}"                # Remove longest match of '/*' from tail.
            APATH="${MOD#$AHOST}"             # Remove Host from front
            APROT="https"
        elif [ "${EU#/}" != "$EU" ]; then
            # Path, with no domain name. e.g. '/some/file.html'
            APATH="$ENC_URL"
        else
            # We should never get here.
            echo "Unhandled request url: $ENC_URL" >> $LOG_FILE
        fi
    else
        APATH="$ENC_URL" # Includes query string (if it exists)
    fi

    if [ -z "$APROT" ]; then
        if [ -f "$PROT_FILE" ]; then
            APROT=$(cat "$PROT_FILE") # Read protocol (may be empty)
        fi
        if [ -z "$APROT" ]; then
            APROT="https"
        fi
    fi

    if [ -z "$AHOST" ]; then
        if [ -f "$HOST_FILE" ]; then
            AHOST=$(cat "$HOST_FILE")
        fi
        if [ -z "$AHOST" ]; then
            MSG="No host"
            echo "HTTP/1.1 404 Not Found" 
            echo "Content-type: text/plain; charset=utf-8"
            echo "Cache-Control: no-store"
            echo "Expires: 0" # Expire immediately
            echo "Content-Length: $(echo $MSG | wc -c)"
            echo ""
            echo "$MSG"
            exit
        fi
    fi

    URL="${APROT}://${AHOST}${APATH}"
}

process_response() {
    FIL="$1"

    HHH=${FIL}_0hdr_
    BBB=${FIL}_1body_
    RES=${FIL}_2res
    
    # Extract response headers. (Everything up to first blank line.)
    sed '/^\s*$/q' $FIL > ${HHH}a

    # Extract response body. (Everything after first blank line.)
    sed -n '/^\s*$/,$p' $FIL > ${BBB}a
    sed -i '1d' ${BBB}a  # Remove initial blank line.


    # content-security-policy prevents Firefox from loading content thru proxy.
    # nel specifies Network Error Logging info.
    # report-to specifies who to report to
    # server-timing, etag, x- are just noise.
    # strict-transport-security forces upgrading to HTTPS
    grep -i -v "^content-security-policy: " ${HHH}a \
     | grep -i -v "^content-security-policy-report-only: " \
     | grep -i -v "^nel: " \
     | grep -i -v "^strict-transport-security: " \
     | grep -i -v "^report-to: " \
     | grep -i -v "^server-timing" \
     | grep -i -v "^etag" \
     | grep -i -v "^x-" \
     > ${HHH}b

    if [ ! -z "$HTTPVER" ]; then
        # Current legal values are: '0.9', '1.0', '1.1', '2', '3'.
        sed -i "s|^HTTP/[01239.]*|HTTP/$HTTPVER|" ${HHH}b
    fi

    # Rewrite redirect (if it exists).
    sed -i \
      -e 's|^[Ll]ocation:.*https://\(.*\)$|Location: /??3\1|'\
      -e 's|^[Ll]ocation:.*http://\(.*\)$|Location: /??2\1|' \
      -e 's|^[Ll]ocation:.*//\(.*\)$|Location: /??1\1|' \
       ${HHH}b

    # Rewrite selected file types.
    #   * text/(html|css|javascript)
    #   * application/javascript
    #   * application/x-javascript
    # There are probably more.
    if grep -q -i "^content-type:.*\(text/\|javascript\)" ${HHH}b; then

        if grep -q -i "^content-encoding:.*gzip" ${HHH}b; then
            # Remove header.
            grep -i -v "^content-encoding:" ${HHH}b > ${HHH}c
            # Decompress body. (-d decompress; -c write to stdout)
            # Must use '-c' else gzip errors due to missing file extension.
            gzip -c -d ${BBB}a > ${BBB}b
        else
            mv ${HHH}b ${HHH}c
            mv ${BBB}a ${BBB}b
        fi

        qq_encode_file ${BBB}b > ${BBB}c
        
        if grep -q -i "^content-length: " ${HHH}c; then
            # Update Content-Length HTTP header.
            CL=$(cat ${BBB}c | wc -c)
            sed -i "s/^[Cc]ontent-[Ll]ength: .*/content-length $CL/" ${HHH}c
        fi
        cat ${HHH}c ${BBB}c > $RES
    else
        cat ${HHH}b ${BBB}a > $RES
    fi
    cat $RES

    rm_files ${HHH}a ${HHH}b ${HHH}c ${BBB}a ${BBB}b ${BBB}c $RES
}



HDRS=${DAT}_0hdrs
RESP=${DAT}_1resp

rm_files "$HDRS" "$RESP"

# Save HTTP headers for processing later.
# The absence of HTTP_HEADERS means we are running in a shell script
# launched by tcdsvd (or similar).
# The presence of HTTP_HEADERS means we are running in a CGI script
# under a customized version of thttpd.
if [ -z "$HTTP_HEADERS" ]; then
    # Read from stdin, save to file.
    LIN=xxx
    while [ "${#LIN}" -gt 2 ]; do
        read -r LIN
        echo "$LIN" >> $HDRS
     done
else
    # Read HTTP headers from environment vars, save to file
    TMPURL="$SCRIPT_NAME"
    if [ ! -z "$QUERY_STRING" ]; then
        TMPURL="$TMPURL?$QUERY_STRING"
    fi
    echo "$REQUEST_METHOD $TMPURL $SERVER_PROTOCOL" > $HDRS
    echo "$HTTP_HEADERS" >> $HDRS
fi


# Parse the saved HTTP headers.
while IFS= read -r LIN; do
    case "$LIN" in
        GET\ *) REQ_METH=GET; REQ_URL=$(echo $LIN | cut -f 2 -d ' ') ;;
        POST\ *) REQ_METH=POST; REQ_URL=$(echo $LIN | cut -f 2 -d ' ') ;;
    esac
done < $HDRS



# The absence of HTTP_HEADERS means we are running in a shell script
# launched by tcdsvd (or similar) and must handle file requests.
# The presence of HTTP_HEADERS means we are running in a CGI script
# under a customized version of thttpd.
if [ -z "$HTTP_HEADERS" ]; then
    if [ "$REQ_URL" = "/nota.html" ]; then
        echo "HTTP/1.1 200 OK" 
        echo "Server: NotaProxy/0.1"
        echo "Content-Type: text/html"
        if [ -e nota.html ]; then
            echo "Content-Length: $(cat nota.html | wc -c)"
            echo ""
            cat nota.html
        else
            MSG="<html><head></head><body>This is NotaProxy</body></html>"
            echo "Content-Length: $(echo $MSG | wc -c)"
            echo ""
            echo "$MSG"
        fi
        rm_files $HDRS $HOST_FILE
        exit
    fi
fi


# Sets $URL, $APROT, $AHOST, $APATH variable
decode_qq_url "$REQ_METH" "$REQ_URL"



# Remove the first line (tail -n +2), which contains the method and URL.
# We can only decompress gzip data, so gzip.
# We are not smart enough to handle keep-alive connection, so close.
# Some servers require Host, Origin, and/or Referer; we use $AHOST and hope it works.
tail -n +2 $HDRS |  sed \
    -e "s|^[Aa]ccept-[Ee]ncoding:.*|accept-encoding: gzip|" \
    -e "s|^[Cc]onnection:.*|connection: close|" \
    -e "s|^[Hh]ost:.*|host: $AHOST|" \
    -e "s|^[Oo]rigin:.*|origin: $APROT://$AHOST|" \
    -e "s|^[Rr]eferer:.*|referer: $APROT://$AHOST|" \
    > ${HDRS}_mod

# Replace User-Agent.
if [ ! -z "$UAGENT" ]; then
    sed -i -e "s|^[Uu]ser-[Aa]gent:.*|user-agent: $UAGENT|" ${HDRS}_mod
fi


if [ "$REQ_METH" = "GET" ]; then

    curl -s -i -H @${HDRS}_mod "$URL" > "$RESP"   # Make request, save response

    # Edit links in response and send result to client.
    process_response "$RESP"

elif [ "$REQ_METH" = "POST" ]; then

    # Read data. Due to the nature of POST requests, 'cat' will never complete, so we use
    # timeout to terminate it and hope all POSTed data has been read in 2 seconds.
    timeout 2 cat - > "$POST_FILE"

    curl -X POST -s -i -H @${HDRS}_mod --data-binary @"$POST_FILE" "$URL" > "$RESP"   # Make request, save response

    # Edit links in response and send result to client.
    process_response "$RESP"
else

    # Some other HTTP method (e.g. HEAD, PUT)
    MSG="<html><head></head><body>Unsupported Method</body></html>"
    echo "HTTP/1.1 405 Method Not Allowed" 
    echo "Server: Nota/0.6"
    echo "Content-Type: text/html"
    echo "Content-Length: $(echo $MSG | wc -c)"
    echo ""
    echo "$MSG"

fi

rm_files $HDRS ${HDRS}_mod $RESP $POST_FILE
