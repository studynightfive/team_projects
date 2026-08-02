"""修复检索指标的知识库与部门归属。

Revision ID: 0024_retrieval_metric_scope
Revises: 0023_metric_product_entity
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0024_retrieval_metric_scope"
down_revision: str | None = "0023_metric_product_entity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 有引用的旧记录可以从主商品文档无歧义地恢复知识库。
    op.execute(
        """
        UPDATE retrieval_metrics AS metric
        SET knowledge_base_id = document.knowledge_base_id
        FROM documents AS document
        WHERE metric.primary_product_id = document.id
          AND metric.knowledge_base_id IS DISTINCT FROM document.knowledge_base_id
        """
    )

    # 旧流式接口遗漏了 kb_ids。助手消息先于指标写入，30 秒内最近的一条可恢复其会话主库；
    # 超出该窗口的数据保持未归属，避免为了填满看板而猜错部门。
    op.execute(
        """
        WITH nearest_conversation AS (
            SELECT DISTINCT ON (metric.id)
                metric.id AS metric_id,
                conversation.kb_id AS knowledge_base_id
            FROM retrieval_metrics AS metric
            JOIN conversations AS conversation
              ON conversation.user_id = metric.user_id
            JOIN messages AS message
              ON message.conversation_id = conversation.id
            WHERE metric.event_type = 'answer'
              AND metric.knowledge_base_id IS NULL
              AND message.role = 'assistant'
              AND message.deleted_at IS NULL
              AND message.is_latest IS TRUE
              AND message.created_at <= metric.created_at
              AND message.created_at >= metric.created_at - INTERVAL '30 seconds'
            ORDER BY metric.id, message.created_at DESC, message.id DESC
        )
        UPDATE retrieval_metrics AS metric
        SET knowledge_base_id = nearest.knowledge_base_id
        FROM nearest_conversation AS nearest
        WHERE metric.id = nearest.metric_id
        """
    )

    # 部门快照始终服从知识库归属，修正超级管理员或跨部门账号产生的旧值。
    op.execute(
        """
        UPDATE retrieval_metrics AS metric
        SET department_id = knowledge_base.department_id
        FROM knowledge_bases AS knowledge_base
        WHERE metric.knowledge_base_id = knowledge_base.id
          AND metric.department_id IS DISTINCT FROM knowledge_base.department_id
        """
    )


def downgrade() -> None:
    # 这是错误数据修正，回滚版本时也不应恢复已经确认错误的部门归属。
    pass
