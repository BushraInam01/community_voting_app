from django.conf import settings
from django.utils.csp import CSP


def embed_csp_config():
    """CSP for the embeddable poll view: same policy, wider frame-ancestors."""
    config = dict(settings.SECURE_CSP)

    config['frame-ancestors'] = [
        CSP.SELF if origin == 'self' else origin
        for origin in settings.EMBED_FRAME_ANCESTORS
    ] or [CSP.SELF]

    return config
