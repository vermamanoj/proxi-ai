import React, { useState } from 'react';
import { Monitor, ZoomIn, X } from 'lucide-react';

interface ScreenshotBubbleProps {
  imageUrl: string;
  caption?: string;
  timestamp?: Date;
}

export const ScreenshotBubble: React.FC<ScreenshotBubbleProps> = ({
  imageUrl,
  caption,
  timestamp
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <>
      {/* Inline preview */}
      <div className="flex justify-start">
        <div className="max-w-[85%] bg-gray-900 border border-gray-800 rounded-2xl rounded-bl-sm overflow-hidden">
          {/* Header */}
          <div className="flex items-center gap-2 px-3 py-2 text-xs text-gray-500 border-b border-gray-800">
            <Monitor className="w-3 h-3" />
            <span>Screen Capture</span>
            {timestamp && (
              <span className="ml-auto opacity-50">
                {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>

          {/* Image preview */}
          <button
            onClick={() => setIsExpanded(true)}
            className="relative w-full group"
          >
            <img
              src={imageUrl}
              alt="Screenshot"
              className="w-full max-h-48 object-cover"
            />
            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <div className="flex items-center gap-2 text-white text-sm">
                <ZoomIn className="w-4 h-4" />
                <span>View full size</span>
              </div>
            </div>
          </button>

          {/* Caption */}
          {caption && (
            <div className="px-3 py-2 text-sm text-gray-300">
              {caption}
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen overlay */}
      {isExpanded && (
        <div
          className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center p-4"
          onClick={() => setIsExpanded(false)}
        >
          <button
            className="absolute top-4 right-4 p-2 text-white/70 hover:text-white bg-white/10 rounded-full"
            onClick={() => setIsExpanded(false)}
          >
            <X className="w-6 h-6" />
          </button>
          
          <img
            src={imageUrl}
            alt="Screenshot"
            className="max-w-full max-h-full object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
          
          {caption && (
            <div className="absolute bottom-4 left-4 right-4 text-center text-white/80 text-sm bg-black/50 px-4 py-2 rounded-lg">
              {caption}
            </div>
          )}
        </div>
      )}
    </>
  );
};
