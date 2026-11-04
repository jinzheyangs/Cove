"""业务模块。

这里显式导入所有 models，确保 Alembic autogenerate 能看到它们。
"""

from app.modules.bills import models as bills_models  # noqa: F401
from app.modules.coin_applies import models as coin_apply_models  # noqa: F401
from app.modules.coins import models as coins_models  # noqa: F401
from app.modules.couples import models as couples_models  # noqa: F401
from app.modules.diaries import models as diaries_models  # noqa: F401
from app.modules.mall import models as mall_models  # noqa: F401
from app.modules.secrets import models as secrets_models  # noqa: F401
from app.modules.todos import models as todos_models  # noqa: F401
from app.modules.users import models as users_models  # noqa: F401
