from app.extensions import db, cache
from app.models.prompt import Prompt


@cache.cached(timeout=3600, key_prefix='all_prompts')
def get_all_prompts():
    """
    Lấy tất cả các prompt từ database, sắp xếp theo tên file và cache kết quả.
    """
    prompts_from_db = Prompt.query.order_by(Prompt.filename).all()
    return {p.filename: p.content for p in prompts_from_db}