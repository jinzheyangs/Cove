"""业务模块。

这里显式导入所有 models，确保 Alembic autogenerate 能看到它们。
"""

from app.modules.agent import models as agent_models  # noqa: F401
from app.modules.ai import models as ai_models  # noqa: F401
from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.bills import models as bills_models  # noqa: F401
from app.modules.coin_applies import models as coin_apply_models  # noqa: F401
from app.modules.coins import models as coins_models  # noqa: F401
from app.modules.conflicts import models as conflicts_models  # noqa: F401
from app.modules.couples import models as couples_models  # noqa: F401
from app.modules.daily import models as daily_models  # noqa: F401
from app.modules.diaries import models as diaries_models  # noqa: F401
from app.modules.inquiries import models as inquiries_models  # noqa: F401
from app.modules.mall import models as mall_models  # noqa: F401
from app.modules.notifications import models as notifications_models  # noqa: F401
from app.modules.secrets import models as secrets_models  # noqa: F401
from app.modules.simta import models as simta_models  # noqa: F401
from app.modules.todos import models as todos_models  # noqa: F401
from app.modules.users import models as users_models  # noqa: F401
