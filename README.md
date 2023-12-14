# NotaProxy

NotaProxy ('Nota') is simple URL-rewriting HTTP proxy.

One benefit of Nota is it allows a client that only understands (non-secure) HTTP to fetch web pages from websites that only accept (secure) HTTPS connections.

Nota is also able to save the traffic that passes through it, although it is not in a very user-friendly format.

Nota has many limitations and is only suitable for experimentation. If you want a real HTTP(S) proxy, try [MITM](https://mitmproxy.org/), [STunnel](https://www.stunnel.org/), or [Squid](http://www.squid-cache.org/)

## Quick Start

1. Ensure `tcpsvd`, `gzip`, and [`curl`](https://curl.se/) are installed.
2. Start the Nota server (`./run-nota.sh`). Nota will listen on port 8081.
3. Open a browser and type `http://localhost:8081/??3www.w3.org/about/`. The browser will connect to Nota. Nota will fetch `https://www.w3.org/about/`. The www.w3.org site will return a page to Nota. Nota will modify all links in the returned page. The modified page will be returned to the browser.

If `tcpsvd` is not available, a custom version of `thttpd` can be compiled. See `Servers`, below.

A single file [nota.html](http://localhost:8081/nota.html) exists only for convenience. It can be edited or deleted. If it is renamed and `tcpsvd` is used, update `index.cgi` to refer to the new name. 

## Limitations

Nota has a number of limitations, some of which are listed below:

* Nota recognizes links using a regex and the regex only handles 'common' cases. The link below spans two lines and is valid HTML, but would not be recognized as a link, and thus, would not be modified.

      href=
         /a/cool/file.html

* Similarly, links that have been encoded (e.g. `https%3A%2F%2F...`) will not be recognized.

* Nota expects to receive 'good' input and has no defense against malicious web pages.

* Nota removes the protocol (e.g. 'http://') from links. Any Javascript code that expects the protocol to exist may malfunction when it does not.

* Some web pages are essentially Javascript apps (rather than HTML web pages) that simply use HTTP to deliver the Javascript code to the browser. Links are dynamically constructed by Javascript running on the client. Nota is unable to modify such links.

* Nota tries to remember what website you are connecting to but can become confused. If you request a page from `right.here.com` and while the page is loading, a link on the page fetches something from `over.there.com`, Nota might start directing all future requests to `over.there.com`, rather than `right.here.com`.

* Nota modifies links in a manner that other HTTP proxies will not understand. (So, other HTTP proxies should not connect to Nota, however, Nota can connect to other HTTP proxies.)

* Nota cannot handle more than one client. 

* Nota blindly modifies all strings that look like URLs. This catches strings that are not URLs such as the DOCTYPE declaration. 

* Since the proxy logic is performed in a script, an HTTP `keep-alive` connection is not possible.

Despite these limitations, Nota works reasonably well.

## Rewriting

Nota modifies links in the following ways:

__URLs that begin with `href=`__
  * `//` is replaced with `??1`
  * `http://` is replaced with `??2`
  * `https://` is replaced with `??3`

__URLs that do not begin with `href=`__ (e.g. src, action, URL in CSS files, LINK elements)
  * `//` is replaced with `??4`
  * `http://` is replaced with `??5`
  * `https://` is replaced with `??6`

In theory, an `href` URL is one that a user would click on, while a non-href URL would be used to fetch resources needed by the page. In practice, thanks to Javascript, there are no guarantees.

When fetching resources, Nota modifies links in the reverse manner. For instance, a resource that starts with `??3` will be retrieved via `https://` and a resource that starts with `??2` will be retrieved via `http://`. Fetching a resource using `??1`, `??2`, or `??3` updates the saved protocol and host (so that future requests that do not specify the protocol or host can be directed to the correct website). Fetching a resource using `??4`, `??5`, or `??6` does not update the saved protocol or host.

    http://localhost:8081/??3some.where.com/about    # Fetches the 'about' resource from some.where.com. Also
                                                     # saves the protocol (https) and host (some.where.com) info.

    http://localhost:8081/path/to/image.png          # Uses saved protocol and host to fetch https://some.where.com/path/to/image.png

Since Nota is a rewriting HTTP proxy, its relatively simple to alter the response from the server before returning it to the client. For example, if an older client does not recognize, and refuses to process a response that specifies the `HTTP/2` protocol, Nota can alter the string to (e.g.) `HTTP/1.1` which may be sufficient to coax the client to process the response, rather than simply refusing.
## Servers

Nota was designed to run either under `tcpsvd` or under a custom version of [`thttpd`](https://acme.com/software/thttpd/).

Run `./build.sh` to compile the custom version of `thttpd` which has the following changes:

  * If the requested file is not found, instead of returning HTTP 404, the `index.cgi` CGI script will be run.
  * When a CGI script is run, all HTTP headers are made available in the `HTTP_HEADERS` environment variable.
  * The Location specified in an HTTP Redirect will be prefixed with `/??`.
  * The CGI time limit was increased to three minutes from 30 seconds.

Edit the `USE_THTTPD` variable in the `run-nota.sh` script to specify which server to use.

Running Nota using `tcpsvd` may not work if your client is picky. In such cases, use the custom `thttpd` server.
