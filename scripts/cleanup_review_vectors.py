"""删除向量库里遗留的争吵复盘向量。

功能下线后，数据库里的表已经删了，但 Chroma 里可能还留着
source_type='review' 的旧向量。跑一次这个脚本清掉。

用法（本地连 Docker 里的 Chroma）：

    CHROMA_HOST=localhost CHROMA_PORT=58000 \
        uv run python scripts/cleanup_review_vectors.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402


def main() -> None:
    import chromadb

    client = chromadb.HttpClient(
        host=settings.CHROMA_HOST, port=settings.CHROMA_PORT
    )
    try:
        collection = client.get_collection(settings.CHROMA_COLLECTION)
    except Exception:
        print(f"集合不存在，无需清理: {settings.CHROMA_COLLECTION}")
        return

    collection.delete(where={"source_type": "review"})
    print("已清理争吵复盘向量")


if __name__ == "__main__":
    main()
