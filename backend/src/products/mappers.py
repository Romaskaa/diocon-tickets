from .domain.entities import SoftwareProduct
from .schemas import ProductResponse


def map_product_to_response(product: SoftwareProduct) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        created_at=product.created_at,
        updated_at=product.updated_at,
        name=product.name,
        vendor=product.vendor,
        version=product.version,
        description=product.description,
        display_name=product.display_name,
        category=product.category,
        status=product.status,
        attributes=product.attributes,
        created_by=product.created_by,
        updated_by=product.updated_by,
    )
