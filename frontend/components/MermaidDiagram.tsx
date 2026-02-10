import React, { useRef, useState, useEffect, useCallback } from 'react';
import { ZoomIn, X, AlertTriangle } from 'lucide-react';
import mermaid from 'mermaid';

interface MermaidDiagramProps {
  chart: string;
}

// Initialize mermaid once with dark theme
let mermaidInitialized = false;
function ensureMermaidInit() {
  if (mermaidInitialized) return;
  mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'loose',
    flowchart: { htmlLabels: true, curve: 'basis' },
    fontFamily: 'ui-sans-serif, system-ui, sans-serif',
  });
  mermaidInitialized = true;
}

/**
 * Sanitize mermaid syntax to fix common LLM output issues.
 * Handles multiple error patterns while preserving valid syntax.
 */
function sanitizeMermaidSyntax(chart: string): string {
  let sanitized = chart;

  // 1. Strip HTML tags (e.g. <br/>, <small>, </small>)
  sanitized = sanitized.replace(/<br\s*\/?>/gi, ' - ');
  sanitized = sanitized.replace(/<\/?[a-z][a-z0-9]*[^>]*>/gi, '');

  // 2. Remove emoji characters that may not render in SVG
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

  // 12. Normalize line endings (but preserve indentation for readability)
  sanitized = sanitized.replace(/\r\n/g, '\n');

  // 13. Remove empty lines that can cause issues
  sanitized = sanitized.replace(/\n\s*\n/g, '\n');

  return sanitized.trim();
}

// Monotonic counter for unique diagram IDs
let diagramCounter = 0;

export const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ chart }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [isZoomed, setIsZoomed] = useState(false);
  const idRef = useRef(`mermaid-${Date.now()}-${++diagramCounter}`);

  const renderDiagram = useCallback(async () => {
    const trimmed = chart?.trim();
    if (!trimmed) { setLoading(false); return; }

    try {
      ensureMermaidInit();
      const sanitized = sanitizeMermaidSyntax(trimmed);
      const { svg } = await mermaid.render(idRef.current, sanitized);
      setSvgContent(svg);
      setLoading(false);
    } catch (err) {
      console.warn('[MermaidDiagram] Render failed:', err);
      setLoading(false);
      setError(true);
    }
  }, [chart]);

  useEffect(() => {
    renderDiagram();
  }, [renderDiagram]);

  if (!chart?.trim()) return null;

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
        onClick={() => !loading && svgContent && setIsZoomed(true)}
      >
        {loading && (
          <div className="flex items-center justify-center h-24">
            <div className="w-5 h-5 border-2 border-proxi-accent border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {svgContent && (
          <div 
            className="mermaid-svg max-w-full"
            style={{ minHeight: '80px' }}
            dangerouslySetInnerHTML={{ __html: svgContent }} 
          />
        )}
        {!loading && svgContent && (
          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="p-1.5 bg-gray-800/80 rounded text-gray-300 text-xs flex items-center gap-1">
              <ZoomIn className="w-3 h-3" />
              Click to zoom
            </div>
          </div>
        )}
      </div>

      {/* Fullscreen zoom modal */}
      {isZoomed && svgContent && (
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
          <div 
            className="mermaid-svg max-w-[95vw] max-h-[95vh] overflow-auto"
            dangerouslySetInnerHTML={{ __html: svgContent }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  );
};
