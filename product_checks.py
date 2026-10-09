"""Independent product configurations sharing one persistent browser context."""
from variant_checks import configured_sizes

CAMISOLE_URL = 'https://www.hollisterco.com/shop/eu-de/p/camisole-mit-spitzenbesatz-fr-lagenlooks-63270319?faceout=model&seq=15&gridProductPosition=3'


def configured_products(cfg):
    products = [dict(cfg, PRODUCT_NAME='Icon Henley')]
    color = cfg.get('CAMISOLE_COLOR', '').strip()
    if color:
        extra = dict(cfg)
        # Never carry identifiers from the Henley into the second product.
        for key in list(extra):
            if key.startswith('PRODUCT_SKU'):
                del extra[key]
        extra.update(PRODUCT_NAME='Camisole mit Spitzenbesatz',
                     PRODUCT_URL=CAMISOLE_URL, PRODUCT_COLOR=color,
                     PRODUCT_SIZE='XS', PRODUCT_SIZES='XS,S,XXL',
                     PRODUCT_SKU=cfg.get('CAMISOLE_SKU_XS', ''),
                     PRODUCT_SKU_S=cfg.get('CAMISOLE_SKU_S', ''),
                     PRODUCT_SKU_XXL=cfg.get('CAMISOLE_SKU_XXL', ''))
        products.append(extra)
    for product in products:
        configured_sizes(product)
    return products
