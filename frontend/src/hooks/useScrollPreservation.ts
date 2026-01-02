import { useRef, useEffect } from 'react';

/**
 * Hook to preserve scroll position when dialogs open/close
 * Usage: Call saveScroll() when dialog opens, restoreScroll() when dialog closes
 */
export function useScrollPreservation() {
  const savedScrollPosition = useRef<number | null>(null);

  const saveScroll = () => {
    // Save current scroll position
    savedScrollPosition.current = window.scrollY || document.documentElement.scrollTop;
  };

  const restoreScroll = () => {
    // Restore scroll position after a brief delay to allow DOM updates
    if (savedScrollPosition.current !== null) {
      // Use requestAnimationFrame to ensure DOM has updated
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.scrollTo({
            top: savedScrollPosition.current!,
            behavior: 'instant' as ScrollBehavior, // Use instant to avoid flicker
          });
        });
      });
    }
  };

  const clearScroll = () => {
    savedScrollPosition.current = null;
  };

  return { saveScroll, restoreScroll, clearScroll };
}

