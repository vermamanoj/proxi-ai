/**
 * Image utilities for mobile-friendly uploads
 * Compresses images to prevent "low memory" errors on mobile devices
 */

const MAX_WIDTH = 1920;
const MAX_HEIGHT = 1920;
const QUALITY = 0.85;
const MAX_FILE_SIZE = 4 * 1024 * 1024; // 4MB target

export async function compressImage(file: File): Promise<File> {
  // Skip compression for small files or non-images
  if (file.size < MAX_FILE_SIZE && !file.type.startsWith('image/')) {
    return file;
  }

  return new Promise((resolve, reject) => {
    const img = new Image();
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    img.onload = () => {
      URL.revokeObjectURL(img.src);

      // Calculate new dimensions maintaining aspect ratio
      let { width, height } = img;
      
      if (width > MAX_WIDTH) {
        height = (height * MAX_WIDTH) / width;
        width = MAX_WIDTH;
      }
      if (height > MAX_HEIGHT) {
        width = (width * MAX_HEIGHT) / height;
        height = MAX_HEIGHT;
      }

      canvas.width = width;
      canvas.height = height;

      if (!ctx) {
        resolve(file); // Fallback to original
        return;
      }

      // Draw with white background (for transparency)
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, width, height);
      ctx.drawImage(img, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          if (!blob) {
            resolve(file);
            return;
          }
          
          // Create new file with compressed data
          const compressedFile = new File(
            [blob],
            file.name.replace(/\.[^.]+$/, '.jpg'),
            { type: 'image/jpeg' }
          );
          
          console.log(`[Image] Compressed: ${(file.size / 1024).toFixed(0)}KB → ${(compressedFile.size / 1024).toFixed(0)}KB`);
          resolve(compressedFile);
        },
        'image/jpeg',
        QUALITY
      );
    };

    img.onerror = () => {
      console.warn('[Image] Compression failed, using original');
      resolve(file);
    };

    img.src = URL.createObjectURL(file);
  });
}
