from app_util.db_util import DBUtil
from app_util.log_util import infologger
from common_helper.decorators import log_timing
from modules.concerns import concerns_queries as cq


class ConcernsHandler(DBUtil):

    @log_timing("concerns_handler.create_report")
    def create_report(
        self, user_id: str, category: str, subject: str | None, body: str
    ) -> tuple[int, dict | str]:
        infologger.info(f"ConcernsHandler.create_report | user_id={user_id} category={category}")
        row = self.execute_query_with_value_returning(
            cq.INSERT_REPORT,
            {"user_id": user_id, "category": category, "subject": subject, "body": body},
        )
        if not row:
            infologger.warning(f"ConcernsHandler.create_report | user not found | user_id={user_id}")
            return 404, "User not found"
        infologger.info(f"ConcernsHandler.create_report | stored report_id={row['id']} user_id={user_id}")
        return 201, {"id": str(row["id"]), "category": row["category"], "created_at": str(row["created_at"])}
