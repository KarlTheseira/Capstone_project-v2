#!/usr/bin/env python3
"""
FlashStudio Video Management Script

Quick script to update homepage videos without using the admin interface.
Run this script to change your homepage videos directly.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import app, db
from models import Product
from datetime import datetime
import shutil

def update_hero_video(video_path):
    """Update the main hero background video"""
    
    try:
        # Copy the new video to the hero location
        hero_path = 'static/video/hero.mp4'
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(hero_path), exist_ok=True)
        
        # Copy the file
        shutil.copy2(video_path, hero_path)
        
        print(f"✅ Hero video updated successfully!")
        print(f"   New video: {video_path} -> {hero_path}")
        
    except Exception as e:
        print(f"❌ Error updating hero video: {e}")

def list_featured_videos():
    """List current featured videos"""
    
    with app.app_context():
        featured = Product.query.filter_by(featured=True).all()
        
        print("\n🎬 Current Featured Videos:")
        print("=" * 50)
        
        for i, video in enumerate(featured, 1):
            print(f"{i}. {video.title}")
            print(f"   Description: {video.description}")
            print(f"   Video file: {video.video_key}")
            print(f"   Thumbnail: {video.video_thumbnail}")
            print(f"   Duration: {video.duration_display}")
            print(f"   Client: {video.client_name}")
            print("")

def update_featured_video(video_id, **updates):
    """Update a specific featured video"""
    
    with app.app_context():
        video = Product.query.get(video_id)
        
        if not video:
            print(f"❌ Video with ID {video_id} not found")
            return
        
        # Update fields
        for field, value in updates.items():
            if hasattr(video, field):
                setattr(video, field, value)
                print(f"   Updated {field}: {value}")
        
        db.session.commit()
        print(f"✅ Updated '{video.title}' successfully!")

def add_new_featured_video(title, description="", video_file="", thumbnail_file="", client_name="", duration=120):
    """Add a new featured video"""
    
    with app.app_context():
        # Check if we have too many featured videos
        current_count = Product.query.filter_by(featured=True).count()
        if current_count >= 6:
            print("❌ Maximum of 6 featured videos allowed. Remove one first.")
            return
        
        # Create new video product
        new_video = Product(
            title=title,
            description=description,
            price_cents=0,
            media_key=video_file,
            video_key=video_file,
            video_thumbnail=thumbnail_file,
            video_duration=duration,
            client_name=client_name,
            featured=True,
            stock=1,
            category='portfolio',
            created_at=datetime.utcnow()
        )
        
        # Copy video files if provided
        if video_file and os.path.exists(video_file):
            video_filename = f"{title.lower().replace(' ', '_')}.mp4"
            video_dest = f"static/uploads/{video_filename}"
            shutil.copy2(video_file, video_dest)
            new_video.video_key = video_filename
            new_video.media_key = video_filename
            print(f"   Copied video: {video_file} -> {video_dest}")
        
        if thumbnail_file and os.path.exists(thumbnail_file):
            thumb_filename = f"{title.lower().replace(' ', '_')}_preview.jpg"
            thumb_dest = f"static/uploads/{thumb_filename}"
            shutil.copy2(thumbnail_file, thumb_dest)
            new_video.video_thumbnail = thumb_filename
            print(f"   Copied thumbnail: {thumbnail_file} -> {thumb_dest}")
        
        db.session.add(new_video)
        db.session.commit()
        
        print(f"✅ Added new featured video: '{title}'")
        print(f"   ID: {new_video.id}")

def remove_featured_video(video_id):
    """Remove a video from featured videos"""
    
    with app.app_context():
        video = Product.query.get(video_id)
        
        if not video:
            print(f"❌ Video with ID {video_id} not found")
            return
        
        video.featured = False
        db.session.commit()
        
        print(f"✅ Removed '{video.title}' from featured videos")

def main():
    """Main menu for video management"""
    
    print("🎬 FlashStudio Video Management")
    print("=" * 40)
    print()
    print("What would you like to do?")
    print()
    print("1. List current featured videos")
    print("2. Update hero background video")
    print("3. Add new featured video")
    print("4. Update existing featured video")
    print("5. Remove featured video")
    print("6. Exit")
    print()
    
    try:
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == "1":
            list_featured_videos()
        
        elif choice == "2":
            video_path = input("Enter path to new hero video: ").strip()
            if os.path.exists(video_path):
                update_hero_video(video_path)
            else:
                print(f"❌ File not found: {video_path}")
        
        elif choice == "3":
            print("\nAdd New Featured Video:")
            title = input("Title: ").strip()
            description = input("Description: ").strip()
            video_file = input("Video file path (optional): ").strip()
            thumbnail_file = input("Thumbnail file path (optional): ").strip()
            client_name = input("Client name (optional): ").strip()
            
            duration_str = input("Duration in seconds (default: 120): ").strip()
            duration = int(duration_str) if duration_str.isdigit() else 120
            
            add_new_featured_video(
                title=title,
                description=description,
                video_file=video_file if video_file else "",
                thumbnail_file=thumbnail_file if thumbnail_file else "",
                client_name=client_name,
                duration=duration
            )
        
        elif choice == "4":
            list_featured_videos()
            video_id = input("\nEnter video ID to update: ").strip()
            
            if video_id.isdigit():
                print("Enter new values (press Enter to skip):")
                updates = {}
                
                title = input("Title: ").strip()
                if title: updates['title'] = title
                
                description = input("Description: ").strip()
                if description: updates['description'] = description
                
                client_name = input("Client name: ").strip()
                if client_name: updates['client_name'] = client_name
                
                if updates:
                    update_featured_video(int(video_id), **updates)
                else:
                    print("No updates provided.")
            else:
                print("❌ Invalid ID")
        
        elif choice == "5":
            list_featured_videos()
            video_id = input("\nEnter video ID to remove: ").strip()
            
            if video_id.isdigit():
                confirm = input(f"Remove video ID {video_id} from homepage? (y/N): ").strip().lower()
                if confirm == 'y':
                    remove_featured_video(int(video_id))
                else:
                    print("Cancelled.")
            else:
                print("❌ Invalid ID")
        
        elif choice == "6":
            print("👋 Goodbye!")
            return
        
        else:
            print("❌ Invalid choice")
        
        # Ask if they want to continue
        print()
        continue_choice = input("Do you want to perform another action? (y/N): ").strip().lower()
        if continue_choice == 'y':
            main()
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()