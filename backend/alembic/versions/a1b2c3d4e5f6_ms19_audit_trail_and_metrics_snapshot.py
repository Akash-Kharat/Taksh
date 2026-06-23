"""ms19_audit_trail_and_metrics_snapshot

Revision ID: a1b2c3d4e5f6
Revises: 6fae9924a500
Create Date: 2026-06-22 17:38:00.000000

MS-19 Product Hardening:
  - Adds MetricsSnapshot table
  - Adds correlation_id to conversation_runtime_sessions
  - Adds created_by, source_component, correlation_id audit columns to:
      cognitive_traces, ai_responses, tool_executions,
      provider_sessions, conversation_turns, memory_episodes
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3fee697e8d21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # MetricsSnapshot table (new)
    # -----------------------------------------------------------------------
    op.create_table(
        'metrics_snapshots',
        sa.Column('snapshot_id',        sa.String(),  primary_key=True),
        sa.Column('captured_at',        sa.DateTime(), nullable=False),
        sa.Column('conversation_count', sa.Integer(),  nullable=False, server_default='0'),
        sa.Column('turn_count',         sa.Integer(),  nullable=False, server_default='0'),
        sa.Column('provider_requests',  sa.Integer(),  nullable=False, server_default='0'),
        sa.Column('provider_failures',  sa.Integer(),  nullable=False, server_default='0'),
        sa.Column('tool_executions',    sa.Integer(),  nullable=False, server_default='0'),
        sa.Column('memory_recalls',     sa.Integer(),  nullable=False, server_default='0'),
        sa.Column('knowledge_searches', sa.Integer(),  nullable=False, server_default='0'),
        sa.Column('average_latency_ms', sa.Float(),    nullable=False, server_default='0.0'),
    )
    op.create_index('ix_metrics_snapshots_captured_at', 'metrics_snapshots', ['captured_at'])

    # -----------------------------------------------------------------------
    # conversation_runtime_sessions — correlation_id (root of trace chain)
    # -----------------------------------------------------------------------
    op.add_column('conversation_runtime_sessions',
        sa.Column('correlation_id', sa.String(), nullable=True))
    op.create_index('ix_crs_correlation_id', 'conversation_runtime_sessions', ['correlation_id'])

    # -----------------------------------------------------------------------
    # cognitive_traces — audit trail
    # -----------------------------------------------------------------------
    op.add_column('cognitive_traces', sa.Column('created_by',       sa.String(), nullable=True))
    op.add_column('cognitive_traces', sa.Column('source_component', sa.String(), nullable=True))
    op.add_column('cognitive_traces', sa.Column('correlation_id',   sa.String(), nullable=True))
    op.create_index('ix_cognitive_traces_correlation_id', 'cognitive_traces', ['correlation_id'])

    # -----------------------------------------------------------------------
    # ai_responses — audit trail
    # -----------------------------------------------------------------------
    op.add_column('ai_responses', sa.Column('created_by',       sa.String(), nullable=True))
    op.add_column('ai_responses', sa.Column('source_component', sa.String(), nullable=True))
    op.add_column('ai_responses', sa.Column('correlation_id',   sa.String(), nullable=True))
    op.create_index('ix_ai_responses_correlation_id', 'ai_responses', ['correlation_id'])

    # -----------------------------------------------------------------------
    # tool_executions — audit trail
    # -----------------------------------------------------------------------
    op.add_column('tool_executions', sa.Column('created_by',       sa.String(), nullable=True))
    op.add_column('tool_executions', sa.Column('source_component', sa.String(), nullable=True))
    op.add_column('tool_executions', sa.Column('correlation_id',   sa.String(), nullable=True))
    op.create_index('ix_tool_executions_correlation_id', 'tool_executions', ['correlation_id'])

    # -----------------------------------------------------------------------
    # provider_sessions — audit trail
    # -----------------------------------------------------------------------
    op.add_column('provider_sessions', sa.Column('created_by',       sa.String(), nullable=True))
    op.add_column('provider_sessions', sa.Column('source_component', sa.String(), nullable=True))
    op.add_column('provider_sessions', sa.Column('correlation_id',   sa.String(), nullable=True))
    op.create_index('ix_provider_sessions_correlation_id', 'provider_sessions', ['correlation_id'])

    # -----------------------------------------------------------------------
    # conversation_turns — audit trail
    # -----------------------------------------------------------------------
    op.add_column('conversation_turns', sa.Column('created_by',       sa.String(), nullable=True))
    op.add_column('conversation_turns', sa.Column('source_component', sa.String(), nullable=True))
    op.add_column('conversation_turns', sa.Column('correlation_id',   sa.String(), nullable=True))
    op.create_index('ix_conversation_turns_correlation_id', 'conversation_turns', ['correlation_id'])

    # -----------------------------------------------------------------------
    # memory_episodes — audit trail
    # -----------------------------------------------------------------------
    op.add_column('memory_episodes', sa.Column('created_by',       sa.String(), nullable=True))
    op.add_column('memory_episodes', sa.Column('source_component', sa.String(), nullable=True))
    op.add_column('memory_episodes', sa.Column('correlation_id',   sa.String(), nullable=True))
    op.create_index('ix_memory_episodes_correlation_id', 'memory_episodes', ['correlation_id'])


def downgrade() -> None:
    # memory_episodes
    op.drop_index('ix_memory_episodes_correlation_id',   table_name='memory_episodes')
    op.drop_column('memory_episodes', 'correlation_id')
    op.drop_column('memory_episodes', 'source_component')
    op.drop_column('memory_episodes', 'created_by')

    # conversation_turns
    op.drop_index('ix_conversation_turns_correlation_id', table_name='conversation_turns')
    op.drop_column('conversation_turns', 'correlation_id')
    op.drop_column('conversation_turns', 'source_component')
    op.drop_column('conversation_turns', 'created_by')

    # provider_sessions
    op.drop_index('ix_provider_sessions_correlation_id', table_name='provider_sessions')
    op.drop_column('provider_sessions', 'correlation_id')
    op.drop_column('provider_sessions', 'source_component')
    op.drop_column('provider_sessions', 'created_by')

    # tool_executions
    op.drop_index('ix_tool_executions_correlation_id', table_name='tool_executions')
    op.drop_column('tool_executions', 'correlation_id')
    op.drop_column('tool_executions', 'source_component')
    op.drop_column('tool_executions', 'created_by')

    # ai_responses
    op.drop_index('ix_ai_responses_correlation_id', table_name='ai_responses')
    op.drop_column('ai_responses', 'correlation_id')
    op.drop_column('ai_responses', 'source_component')
    op.drop_column('ai_responses', 'created_by')

    # cognitive_traces
    op.drop_index('ix_cognitive_traces_correlation_id', table_name='cognitive_traces')
    op.drop_column('cognitive_traces', 'correlation_id')
    op.drop_column('cognitive_traces', 'source_component')
    op.drop_column('cognitive_traces', 'created_by')

    # conversation_runtime_sessions
    op.drop_index('ix_crs_correlation_id', table_name='conversation_runtime_sessions')
    op.drop_column('conversation_runtime_sessions', 'correlation_id')

    # metrics_snapshots
    op.drop_index('ix_metrics_snapshots_captured_at', table_name='metrics_snapshots')
    op.drop_table('metrics_snapshots')
