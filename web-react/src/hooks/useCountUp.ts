import { useState, useEffect, useRef } from 'react';

export function useCountUp(end: number, duration = 1200) {
  const [count, setCount] = useState(0);
  const prevEnd = useRef(0);

  useEffect(() => {
    if (end === prevEnd.current) return;
    prevEnd.current = end;

    const startVal = 0;
    const startTime = performance.now();

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(startVal + (end - startVal) * eased);

      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    };

    requestAnimationFrame(tick);
  }, [end, duration]);

  return count;
}
