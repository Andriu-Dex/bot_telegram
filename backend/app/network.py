import ssl
import truststore

def tls_context():
    """Use OS roots, including managed Windows certificates; never disable TLS."""
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
