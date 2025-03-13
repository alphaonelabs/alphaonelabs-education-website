document.addEventListener('DOMContentLoaded', function() {
    const materialTypeSelect = document.getElementById('id_material_type');
    const fileInput = document.getElementById('id_file');
    const externalUrlInput = document.getElementById('id_external_url');
    const titleInput = document.getElementById('id_title');
    
    if (!materialTypeSelect) return;
    
    // Handle material type change
    materialTypeSelect.addEventListener('change', function() {
      const isVideo = materialTypeSelect.value === 'video';
      
      // Show/hide appropriate fields based on material type
      if (isVideo) {
        // For videos, hide file input and show external URL with note
        if (fileInput) {
          const fileInputParent = fileInput.closest('.mb-4');
          if (fileInputParent) {
            fileInputParent.style.display = 'none';
          }
        }
      } else {
        // Show the file input for non-video material types
        if (fileInput) {
          const fileInputParent = fileInput.closest('.mb-4');
          if (fileInputParent) {
            fileInputParent.style.display = '';
          }
        }
      }
    });
    
    // Initial check
    if (materialTypeSelect.value === 'video') {
      if (fileInput) {
        const fileInputParent = fileInput.closest('.mb-4');
        if (fileInputParent) {
          fileInputParent.style.display = 'none';
        }
      }
    }
    
    // Auto-detect title from YouTube/Vimeo URLs
    if (externalUrlInput) {
      externalUrlInput.addEventListener('change', function() {
        const url = externalUrlInput.value;
        if (!url) return;
        
        // Only process for videos
        if (materialTypeSelect.value !== 'video') return;
        
        // Try to extract video information from YouTube or Vimeo
        if (url.includes('youtube.com') || url.includes('youtu.be')) {
          fetchYouTubeInfo(url);
        } else if (url.includes('vimeo.com')) {
          fetchVimeoInfo(url);
        }
      });
    }
    
    // Fetch YouTube video information
    function fetchYouTubeInfo(url) {
      let videoId = '';
      
      // Extract video ID from URL
      if (url.includes('youtube.com/watch')) {
        const urlParams = new URLSearchParams(new URL(url).search);
        videoId = urlParams.get('v');
      } else if (url.includes('youtu.be/')) {
        videoId = url.split('youtu.be/')[1].split('?')[0];
      }
      
      if (!videoId) return;
      
      // Use YouTube oEmbed API to get video information
      fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`)
        .then(response => response.json())
        .then(data => {
          // Auto-fill title if empty
          if (titleInput && (!titleInput.value || titleInput.value === '')) {
            titleInput.value = data.title;
          }
        })
        .catch(error => {
          console.error('Error fetching YouTube video info:', error);
        });
    }
    
    // Fetch Vimeo video information
    function fetchVimeoInfo(url) {
      let videoId = '';
      
      // Extract video ID from URL
      const match = url.match(/vimeo\\.com\\/(?:video\\/)?(\\d+)/);
      videoId = match ? match[1] : '';
      
      if (!videoId) return;
      
      // Use Vimeo oEmbed API to get video information
      fetch(`https://vimeo.com/api/oembed.json?url=https://vimeo.com/${videoId}`)
        .then(response => response.json())
        .then(data => {
          // Auto-fill title if empty
          if (titleInput && (!titleInput.value || titleInput.value === '')) {
            titleInput.value = data.title;
          }
        })
        .catch(error => {
          console.error('Error fetching Vimeo video info:', error);
        });
    }
  });