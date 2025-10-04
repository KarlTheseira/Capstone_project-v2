import cv2
import numpy as np
import os

def create_video(filename, config=None):
    """
    Create a video with custom settings.
    
    Args:
        filename (str): Output video file path
        config (dict): Video configuration with options:
            - duration (int): Video duration in seconds (default: 10)
            - fps (int): Frames per second (default: 30)
            - size (tuple): Video dimensions (width, height) (default: 1920x1080)
            - style (str): Animation style ('gradient', 'particles', 'waves') (default: 'gradient')
            - text (str): Text to display (optional)
            - colors (dict): Color configuration for the animation
    """
    # Default configuration
    default_config = {
        'duration': 10,
        'fps': 30,
        'size': (1920, 1080),
        'style': 'gradient',
        'text': None,
        'colors': {
            'primary': (64, 32, 16),    # Dark blue (BGR)
            'secondary': (32, 16, 8),    # Darker blue
            'text': (255, 255, 255),     # White
            'shadow': (0, 0, 0)          # Black
        }
    }
    
    # Merge with provided config
    if config is None:
        config = {}
    config = {**default_config, **config}
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, config['fps'], config['size'])
    
    try:
        total_frames = config['duration'] * config['fps']
        
        for i in range(total_frames):
            t = i / total_frames  # Normalized time from 0 to 1
            
            # Create base frame
            if config['style'] == 'gradient':
                frame = create_gradient_frame(t, config)
            elif config['style'] == 'particles':
                frame = create_particle_frame(t, config)
            elif config['style'] == 'waves':
                frame = create_wave_frame(t, config)
            else:
                frame = create_gradient_frame(t, config)
            
            # Add text if specified
            if config['text']:
                add_text_to_frame(frame, config['text'], config['colors'])
            
            out.write(frame)
            
        return True
        
    except Exception as e:
        return False
        
    finally:
        out.release()

def create_gradient_frame(t, config):
    """Create a frame with moving gradient effect."""
    size = config['size']
    x = np.linspace(0, 1, size[0])
    y = np.linspace(0, 1, size[1])
    X, Y = np.meshgrid(x, y)
    
    # Create moving gradient
    angle = t * 2 * np.pi
    gradient = np.sin(X * np.cos(angle) * 5 + Y * np.sin(angle) * 5 + t * 2)
    gradient = (gradient + 1) / 2  # Normalize to 0-1
    
    # Apply colors
    b = gradient * config['colors']['primary'][0]
    g = gradient * config['colors']['primary'][1]
    r = gradient * config['colors']['primary'][2]
    
    return np.stack([b, g, r], axis=2).astype(np.uint8)

def create_particle_frame(t, config):
    """Create a frame with particle effect."""
    size = config['size']
    frame = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    
    # Number of particles
    n_particles = 50
    
    # Create random positions
    xs = np.random.randint(0, size[0], n_particles)
    ys = np.random.randint(0, size[1], n_particles)
    
    # Move particles
    for i in range(n_particles):
        x = int(xs[i] + np.sin(t * 2 * np.pi + i) * 50) % size[0]
        y = int(ys[i] + np.cos(t * 2 * np.pi + i) * 50) % size[1]
        
        # Draw particle
        cv2.circle(frame, (x, y), 5, config['colors']['primary'], -1)
        
    return frame

def create_wave_frame(t, config):
    """Create a frame with wave effect."""
    size = config['size']
    x = np.linspace(0, 1, size[0])
    y = np.linspace(0, 1, size[1])
    X, Y = np.meshgrid(x, y)
    
    # Create waves
    waves = np.sin(X * 10 + t * 2 * np.pi) * np.cos(Y * 10 - t * 2 * np.pi)
    waves = (waves + 1) / 2  # Normalize to 0-1
    
    # Apply colors
    b = waves * config['colors']['primary'][0]
    g = waves * config['colors']['primary'][1]
    r = waves * config['colors']['primary'][2]
    
    return np.stack([b, g, r], axis=2).astype(np.uint8)

def add_text_to_frame(frame, text, colors):
    """Add text with shadow to frame."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 2
    thickness = 3
    
    # Get text size
    textsize = cv2.getTextSize(text, font, font_scale, thickness)[0]
    
    # Center coordinates
    textX = (frame.shape[1] - textsize[0]) // 2
    textY = (frame.shape[0] + textsize[1]) // 2
    
    # Add shadow
    cv2.putText(frame, text, 
                (textX + 2, textY + 2), 
                font, font_scale, 
                colors['shadow'], 
                thickness)
    
    # Add main text
    cv2.putText(frame, text, 
                (textX, textY), 
                font, font_scale, 
                colors['text'], 
                thickness)