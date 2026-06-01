#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Monkeypatch ssl.wrap_socket for Python 3.12+ (django-sslserver compatibility)
try:
    import ssl
    if not hasattr(ssl, 'wrap_socket'):
        def wrap_socket(sock, keyfile=None, certfile=None, server_side=False, cert_reqs=None, ssl_version=None, ca_certs=None, do_handshake_on_connect=True, suppress_ragged_eofs=True, ciphers=None):
            if cert_reqs is None:
                cert_reqs = ssl.CERT_NONE
            # Create a context appropriate for server or client
            if ssl_version is None:
                ssl_version = ssl.PROTOCOL_TLS_SERVER if server_side else ssl.PROTOCOL_TLS_CLIENT
            elif ssl_version == ssl.PROTOCOL_TLS:
                # Use standard protocol for modern python depending on side
                ssl_version = ssl.PROTOCOL_TLS_SERVER if server_side else ssl.PROTOCOL_TLS_CLIENT
            
            context = ssl.SSLContext(ssl_version)
            context.check_hostname = False
            context.verify_mode = cert_reqs
            if certfile:
                context.load_cert_chain(certfile, keyfile)
            return context.wrap_socket(sock, server_side=server_side, do_handshake_on_connect=do_handshake_on_connect, suppress_ragged_eofs=suppress_ragged_eofs)
        ssl.wrap_socket = wrap_socket
except ImportError:
    pass



def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
