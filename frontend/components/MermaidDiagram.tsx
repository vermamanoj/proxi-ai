import React, { useRef, useState, useMemo } from 'react';
import { ZoomIn, X, AlertTriangle } from 'lucide-react';

interface MermaidDiagramProps {
  chart: string;
}

/**
 * Sanitize mermaid syntax to fix common LLM output issues.
 * Handles multiple error patterns while preserving valid syntax.
 */
function sanitizeMermaidSyntax(chart: string): string {
  let sanitized = chart;

  // 1. Strip HTML tags (e.g. <br/>, <small>, </small>) - mermaid.ink can't parse them in labels
  sanitized = sanitized.replace(/<br\s*\/?>/gi, ' - ');
  sanitized = sanitized.replace(/<\/?[a-z][a-z0-9]*[^>]*>/gi, '');

  // 2. Remove emoji characters that mermaid.ink may not support
  sanitized = sanitized.replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE00}-\u{FE0F}\u{200D}]/gu, '');

  // 3. Fix parentheses inside node labels [...] - mermaid interprets () as shape delimiters
  // Process each line: if it has a node definition like ID[...] or ID["..."], escape parens in label
  sanitized = sanitized.replace(/^(\s*\w+)\[([^\]]+)\]/gm, (match, id, label) => {
    const safe = label.replace(/\(/g, ' ').replace(/\)/g, ' ');
    return `${id}[${safe}]`;
  });

  // 4. Fix parentheses inside double-quoted strings (edge labels)
  sanitized = sanitized.replace(/"([^"]+)"/g, (match, content) => {
    const cleaned = content
      .replace(/\(/g, ' - ')
      .replace(/\)/g, '')
      .replace(/\s+/g, ' ')
      .trim();
    return `"${cleaned}"`;
  });

  // 5. Fix square brackets inside node labels - convert to parentheses
  // Pattern: A[Text [with] brackets] -> A[Text with brackets]
  sanitized = sanitized.replace(/\[([^\]]*)\[([^\]]*)\]([^\]]*)\]/g, '[$1$2$3]');

  // 6. Remove HTML entities that break parsing
  sanitized = sanitized.replace(/&[a-z]+;/gi, ' ');
  sanitized = sanitized.replace(/&#\d+;/g, ' ');

  // 7. Fix common arrow typos
  sanitized = sanitized.replace(/-->/g, '-->');  // Normalize arrows
  sanitized = sanitized.replace(/-\s+->/g, '-->');  // "- ->" -> "-->"
  sanitized = sanitized.replace(/=\s+=>/g, '==>');  // "= =>" -> "==>"

  // 8. Remove problematic characters in node IDs (keep alphanumeric and underscore)
  // Fix: node-name -> node_name (hyphens in IDs can cause issues)
  sanitized = sanitized.replace(/([A-Za-z])[\-]([A-Za-z])/g, '$1_$2');

  // 9. Fix unbalanced quotes by removing incomplete ones at end of lines
  sanitized = sanitized.replace(/"([^"\n]*)\n/g, '"$1"\n');

  // 10. Remove backticks that LLMs sometimes add
  sanitized = sanitized.replace(/```mermaid\n?/gi, '');
  sanitized = sanitized.replace(/```\n?/g, '');

  // 11. Fix "Port XXXX" pattern that often causes parse errors
  sanitized = sanitized.replace(/Port\s+(\d+)/gi, 'Port $1');

  // 12. Clean up multiple spaces and normalize line endings
  sanitized = sanitized.replace(/[ \t]+/g, ' ');
  sanitized = sanitized.replace(/\r\n/g, '\n');

  // 13. Remove empty lines that can cause issues
  sanitized = sanitized.replace(/\n\s*\n/g, '\n');

  return sanitized.trim();
}

/**
 * Build a mermaid.ink image URL from chart code.
 * Uses dark theme and SVG output for crisp rendering.
 * Image-based approach eliminates client-side mermaid.js crash risk.
 */
function buildMermaidInkUrl(chartCode: string): string {
  // Prepend dark theme directive if not already present
  let code = chartCode;
  if (!code.includes('%%{init')) {
    code = `%%{init: {'theme': 'dark'}}%%\n${code}`;
  }
  // Base64 encode (handle UTF-8 properly)
  const base64 = btoa(unescape(encodeURIComponent(code)));
  return `https://mermaid.ink/svg/base64:${base64}`;
}

export const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ chart }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [isZoomed, setIsZoomed] = useState(false);

  // Build image URL from sanitized chart code (memoized to prevent re-fetches)
  const imageUrl = useMemo(() => {
    const trimmed = chart?.trim();
    if (!trimmed) return '';
    const sanitized = sanitizeMermaidSyntax(trimmed);
    return buildMermaidInkUrl(sanitized);
  }, [chart]);

  if (!imageUrl) return null;

  if (error) {
    return (
      <div className="my-3 bg-red-900/20 border border-red-800 rounded-lg p-3 text-red-400 text-xs">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-4 h-4" />
          <span className="font-semibold">Diagram render failed</span>
        </div>
        <pre className="text-xs opacity-70 overflow-x-auto whitespace-pre-wrap">{chart}</pre>
      </div>
    );
  }

  return (
    <>
      {/* Diagram with loading state */}
      <div 
        ref={containerRef}
        className="my-3 p-4 bg-black/30 rounded-lg overflow-x-auto relative group cursor-pointer"
        onClick={() => !loading && setIsZoomed(true)}
      >
        {loading && (
          <div className="flex items-center justify-center h-24">
            <div className="w-5 h-5 border-2 border-proxi-accent border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        <img 
          src={imageUrl} 
          alt="Mermaid Diagram" 
          className={`max-w-full h-auto ${loading ? 'hidden' : ''}`}
          style={{ minHeight: '80px' }}
          onLoad={() => setLoading(false)}
          onError={() => { setLoading(false); setError(true); }}
        />
        {!loading && (
          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="p-1.5 bg-gray-800/80 rounded text-gray-300 text-xs flex items-center gap-1">
              <ZoomIn className="w-3 h-3" />
              Click to zoom
            </div>
          </div>
        )}
      </div>

      {/* Fullscreen zoom modal */}
      {isZoomed && (
        <div 
          className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center p-4"
          onClick={() => setIsZoomed(false)}
        >
          <button
            className="absolute top-4 right-4 p-2 bg-gray-800 hover:bg-gray-700 rounded-full text-white transition-colors"
            onClick={() => setIsZoomed(false)}
          >
            <X className="w-6 h-6" />
          </button>
          <img 
            src={imageUrl} 
            alt="Mermaid Diagram (Zoomed)" 
            className="max-w-[95vw] max-h-[95vh] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  );
};
