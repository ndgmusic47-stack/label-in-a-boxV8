"""
Analytics Engine for Label-in-a-Box v4
Tracks and analyzes streams, revenue, engagement, and performance metrics
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Manages analytics tracking and reporting for independent artists.
    Tracks streams, revenue, engagement, and provides AI insights.
    """
    
    def __init__(self):
        self.platforms = ["Spotify", "Apple Music", "YouTube", "SoundCloud", "TikTok", "Instagram"]
    
    def get_project_analytics(self, project_memory) -> Dict:
        """
        Get comprehensive analytics for a specific project.
        
        Args:
            project_memory: ProjectMemory instance for the project
            
        Returns:
            Dict with streams, revenue, engagement, and platform breakdowns
        """
        try:
            analytics_data = project_memory.project_data.get("analytics", {})
            
            # Add platform breakdown if not present
            if "platform_breakdown" not in analytics_data:
                analytics_data["platform_breakdown"] = self._generate_platform_breakdown(
                    analytics_data.get("streams", 0)
                )
            
            # Add growth trends if not present
            if "growth_trends" not in analytics_data:
                analytics_data["growth_trends"] = self._generate_growth_trends(
                    analytics_data.get("streams", 0)
                )
            
            # Calculate derived metrics
            total_streams = analytics_data.get("streams", 0)
            total_revenue = analytics_data.get("revenue", 0.0)
            
            analytics_data["avg_revenue_per_stream"] = (
                total_revenue / total_streams if total_streams > 0 else 0.0
            )
            
            analytics_data["engagement_rate"] = self._calculate_engagement_rate(
                total_streams,
                analytics_data.get("saves", 0),
                analytics_data.get("shares", 0)
            )
            
            return {
                "status": "ready",
                "analytics": analytics_data,
                "insights": self._generate_insights(analytics_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to get project analytics: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_dashboard_analytics(self, all_projects: List) -> Dict:
        """
        Get aggregate analytics across all projects.
        
        Args:
            all_projects: List of all project metadata dicts
            
        Returns:
            Dict with aggregate metrics and top performers
        """
        try:
            total_streams = 0
            total_revenue = 0.0
            total_saves = 0
            total_shares = 0
            platform_totals = {platform: 0 for platform in self.platforms}
            
            top_tracks = []
            
            for project in all_projects:
                analytics = project.get("analytics", {})
                streams = analytics.get("streams", 0)
                revenue = analytics.get("revenue", 0.0)
                
                total_streams += streams
                total_revenue += revenue
                total_saves += analytics.get("saves", 0)
                total_shares += analytics.get("shares", 0)
                
                # Platform breakdown
                platform_breakdown = analytics.get("platform_breakdown", {})
                for platform, count in platform_breakdown.items():
                    if platform in platform_totals:
                        platform_totals[platform] += count
                
                # Track performance
                track_title = project.get("metadata", {}).get("track_title", "Untitled")
                if track_title and streams > 0:
                    top_tracks.append({
                        "title": track_title,
                        "streams": streams,
                        "revenue": revenue,
                        "session_id": project.get("session_id")
                    })
            
            # Sort top tracks
            top_tracks.sort(key=lambda x: x["streams"], reverse=True)
            top_tracks = top_tracks[:10]  # Top 10
            
            return {
                "status": "ready",
                "dashboard": {
                    "total_streams": total_streams,
                    "total_revenue": total_revenue,
                    "total_saves": total_saves,
                    "total_shares": total_shares,
                    "platform_breakdown": platform_totals,
                    "top_tracks": top_tracks,
                    "total_projects": len(all_projects),
                    "avg_revenue_per_stream": (
                        total_revenue / total_streams if total_streams > 0 else 0.0
                    )
                },
                "insights": self._generate_dashboard_insights({
                    "total_streams": total_streams,
                    "total_revenue": total_revenue,
                    "platform_breakdown": platform_totals,
                    "top_tracks": top_tracks
                })
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard analytics: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def update_analytics(
        self,
        project_memory,
        streams: Optional[int] = None,
        revenue: Optional[float] = None,
        saves: Optional[int] = None,
        shares: Optional[int] = None,
        platform_data: Optional[Dict] = None
    ) -> Dict:
        """
        Update analytics metrics for a project.
        
        Args:
            project_memory: ProjectMemory instance
            streams: Number of streams to add
            revenue: Revenue to add
            saves: Number of saves to add
            shares: Number of shares to add
            platform_data: Platform-specific data {platform: stream_count}
            
        Returns:
            Updated analytics dict
        """
        try:
            current_analytics = project_memory.project_data.get("analytics", {
                "streams": 0,
                "saves": 0,
                "shares": 0,
                "revenue": 0.0,
                "platform_breakdown": {},
                "last_updated": datetime.now().isoformat()
            })
            
            # Update metrics
            if streams is not None:
                current_analytics["streams"] += streams
            if revenue is not None:
                current_analytics["revenue"] += revenue
            if saves is not None:
                current_analytics["saves"] += saves
            if shares is not None:
                current_analytics["shares"] += shares
            
            # Update platform breakdown
            if platform_data:
                platform_breakdown = current_analytics.get("platform_breakdown", {})
                for platform, count in platform_data.items():
                    platform_breakdown[platform] = platform_breakdown.get(platform, 0) + count
                current_analytics["platform_breakdown"] = platform_breakdown
            
            current_analytics["last_updated"] = datetime.now().isoformat()
            
            # Save back to project memory
            project_memory.project_data["analytics"] = current_analytics
            project_memory.save()
            
            return {
                "status": "updated",
                "analytics": current_analytics
            }
            
        except Exception as e:
            logger.error(f"Failed to update analytics: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _generate_platform_breakdown(self, total_streams: int) -> Dict:
        """Generate realistic platform distribution for streams"""
        if total_streams == 0:
            return {platform: 0 for platform in self.platforms}
        
        # Realistic distribution percentages
        distribution = {
            "Spotify": 0.45,
            "Apple Music": 0.25,
            "YouTube": 0.15,
            "SoundCloud": 0.08,
            "TikTok": 0.05,
            "Instagram": 0.02
        }
        
        breakdown = {}
        remaining = total_streams
        
        for platform, percentage in distribution.items():
            count = int(total_streams * percentage)
            breakdown[platform] = count
            remaining -= count
        
        # Add remaining to Spotify
        breakdown["Spotify"] += remaining
        
        return breakdown
    
    def _generate_growth_trends(self, total_streams: int) -> List:
        """Generate growth trend data for the last 7 days"""
        trends = []
        base_streams = total_streams // 7 if total_streams > 0 else 0
        
        for i in range(7):
            date = datetime.now() - timedelta(days=6-i)
            # Add some variance
            variance = random.uniform(0.8, 1.2)
            daily_streams = int(base_streams * variance)
            
            trends.append({
                "date": date.strftime("%Y-%m-%d"),
                "streams": daily_streams,
                "revenue": daily_streams * 0.004  # ~$0.004 per stream
            })
        
        return trends
    
    def _calculate_engagement_rate(
        self,
        streams: int,
        saves: int,
        shares: int
    ) -> float:
        """Calculate engagement rate based on saves and shares"""
        if streams == 0:
            return 0.0
        
        engagement_actions = saves + (shares * 2)  # Shares count more
        return (engagement_actions / streams) * 100
    
    def _generate_insights(self, analytics: Dict) -> List[str]:
        """Generate AI insights based on analytics data"""
        insights = []
        
        streams = analytics.get("streams", 0)
        revenue = analytics.get("revenue", 0.0)
        engagement_rate = analytics.get("engagement_rate", 0.0)
        platform_breakdown = analytics.get("platform_breakdown", {})
        
        # Stream milestone insights
        if streams >= 10000:
            insights.append(f"🎉 Congrats on {streams:,} streams! You're building serious momentum.")
        elif streams >= 1000:
            insights.append(f"📈 {streams:,} streams and counting—keep pushing!")
        elif streams > 0:
            insights.append(f"🚀 You're at {streams:,} streams. Stay consistent to hit 1K!")
        
        # Revenue insights
        if revenue >= 100:
            insights.append(f"💰 You've earned ${revenue:.2f}! Consider investing in promotion.")
        elif revenue > 0:
            insights.append(f"💵 ${revenue:.2f} in revenue—every stream counts!")
        
        # Engagement insights
        if engagement_rate > 5:
            insights.append(f"🔥 {engagement_rate:.1f}% engagement rate is excellent!")
        elif engagement_rate > 2:
            insights.append(f"👍 {engagement_rate:.1f}% engagement—people are vibing with your music.")
        
        # Platform insights
        if platform_breakdown:
            top_platform = max(platform_breakdown.items(), key=lambda x: x[1])
            if top_platform[1] > 0:
                insights.append(f"📱 {top_platform[0]} is your strongest platform ({top_platform[1]:,} streams).")
        
        if not insights:
            insights.append("📊 Start tracking your music's performance to unlock insights!")
        
        return insights
    
    def _generate_dashboard_insights(self, dashboard_data: Dict) -> List[str]:
        """Generate insights for the overall dashboard"""
        insights = []
        
        total_streams = dashboard_data.get("total_streams", 0)
        total_revenue = dashboard_data.get("total_revenue", 0.0)
        top_tracks = dashboard_data.get("top_tracks", [])
        platform_breakdown = dashboard_data.get("platform_breakdown", {})
        
        # Overall performance
        if total_streams >= 50000:
            insights.append(f"🌟 {total_streams:,} total streams across all tracks! You're an artist on the rise.")
        elif total_streams >= 10000:
            insights.append(f"📈 {total_streams:,} total streams! Your catalog is growing.")
        
        # Revenue milestone
        if total_revenue >= 500:
            insights.append(f"💎 ${total_revenue:.2f} total revenue! Your music is paying off.")
        elif total_revenue >= 100:
            insights.append(f"💰 ${total_revenue:.2f} earned so far—keep releasing!")
        
        # Top track insight
        if top_tracks and len(top_tracks) > 0:
            top_track = top_tracks[0]
            insights.append(f"🏆 '{top_track['title']}' is your top track with {top_track['streams']:,} streams!")
        
        # Platform distribution
        if platform_breakdown:
            total_platform_streams = sum(platform_breakdown.values())
            if total_platform_streams > 0:
                diversification = len([v for v in platform_breakdown.values() if v > 0])
                if diversification >= 5:
                    insights.append(f"🌐 You're active on {diversification} platforms—great distribution!")
        
        if not insights:
            insights.append("🎯 Release more tracks to start building your analytics dashboard!")
        
        return insights
    
    def generate_voice_response(self, insights: List[str], analytics: Dict) -> str:
        """
        Generate a voice response from Pulse (Analytics) based on insights.
        """
        streams = analytics.get("streams", 0)
        revenue = analytics.get("revenue", 0.0)
        
        if streams == 0:
            return "Ready to track your performance? Once your music goes live, I'll show you exactly how it's performing across all platforms."
        
        # Pick a top insight
        if insights and len(insights) > 0:
            top_insight = insights[0]
            return f"{top_insight} Let's keep building on this momentum!"
        
        return f"You've got {streams:,} streams and ${revenue:.2f} in revenue. Here's what the data says about your audience."
