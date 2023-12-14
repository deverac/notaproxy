#!/bin/sh
set -e

# This script extracts thttpd source files, applies a patch, and then builds.
#
# To create a file.patch:
#     -r   recurse
#     -u   unified format
#     -N   treat absent files as empty
#   diff -ruN thttpd-2.29 thttpd-2.29mod > nota.patch

PKG=thttpd-2.29

rm -rf "$PKG"

tar -xzf "$PKG".tar.gz

chmod +w ./"$PKG"/*

# Apply patch
# -p0  ignore directory names
#  -s  silent
patch -p0 -s < nota.patch

cd "$PKG"
    ./configure
    make
cd ..
