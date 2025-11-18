"""
Social Media Scheduler
Handles multi-platform post scheduling, formatting, and content optimization.
"""

import os
import json
import requests
import httpx
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SocialScheduler:
    """
    Multi-platform social media scheduler with AI-powered content optimization.
    Supports Instagram, Twitter/X, TikTok, Facebook, and YouTube.
    """
    
    PLATFORMS = {
        "instagram": {
            "name": "Instagram",
            "char_limit": 2200,
            "hashtag_limit": 30,
            "supports_video": True,
            "supports_images": True,
            "aspect_ratios": ["1:1", "4:5", "9:16"]
        },
        "twitter": {
            "name": "Twitter/X",
            "char_limit": 280,
            "hashtag_limit": 3,
            "supports_video": True,
            "supports_images": True,
            "aspect_ratios": ["16:9", "1:1"]
        },
        "tiktok": {
            "name": "TikTok",
            "char_limit": 150,
            "hashtag_limit": 5,
            "supports_video": True,
            "supports_images": False,
            "aspect_ratios": ["9:16"]
        },
        "facebook": {
            "name": "Facebook",
            "char_limit": 63206,
            "hashtag_limit": 3,
            "supports_video": True,
            "supports_images": True,
            "aspect_ratios": ["16:9", "1:1", "4:5"]
        },
        "youtube": {
            "name": "YouTube",
            "char_limit": 5000,
            "hashtag_limit": 15,
            "supports_video": True,
            "supports_images": False,
            "aspect_ratios": ["16:9", "9:16"]
        }
    }
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.schedule_dir = f"sessions/{session_id}/social_schedule"
        os.makedirs(self.schedule_dir, exist_ok=True)
    
    def get_platform_info(self, platform: str) -> Dict:
        """
        Get information about a specific platform's requirements.
        """
        if platform not in self.PLATFORMS:
            return {
                "success": False,
                "error": "unknown_platform",
                "supported_platforms": list(self.PLATFORMS.keys())
            }
        
        return {
            "success": True,
            "platform": platform,
            **self.PLATFORMS[platform]
        }
    
    def optimize_content_for_platform(
        self,
        content: str,
        platform: str,
        hashtags: Optional[List[str]] = None
    ) -> Dict:
        """
        Optimize content for a specific platform's requirements.
        Truncates text, limits hashtags, and provides platform-specific suggestions.
        """
        if platform not in self.PLATFORMS:
            return {
                "success": False,
                "error": "unknown_platform"
            }
        
        platform_info = self.PLATFORMS[platform]
        char_limit = platform_info["char_limit"]
        hashtag_limit = platform_info["hashtag_limit"]
        
        # Process hashtags
        optimized_hashtags = []
        if hashtags:
            optimized_hashtags = hashtags[:hashtag_limit]
        
        # Build hashtag string
        hashtag_string = " ".join(optimized_hashtags) if optimized_hashtags else ""
        
        # Calculate available space for content
        available_chars = char_limit - len(hashtag_string) - 2  # -2 for spacing
        
        # Truncate content if needed
        if len(content) > available_chars:
            optimized_content = content[:available_chars-3] + "..."
            truncated = True
        else:
            optimized_content = content
            truncated = False
        
        # Build final post
        final_post = f"{optimized_content}\n\n{hashtag_string}".strip()
        
        return {
            "success": True,
            "platform": platform,
            "original_length": len(content),
            "optimized_content": optimized_content,
            "hashtags": optimized_hashtags,
            "final_post": final_post,
            "character_count": len(final_post),
            "character_limit": char_limit,
            "truncated": truncated,
            "suggestions": self._get_platform_suggestions(platform)
        }
    
    def _get_platform_suggestions(self, platform: str) -> List[str]:
        """
        Get AI-powered posting suggestions for each platform.
        """
        suggestions = {
            "instagram": [
                "Post between 6-9 AM or 5-7 PM for maximum engagement",
                "Use all available hashtags for discovery",
                "Add a call-to-action in your caption",
                "Share to Stories for extra reach"
            ],
            "twitter": [
                "Tweet during peak hours: 8-10 AM and 6-9 PM",
                "Keep hashtags minimal (1-3) for better engagement",
                "Use line breaks to make text scannable",
                "Tag relevant accounts to increase visibility"
            ],
            "tiktok": [
                "Post between 6-10 AM or 7-11 PM EST",
                "Use trending sounds to boost algorithm",
                "Hook viewers in first 3 seconds",
                "Keep captions short and engaging"
            ],
            "facebook": [
                "Post between 1-4 PM on weekdays",
                "Ask questions to drive comments",
                "Video posts get 6x more engagement",
                "Share to Groups for targeted reach"
            ],
            "youtube": [
                "Upload at 2-4 PM EST on weekdays",
                "Front-load important keywords in description",
                "Use 5-8 relevant hashtags",
                "Create custom thumbnail for click-through"
            ]
        }
        
        return suggestions.get(platform, ["Post during peak engagement hours"])
    
    def schedule_post(
        self,
        platform: str,
        content: str,
        scheduled_time: str,
        media_url: Optional[str] = None,
        hashtags: Optional[List[str]] = None
    ) -> Dict:
        """
        Schedule a post for a specific platform and time.
        
        Args:
            platform: Social media platform
            content: Post content/caption
            scheduled_time: ISO format datetime string
            media_url: Optional media file URL
            hashtags: Optional list of hashtags
            
        Returns:
            Scheduling result with post ID and confirmation
        """
        # Optimize content for platform
        optimized = self.optimize_content_for_platform(content, platform, hashtags)
        
        if not optimized.get("success"):
            return optimized
        
        # Parse scheduled time
        try:
            schedule_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
        except ValueError:
            return {
                "success": False,
                "error": "invalid_datetime",
                "message": "Scheduled time must be in ISO format"
            }
        
        # Create post ID
        post_id = f"{platform}_{schedule_dt.strftime('%Y%m%d_%H%M%S')}"
        
        # Save scheduled post
        post_data = {
            "post_id": post_id,
            "platform": platform,
            "content": optimized["optimized_content"],
            "hashtags": optimized["hashtags"],
            "final_post": optimized["final_post"],
            "media_url": media_url,
            "scheduled_time": scheduled_time,
            "created_at": datetime.now().isoformat(),
            "status": "scheduled",
            "character_count": optimized["character_count"]
        }
        
        # Save to file
        post_file = os.path.join(self.schedule_dir, f"{post_id}.json")
        with open(post_file, 'w') as f:
            json.dump(post_data, f, indent=2)
        
        return {
            "success": True,
            "post_id": post_id,
            "platform": platform,
            "scheduled_time": scheduled_time,
            "character_count": optimized["character_count"],
            "message": f"Post scheduled for {self.PLATFORMS[platform]['name']} at {schedule_dt.strftime('%I:%M %p on %B %d, %Y')}",
            "suggestions": optimized["suggestions"]
        }
    
    async def schedule_with_getlate(
        self,
        platform: str,
        content: str,
        scheduled_time: str,
        api_key: str,
        media_url: Optional[str] = None,
        hashtags: Optional[List[str]] = None
    ) -> Dict:
        """
        Schedule a post using GetLate.dev API.
        
        Args:
            platform: Social media platform (tiktok, shorts, reels)
            content: Post content/caption
            scheduled_time: ISO format datetime string
            api_key: GetLate.dev API key
            media_url: Optional media file URL
            hashtags: Optional list of hashtags
            
        Returns:
            Scheduling result with post ID and confirmation
        """
        try:
            # Map platform names to GetLate format
            platform_map = {
                "tiktok": "tiktok",
                "shorts": "youtube",  # YouTube Shorts
                "reels": "instagram"   # Instagram Reels
            }
            
            getlate_platform = platform_map.get(platform.lower(), platform.lower())
            
            # Optimize content for platform
            optimized = self.optimize_content_for_platform(content, platform, hashtags)
            if not optimized.get("success"):
                return optimized
            
            # Prepare GetLate API request
            # Note: Adjust API endpoint and payload structure based on GetLate.dev documentation
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "platform": getlate_platform,
                "content": optimized["final_post"],
                "scheduled_at": scheduled_time,
            }
            
            if media_url:
                payload["media_url"] = media_url
            
            # Call GetLate.dev API
            # Update this URL based on actual GetLate.dev API documentation
            api_url = "https://api.getlate.dev/v1/posts"
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(api_url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                
                # Extract post ID from GetLate response
                post_id = result.get("id") or result.get("post_id") or f"getlate_{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Save to local JSON for backup
                post_data = {
                    "post_id": post_id,
                    "platform": platform,
                    "content": optimized["final_post"],
                    "hashtags": optimized["hashtags"],
                    "scheduled_time": scheduled_time,
                    "created_at": datetime.now().isoformat(),
                    "status": "scheduled",
                    "provider": "getlate",
                    "getlate_response": result
                }
                
                post_file = os.path.join(self.schedule_dir, f"{post_id}.json")
                os.makedirs(self.schedule_dir, exist_ok=True)
                with open(post_file, 'w') as f:
                    json.dump(post_data, f, indent=2)
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "platform": platform,
                    "scheduled_time": scheduled_time,
                    "provider": "getlate",
                    "message": f"Post scheduled on {platform} via GetLate.dev"
                }
                
            except httpx.RequestError as e:
                logger.error(f"GetLate API request failed: {e}")
                return {
                    "success": False,
                    "error": f"GetLate API error: {str(e)}",
                    "message": "Failed to schedule post via GetLate.dev"
                }
                
        except Exception as e:
            logger.error(f"GetLate scheduling failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "GetLate scheduling encountered an error"
            }
    
    def get_scheduled_posts(self, platform: Optional[str] = None) -> Dict:
        """
        Get all scheduled posts, optionally filtered by platform.
        """
        try:
            # Load all scheduled posts
            posts = []
            
            if os.path.exists(self.schedule_dir):
                for filename in os.listdir(self.schedule_dir):
                    if filename.endswith('.json'):
                        with open(os.path.join(self.schedule_dir, filename), 'r') as f:
                            post_data = json.load(f)
                            
                            # Filter by platform if specified
                            if platform is None or post_data.get('platform') == platform:
                                posts.append(post_data)
            
            # Sort by scheduled time
            posts.sort(key=lambda x: x.get('scheduled_time', ''))
            
            return {
                "success": True,
                "total_posts": len(posts),
                "posts": posts,
                "platforms": list(set(p['platform'] for p in posts))
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "posts": []
            }
    
    def cancel_post(self, post_id: str) -> Dict:
        """
        Cancel a scheduled post.
        """
        try:
            post_file = os.path.join(self.schedule_dir, f"{post_id}.json")
            
            if not os.path.exists(post_file):
                return {
                    "success": False,
                    "error": "post_not_found",
                    "message": "Scheduled post not found"
                }
            
            # Load post data
            with open(post_file, 'r') as f:
                post_data = json.load(f)
            
            # Update status
            post_data['status'] = 'cancelled'
            post_data['cancelled_at'] = datetime.now().isoformat()
            
            # Save updated data
            with open(post_file, 'w') as f:
                json.dump(post_data, f, indent=2)
            
            return {
                "success": True,
                "post_id": post_id,
                "message": "Post cancelled successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_optimal_posting_times(self, platform: str, timezone: str = "EST") -> Dict:
        """
        Get AI-recommended optimal posting times for a platform.
        """
        # Optimal times by platform (EST)
        optimal_times = {
            "instagram": [
                {"time": "6:00 AM", "reason": "Morning scroll before work"},
                {"time": "12:00 PM", "reason": "Lunch break engagement"},
                {"time": "7:00 PM", "reason": "Peak evening engagement"}
            ],
            "twitter": [
                {"time": "8:00 AM", "reason": "Morning commute"},
                {"time": "12:00 PM", "reason": "Lunch conversations"},
                {"time": "6:00 PM", "reason": "After-work browsing"}
            ],
            "tiktok": [
                {"time": "7:00 AM", "reason": "Before school/work"},
                {"time": "4:00 PM", "reason": "After school"},
                {"time": "9:00 PM", "reason": "Prime scrolling time"}
            ],
            "facebook": [
                {"time": "1:00 PM", "reason": "Midday break"},
                {"time": "3:00 PM", "reason": "Afternoon engagement"},
                {"time": "8:00 PM", "reason": "Evening relaxation"}
            ],
            "youtube": [
                {"time": "2:00 PM", "reason": "Afternoon viewing"},
                {"time": "5:00 PM", "reason": "After-work content"},
                {"time": "9:00 PM", "reason": "Prime viewing time"}
            ]
        }
        
        if platform not in optimal_times:
            return {
                "success": False,
                "error": "unknown_platform"
            }
        
        return {
            "success": True,
            "platform": platform,
            "timezone": timezone,
            "optimal_times": optimal_times[platform],
            "ai_insight": f"These times are when {platform} users are most active and engaged"
        }
