/**
 * Optimized image compression utility
 * Compresses images to reduce file size before upload
 * 
 * @param {File} file - The image file to compress
 * @param {Object} options - Compression options
 * @param {number} options.maxWidth - Maximum width (default: 800)
 * @param {number} options.maxHeight - Maximum height (default: 800)
 * @param {number} options.quality - JPEG quality 0-1 (default: 0.7)
 * @param {number} options.maxSize - Maximum file size in bytes (default: 500KB)
 * @returns {Promise<string>} Base64 encoded compressed image
 */
export const compressImage = (file, options = {}) => {
  const {
    maxWidth = 800,      // Reduced from 1920 for profile images
    maxHeight = 800,      // Reduced from 1920 for profile images
    quality = 0.7,        // Reduced from 0.8 for better compression
    maxSize = 500 * 1024  // 500KB max size
  } = options;

  return new Promise((resolve, reject) => {
    // Validate file type
    if (!file.type.startsWith('image/')) {
      reject(new Error('File must be an image'));
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;
        
        // Calculate new dimensions maintaining aspect ratio
        const aspectRatio = width / height;
        
        if (width > height) {
          if (width > maxWidth) {
            width = maxWidth;
            height = width / aspectRatio;
          }
        } else {
          if (height > maxHeight) {
            height = maxHeight;
            width = height * aspectRatio;
          }
        }
        
        // Round to avoid sub-pixel rendering issues
        width = Math.round(width);
        height = Math.round(height);
        
        canvas.width = width;
        canvas.height = height;
        
        const ctx = canvas.getContext('2d');
        
        // Use high-quality image rendering
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        
        // Draw image to canvas
        ctx.drawImage(img, 0, 0, width, height);
        
        // Convert to blob with compression
        canvas.toBlob((blob) => {
          if (!blob) {
            reject(new Error('Failed to compress image'));
            return;
          }
          
          // If still too large, try with lower quality
          if (blob.size > maxSize) {
            // Recursive call with lower quality
            canvas.toBlob((smallerBlob) => {
              if (!smallerBlob) {
                reject(new Error('Failed to compress image to target size'));
                return;
              }
              
              const reader2 = new FileReader();
              reader2.onloadend = () => resolve(reader2.result);
              reader2.onerror = () => reject(new Error('Failed to read compressed image'));
              reader2.readAsDataURL(smallerBlob);
            }, 'image/jpeg', Math.max(0.5, quality - 0.1));
          } else {
            // Size is acceptable, convert to base64
            const reader2 = new FileReader();
            reader2.onloadend = () => resolve(reader2.result);
            reader2.onerror = () => reject(new Error('Failed to read compressed image'));
            reader2.readAsDataURL(blob);
          }
        }, 'image/jpeg', quality);
      };
      img.onerror = () => reject(new Error('Failed to load image'));
      img.src = e.target.result;
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
};

/**
 * Smart compression that automatically adjusts quality based on file size
 * Optimized to reduce compression attempts for better performance
 * @param {File} file - The image file to compress
 * @returns {Promise<string>} Base64 encoded compressed image
 */
export const smartCompressImage = async (file) => {
  const maxSize = 500 * 1024; // 500KB target
  
  // Estimate initial compression based on file size
  let initialWidth = 800;
  let initialQuality = 0.7;
  
  // If file is very large (>5MB), start with more aggressive compression
  if (file.size > 5 * 1024 * 1024) {
    initialWidth = 600;
    initialQuality = 0.6;
  } else if (file.size > 2 * 1024 * 1024) {
    initialWidth = 700;
    initialQuality = 0.65;
  }
  
  // Start with optimized compression based on file size
  let compressed = await compressImage(file, {
    maxWidth: initialWidth,
    maxHeight: initialWidth,
    quality: initialQuality,
    maxSize: maxSize
  });
  
  // Only try one more time if still too large (reduced from 3 attempts to 2)
  if (compressed.length > maxSize) {
    console.log('Image still too large, applying more aggressive compression...');
    compressed = await compressImage(file, {
      maxWidth: 500,
      maxHeight: 500,
      quality: 0.55,
      maxSize: maxSize
    });
  }
  
  return compressed;
};
