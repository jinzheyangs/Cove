"""业务模块。

这里显式导入所有 models，确保 Alembic autogenerate 能看到它们。
"""

from app.modules.couples import models as couples_models  # noqa: F401
from app.modules.users import models as users_models  # noqa: F401
