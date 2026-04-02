"""
NexusFlow Customer Success Digital FTE - Reports API
=====================================================
Exercise 2.6: Daily Reports & Dashboard Endpoints

FastAPI endpoints for accessing metrics and generating reports.

Endpoints:
- GET /reports/daily-sentiment - Daily sentiment report
- GET /reports/dashboard - Dashboard metrics
- GET /reports/trends - Sentiment trends over time

Author: Digital FTE Team
Version: 1.0.0 (Production)
"""

import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from workers.message_processor import DatabasePool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/reports", tags=["Reports"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class DailySentimentReport:
    """Daily sentiment report response model."""
    
    def __init__(
        self,
        report_date: date,
        total_tickets: int,
        resolved_by_ai: int,
        resolved_by_human: int,
        ai_resolution_rate: float,
        sentiment_distribution: Dict[str, int],
        top_sentiment: str,
        sentiment_trend: str,
        channel_breakdown: Dict[str, int],
        escalation_rate: float,
        avg_response_time_minutes: float,
        avg_resolution_time_hours: float,
        top_topics: List[str],
        sla_compliance_rate: float,
        csat_score: Optional[float]
    ):
        self.report_date = report_date
        self.total_tickets = total_tickets
        self.resolved_by_ai = resolved_by_ai
        self.resolved_by_human = resolved_by_human
        self.ai_resolution_rate = ai_resolution_rate
        self.sentiment_distribution = sentiment_distribution
        self.top_sentiment = top_sentiment
        self.sentiment_trend = sentiment_trend
        self.channel_breakdown = channel_breakdown
        self.escalation_rate = escalation_rate
        self.avg_response_time_minutes = avg_response_time_minutes
        self.avg_resolution_time_hours = avg_resolution_time_hours
        self.top_topics = top_topics
        self.sla_compliance_rate = sla_compliance_rate
        self.csat_score = csat_score
    
    def dict(self) -> Dict[str, Any]:
        return {
            "report_date": self.report_date.isoformat(),
            "summary": {
                "total_tickets": self.total_tickets,
                "resolved_by_ai": self.resolved_by_ai,
                "resolved_by_human": self.resolved_by_human,
                "ai_resolution_rate": self.ai_resolution_rate
            },
            "sentiment": {
                "distribution": self.sentiment_distribution,
                "top_sentiment": self.top_sentiment,
                "trend": self.sentiment_trend
            },
            "channels": self.channel_breakdown,
            "performance": {
                "escalation_rate": self.escalation_rate,
                "avg_response_time_minutes": self.avg_response_time_minutes,
                "avg_resolution_time_hours": self.avg_resolution_time_hours,
                "sla_compliance_rate": self.sla_compliance_rate
            },
            "topics": self.top_topics,
            "customer_satisfaction": {
                "csat_score": self.csat_score
            }
        }


class DashboardMetrics:
    """Real-time dashboard metrics response model."""
    
    def __init__(
        self,
        timestamp: str,
        today_stats: Dict[str, Any],
        this_week_stats: Dict[str, Any],
        this_month_stats: Dict[str, Any],
        sentiment_trend: List[Dict[str, Any]],
        channel_performance: Dict[str, Any],
        top_agents: List[Dict[str, Any]],
        recent_escalations: List[Dict[str, Any]]
    ):
        self.timestamp = timestamp
        self.today_stats = today_stats
        self.this_week_stats = this_week_stats
        self.this_month_stats = this_month_stats
        self.sentiment_trend = sentiment_trend
        self.channel_performance = channel_performance
        self.top_agents = top_agents
        self.recent_escalations = recent_escalations
    
    def dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "today": self.today_stats,
            "this_week": self.this_week_stats,
            "this_month": self.this_month_stats,
            "sentiment_trend": self.sentiment_trend,
            "channel_performance": self.channel_performance,
            "top_agents": self.top_agents,
            "recent_escalations": self.recent_escalations
        }


# =============================================================================
# ROUTES
# =============================================================================

@router.get(
    "/daily-sentiment",
    response_model=Dict[str, Any],
    summary="Daily Sentiment Report",
    description="Get daily customer sentiment report with breakdown by channel"
)
async def get_daily_sentiment_report(
    report_date: Optional[date] = Query(
        None,
        description="Date for the report (defaults to yesterday)"
    ),
    db_pool: DatabasePool = Depends(lambda: DatabasePool())
) -> Dict[str, Any]:
    """
    Generate and return daily sentiment report.
    
    Calculates:
    - Total tickets and resolution breakdown (AI vs Human)
    - Sentiment distribution across all messages
    - Channel breakdown
    - Escalation rate
    - Average response and resolution times
    - Top topics discussed
    - SLA compliance rate
    - Customer satisfaction score
    """
    if report_date is None:
        report_date = datetime.now().date() - timedelta(days=1)
    
    async with db_pool.acquire() as conn:
        # Get metrics from agent_metrics table
        metrics = await conn.fetchrow("""
            SELECT * FROM agent_metrics
            WHERE metric_date = $1 AND metric_hour IS NULL
        """, report_date)
        
        if not metrics:
            # Generate report on the fly
            from workers.metrics_collector import MetricsCollector
            collector = MetricsCollector(db_pool)
            metrics_data = await collector._calculate_daily_metrics(conn, report_date)
        else:
            metrics_data = dict(metrics)
        
        # Get top topics
        topics_result = await conn.fetch("""
            SELECT topic, COUNT(*) as count
            FROM (
                SELECT jsonb_array_elements_text(topics_discussed) as topic
                FROM conversations
                WHERE DATE(created_at) = $1
            ) t
            GROUP BY topic
            ORDER BY count DESC
            LIMIT 5
        """, report_date)
        top_topics = [r['topic'] for r in topics_result]
        
        # Determine top sentiment
        sentiment_dist = metrics_data.get('sentiment_distribution', {})
        top_sentiment = max(sentiment_dist.keys(), key=lambda k: sentiment_dist[k]) if sentiment_dist else "neutral"
        
        # Determine sentiment trend (compare to previous day)
        prev_day = report_date - timedelta(days=1)
        prev_metrics = await conn.fetchrow("""
            SELECT sentiment_distribution FROM agent_metrics
            WHERE metric_date = $1 AND metric_hour IS NULL
        """, prev_day)
        
        if prev_metrics and prev_metrics['sentiment_distribution']:
            prev_dist = prev_metrics['sentiment_distribution']
            positive_change = (
                sentiment_dist.get('positive', 0) + sentiment_dist.get('very_positive', 0)
            ) > (
                prev_dist.get('positive', 0) + prev_dist.get('very_positive', 0)
            )
            sentiment_trend = "improving" if positive_change else "stable"
        else:
            sentiment_trend = "stable"
        
        # Build report
        report = DailySentimentReport(
            report_date=report_date,
            total_tickets=metrics_data.get('total_tickets', 0),
            resolved_by_ai=metrics_data.get('ai_resolved_count', 0),
            resolved_by_human=metrics_data.get('human_resolved_count', 0),
            ai_resolution_rate=metrics_data.get('ai_resolution_rate', 0),
            sentiment_distribution=sentiment_dist,
            top_sentiment=top_sentiment,
            sentiment_trend=sentiment_trend,
            channel_breakdown=metrics_data.get('messages_by_channel', {}),
            escalation_rate=metrics_data.get('escalation_rate', 0),
            avg_response_time_minutes=round(metrics_data.get('avg_first_response_time', 0) / 60, 2),
            avg_resolution_time_hours=round(metrics_data.get('avg_resolution_time', 0) / 3600, 2),
            top_topics=top_topics,
            sla_compliance_rate=metrics_data.get('sla_compliance_rate', 100),
            csat_score=metrics_data.get('avg_csat_score')
        )
        
        return report.dict()


@router.get(
    "/dashboard",
    response_model=Dict[str, Any],
    summary="Dashboard Metrics",
    description="Get real-time dashboard metrics for monitoring"
)
async def get_dashboard_metrics(
    db_pool: DatabasePool = Depends(lambda: DatabasePool())
) -> Dict[str, Any]:
    """
    Get real-time dashboard metrics.
    
    Includes:
    - Today's statistics
    - Week-to-date statistics
    - Month-to-date statistics
    - Sentiment trend (last 7 days)
    - Channel performance
    - Recent escalations
    """
    now = datetime.now()
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    async with db_pool.acquire() as conn:
        # Today's stats
        today_stats = await conn.fetchrow("""
            SELECT
                COUNT(DISTINCT c.id) as conversations,
                COUNT(m.id) as messages,
                COUNT(DISTINCT t.id) as tickets,
                COUNT(DISTINCT e.id) as escalations,
                AVG(EXTRACT(EPOCH FROM (t.first_response_at - t.created_at))) as avg_response_time
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            LEFT JOIN tickets t ON c.id = t.conversation_id
            LEFT JOIN escalations e ON t.id = e.ticket_id
            WHERE DATE(c.created_at) = $1
        """, today)
        
        # Week stats
        week_stats = await conn.fetchrow("""
            SELECT
                COUNT(DISTINCT c.id) as conversations,
                COUNT(m.id) as messages,
                COUNT(DISTINCT t.id) as tickets,
                COUNT(DISTINCT e.id) as escalations
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            LEFT JOIN tickets t ON c.id = t.conversation_id
            LEFT JOIN escalations e ON t.id = e.ticket_id
            WHERE DATE(c.created_at) >= $1
        """, week_start)
        
        # Month stats
        month_stats = await conn.fetchrow("""
            SELECT
                COUNT(DISTINCT c.id) as conversations,
                COUNT(m.id) as messages,
                COUNT(DISTINCT t.id) as tickets,
                COUNT(DISTINCT e.id) as escalations
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            LEFT JOIN tickets t ON c.id = t.conversation_id
            LEFT JOIN escalations e ON t.id = e.ticket_id
            WHERE DATE(c.created_at) >= $1
        """, month_start)
        
        # Sentiment trend (last 7 days)
        sentiment_trend = await conn.fetch("""
            SELECT metric_date, sentiment_distribution
            FROM agent_metrics
            WHERE metric_date >= $1 AND metric_hour IS NULL
            ORDER BY metric_date
        """, today - timedelta(days=7))
        
        sentiment_trend_data = [
            {
                "date": r['metric_date'].isoformat(),
                "distribution": r['sentiment_distribution']
            }
            for r in sentiment_trend
        ]
        
        # Channel performance
        channel_perf = await conn.fetch("""
            SELECT
                original_channel as channel,
                COUNT(*) as conversations,
                AVG(EXTRACT(EPOCH FROM (last_message_at - created_at))) as avg_duration
            FROM conversations
            WHERE DATE(created_at) >= $1
            GROUP BY original_channel
        """, week_start)
        
        channel_performance = {
            r['channel']: {
                "conversations": r['conversations'],
                "avg_duration_seconds": round(r['avg_duration'] or 0, 2)
            }
            for r in channel_perf
        }
        
        # Recent escalations
        recent_esc = await conn.fetch("""
            SELECT
                e.id as escalation_id,
                e.ticket_id,
                e.escalation_level,
                e.reason,
                e.created_at,
                c.name as customer_name
            FROM escalations e
            JOIN tickets t ON e.ticket_id = t.id
            JOIN conversations c ON t.conversation_id = c.id
            ORDER BY e.created_at DESC
            LIMIT 5
        """)
        
        recent_escalations = [
            {
                "escalation_id": r['escalation_id'],
                "ticket_id": r['ticket_id'],
                "level": r['escalation_level'],
                "reason": r['reason'][:100],
                "customer": r['customer_name'],
                "created_at": r['created_at'].isoformat()
            }
            for r in recent_esc
        ]
        
        # Build dashboard
        dashboard = DashboardMetrics(
            timestamp=now.isoformat(),
            today_stats={
                "conversations": today_stats['conversations'] or 0,
                "messages": today_stats['messages'] or 0,
                "tickets": today_stats['tickets'] or 0,
                "escalations": today_stats['escalations'] or 0,
                "avg_response_time_seconds": round(today_stats['avg_response_time'] or 0, 2)
            },
            this_week_stats={
                "conversations": week_stats['conversations'] or 0,
                "messages": week_stats['messages'] or 0,
                "tickets": week_stats['tickets'] or 0,
                "escalations": week_stats['escalations'] or 0
            },
            this_month_stats={
                "conversations": month_stats['conversations'] or 0,
                "messages": month_stats['messages'] or 0,
                "tickets": month_stats['tickets'] or 0,
                "escalations": month_stats['escalations'] or 0
            },
            sentiment_trend=sentiment_trend_data,
            channel_performance=channel_performance,
            top_agents=[],  # Would require user tracking
            recent_escalations=recent_escalations
        )
        
        return dashboard.dict()


@router.get(
    "/trends",
    response_model=Dict[str, Any],
    summary="Sentiment Trends",
    description="Get sentiment trends over time"
)
async def get_sentiment_trends(
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    db_pool: DatabasePool = Depends(lambda: DatabasePool())
) -> Dict[str, Any]:
    """
    Get sentiment trends over specified period.
    
    Args:
        days: Number of days to analyze (1-90)
        
    Returns:
        Sentiment trend data with daily breakdown
    """
    start_date = datetime.now().date() - timedelta(days=days)
    
    async with db_pool.acquire() as conn:
        trends = await conn.fetch("""
            SELECT metric_date, sentiment_distribution, ai_resolution_rate, escalation_rate
            FROM agent_metrics
            WHERE metric_date >= $1 AND metric_hour IS NULL
            ORDER BY metric_date
        """, start_date)
        
        trend_data = [
            {
                "date": r['metric_date'].isoformat(),
                "sentiment": r['sentiment_distribution'],
                "ai_resolution_rate": float(r['ai_resolution_rate']) if r['ai_resolution_rate'] else 0,
                "escalation_rate": float(r['escalation_rate']) if r['escalation_rate'] else 0
            }
            for r in trends
        ]
        
        # Calculate overall trend
        if len(trend_data) >= 2:
            first_ai_rate = trend_data[0]['ai_resolution_rate']
            last_ai_rate = trend_data[-1]['ai_resolution_rate']
            ai_trend = "improving" if last_ai_rate > first_ai_rate else "declining"
        else:
            ai_trend = "stable"
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": datetime.now().date().isoformat(),
                "days": days
            },
            "trend": trend_data,
            "summary": {
                "ai_resolution_trend": ai_trend,
                "data_points": len(trend_data)
            }
        }
