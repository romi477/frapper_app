def api_base_url(host: str, port: int | str | None = None, scheme: str = 'http') -> str:
    host = (host or '').strip().rstrip('/')
    if not host:
        raise ValueError('API host is empty')
    if '://' in host:

        return host
    if port is None or str(port).strip() == '':
        raise ValueError('API port is required')

    return f'{scheme}://{host}:{port}'
