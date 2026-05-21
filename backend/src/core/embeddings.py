from typing import Literal

from openai import AsyncOpenAI

from .settings import settings

client = AsyncOpenAI(base_url=settings.embeddings.base_url)


async def embed(
        inputs: list[str], modality: Literal["text", "image", "audio"]
) -> list[list[float]]:
    """Создаёт векторное представление текста"""

    response = await client.embeddings.create(
        model=settings.embeddings.model_name,
        input=inputs,
        dimensions=settings.embeddings.dimensions,
        encoding_format="base64",
        extra_body={"modality": modality}
    )

    # Сохранение порядка как при передаче текста
    sorted_data = sorted(response.data, key=lambda x: x.index)

    return [item.embedding for item in sorted_data]
