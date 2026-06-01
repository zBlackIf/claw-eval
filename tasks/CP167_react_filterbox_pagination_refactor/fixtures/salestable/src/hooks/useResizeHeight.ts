import { useEffect, useRef, useCallback } from 'react';

/**
 * Hook to observe height changes of a DOM element by its ID.
 * Calls the callback whenever the element's height changes.
 *
 * @param elementId - The DOM element ID to observe
 * @param callback - Called with the new height whenever it changes
 */
export const useResizeHeight = (elementId: string, callback: (height: number) => void) => {
  const observerRef = useRef<ResizeObserver | null>(null);
  const prevHeightRef = useRef<number>(0);

  const observe = useCallback(() => {
    const element = document.getElementById(elementId);
    if (!element) return;

    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    observerRef.current = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const height = entry.contentRect.height;
        if (height !== prevHeightRef.current) {
          prevHeightRef.current = height;
          callback(height);
        }
      }
    });

    observerRef.current.observe(element);
  }, [elementId, callback]);

  useEffect(() => {
    observe();
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [observe]);
};
