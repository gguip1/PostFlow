from vcli.adapters.velog.adapter import PostData
from vcli.models import Meta


def to_post_data(meta: Meta, content: str) -> PostData:
    """Meta + content를 Velog 발행용 PostData로 변환한다."""
    return PostData(
        title=meta.title,
        body=content,
        tags=meta.tags,
        description=meta.description,
        slug=meta.slug,
        visibility=meta.visibility,
        series=meta.series,
    )
