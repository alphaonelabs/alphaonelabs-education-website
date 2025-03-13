class VideoPlayer {
    constructor(options) {
      this.containerId = options.containerId;
      this.videoUrl = options.videoUrl;
      this.videoType = options.videoType || 'auto';
      this.title = options.title || '';
      this.poster = options.poster || '';
      
      this.container = document.getElementById(this.containerId);
      if (!this.container) {
        console.error(`Container with ID ${this.containerId} not found`);
        return;
      }
      
      this.detectVideoType();
      this.createPlayer();
    }
    
    detectVideoType() {
      if (this.videoType !== 'auto') return;
      
      if (this.videoUrl.includes('youtube.com') || this.videoUrl.includes('youtu.be')) {
        this.videoType = 'youtube';
        this.videoId = this.extractYouTubeId(this.videoUrl);
      } else if (this.videoUrl.includes('vimeo.com')) {
        this.videoType = 'vimeo';
        this.videoId = this.extractVimeoId(this.videoUrl);
      } else {
        this.videoType = 'html5';
      }
    }
    
    extractYouTubeId(url) {
      let videoId = '';
      if (url.includes('youtube.com/watch')) {
        const urlParams = new URLSearchParams(new URL(url).search);
        videoId = urlParams.get('v');
      } else if (url.includes('youtu.be/')) {
        videoId = url.split('youtu.be/')[1].split('?')[0];
      }
      return videoId;
    }
    
    extractVimeoId(url) {
      let match = url.match(/vimeo\\.com\\/(?:video\\/)?(\\d+)/);
      return match ? match[1] : '';
    }
    
    createPlayer() {
      this.container.innerHTML = '';
      this.container.classList.add('video-player');
      
      // Add title if provided
      if (this.title) {
        const titleElement = document.createElement('div');
        titleElement.className = 'video-player-title';
        titleElement.textContent = this.title;
        this.container.appendChild(titleElement);
      }
      
      // Create loading indicator
      const loadingElement = document.createElement('div');
      loadingElement.className = 'video-loading';
      loadingElement.innerHTML = '<div class="video-loading-spinner"></div>';
      this.container.appendChild(loadingElement);
      
      // Create player based on video type
      switch (this.videoType) {
        case 'youtube':
          this.createYouTubePlayer();
          break;
        case 'vimeo':
          this.createVimeoPlayer();
          break;
        case 'html5':
        default:
          this.createHTML5Player();
          break;
      }
    }
    
    createYouTubePlayer() {
      if (!this.videoId) {
        this.showError('Invalid YouTube URL');
        return;
      }
      
      // Create iframe for YouTube
      const iframe = document.createElement('iframe');
      iframe.src = `https://www.youtube.com/embed/${this.videoId}?autoplay=0&rel=0&modestbranding=1`;
      iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
      iframe.allowFullscreen = true;
      
      iframe.onload = () => {
        // Remove loading indicator when iframe is loaded
        const loadingElement = this.container.querySelector('.video-loading');
        if (loadingElement) {
          loadingElement.remove();
        }
      };
      
      this.container.appendChild(iframe);
    }
    
    createVimeoPlayer() {
      if (!this.videoId) {
        this.showError('Invalid Vimeo URL');
        return;
      }
      
      // Create iframe for Vimeo
      const iframe = document.createElement('iframe');
      iframe.src = `https://player.vimeo.com/video/${this.videoId}?autoplay=0&title=0&byline=0&portrait=0`;
      iframe.allow = 'autoplay; fullscreen; picture-in-picture';
      iframe.allowFullscreen = true;
      
      iframe.onload = () => {
        // Remove loading indicator when iframe is loaded
        const loadingElement = this.container.querySelector('.video-loading');
        if (loadingElement) {
          loadingElement.remove();
        }
      };
      
      this.container.appendChild(iframe);
    }
    
    createHTML5Player() {
      // Create video element
      const video = document.createElement('video');
      video.controls = true;
      video.preload = 'metadata';
      
      if (this.poster) {
        video.poster = this.poster;
      }
      
      // Create source element
      const source = document.createElement('source');
      source.src = this.videoUrl;
      
      // Try to determine the MIME type from the URL
      const extension = this.videoUrl.split('.').pop().toLowerCase();
      switch (extension) {
        case 'mp4':
          source.type = 'video/mp4';
          break;
        case 'webm':
          source.type = 'video/webm';
          break;
        case 'ogg':
        case 'ogv':
          source.type = 'video/ogg';
          break;
        case 'mov':
          source.type = 'video/quicktime';
          break;
      }
      
      video.appendChild(source);
      
      // Add error handling
      video.onerror = () => {
        this.showError('Video could not be loaded');
      };
      
      // Remove loading indicator when video can play
      video.oncanplay = () => {
        const loadingElement = this.container.querySelector('.video-loading');
        if (loadingElement) {
          loadingElement.remove();
        }
      };
      
      this.container.appendChild(video);
    }
    
    showError(message) {
      // Remove loading indicator
      const loadingElement = this.container.querySelector('.video-loading');
      if (loadingElement) {
        loadingElement.remove();
      }
      
      // Create error message
      const errorElement = document.createElement('div');
      errorElement.className = 'video-error';
      errorElement.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        <p>${message}</p>
        <p class="text-sm mt-2">Please try again later or contact support if the problem persists.</p>
      `;
      
      this.container.appendChild(errorElement);
    }
  }
  
  // Initialize all video players on the page
  document.addEventListener('DOMContentLoaded', () => {
    const videoElements = document.querySelectorAll('[data-video-player]');
    videoElements.forEach(element => {
      // Only initialize if not already in a container that will be initialized by toggleVideoPlayer
      if (!element.closest('[id$="-container"]')) {
        new VideoPlayer({
          containerId: element.id,
          videoUrl: element.dataset.videoUrl,
          videoType: element.dataset.videoType,
          title: element.dataset.title,
          poster: element.dataset.poster
        });
      }
    });
  });