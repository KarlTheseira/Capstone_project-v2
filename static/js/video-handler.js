// Video handler for Flash Studio
document.addEventListener('DOMContentLoaded', function() {
    console.log('Video handler loaded');
    
    // Enhanced video error handling
    const videos = document.querySelectorAll('video');
    videos.forEach(video => {
        video.addEventListener('loadstart', function() {
            console.log('Video loading started:', this.src);
        });
        
        video.addEventListener('canplay', function() {
            console.log('Video can play:', this.src);
        });
        
        video.addEventListener('error', function(e) {
            console.error('Video error:', this.src, e);
            
            // Try to provide helpful error messages
            const error = this.error;
            let errorMessage = 'Video playback error';
            
            if (error) {
                switch(error.code) {
                    case error.MEDIA_ERR_ABORTED:
                        errorMessage = 'Video playback was aborted';
                        break;
                    case error.MEDIA_ERR_NETWORK:
                        errorMessage = 'Network error while loading video';
                        break;
                    case error.MEDIA_ERR_DECODE:
                        errorMessage = 'Video format not supported';
                        break;
                    case error.MEDIA_ERR_SRC_NOT_SUPPORTED:
                        errorMessage = 'Video source not supported';
                        break;
                }
            }
            
            // Show error message to user
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-warning mt-2';
            errorDiv.innerHTML = `<i class="bi bi-exclamation-triangle"></i> ${errorMessage}`;
            
            if (this.parentNode) {
                this.parentNode.appendChild(errorDiv);
            }
        });
    });
});