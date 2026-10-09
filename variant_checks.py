"""Explicit size-specific configuration; never borrow XS's SKU for S."""


def configured_sizes(cfg):
    sizes = list(dict.fromkeys(part.strip() for part in cfg.get('PRODUCT_SIZES', cfg['PRODUCT_SIZE']).split(',')))
    if not sizes or any(size not in ('XS', 'S', 'XXL') for size in sizes):
        raise ValueError('PRODUCT_SIZES must contain XS, S and/or XXL')
    return sizes


def variant_config(cfg, size):
    if size not in ('XS', 'S', 'XXL'):
        raise ValueError('Supported sizes: XS, S, XXL')
    variant = dict(cfg)
    variant['PRODUCT_SIZE'] = size
    if size != cfg['PRODUCT_SIZE']:
        variant['PRODUCT_SKU'] = cfg.get('PRODUCT_SKU_' + size, '')
    return variant


def check_sizes(session, cfg, sizes):
    for index, size in enumerate(sizes):
        variant = variant_config(cfg, size)
        # A fresh document for each additional size prevents retaining XS's
        # sold-out rendering when changing to S. Browser/context stay alive.
        status, reason = session.check(variant, force_refresh=index > 0)
        yield variant, status, reason
