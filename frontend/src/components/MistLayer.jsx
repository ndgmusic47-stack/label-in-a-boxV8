import { useEffect } from 'react';
import '../styles/mist.css';

/**
 * MistLayer - Purple/gold gradient mist background
 * Fixed CSS-based gradient (no canvas animation for performance)
 */
export default function MistLayer({ activeStage, stagePositions }) {
  useEffect(() => {
    // Resize handler to update canvas if needed (currently using CSS)
    const handleResize = () => {
      // CSS handles the gradient, no canvas needed
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return <div className="mist-layer" />;
}
