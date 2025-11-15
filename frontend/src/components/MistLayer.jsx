import '../styles/mist.css';

/**
 * MistLayer - Red/orange gradient mist background
 * Animates based on activeStage using a simple position map
 */
export default function MistLayer({ activeStage }) {
  const mistPositions = {
    beat: { x: '10%', y: '40%' },
    lyrics: { x: '28%', y: '40%' },
    upload: { x: '46%', y: '40%' },
    mix: { x: '64%', y: '40%' },
    release: { x: '82%', y: '40%' },
    content: { x: '90%', y: '40%' },
    analytics: { x: '95%', y: '40%' }
  };

  const pos = activeStage ? mistPositions[activeStage] || { x: '50%', y: '50%' } : { x: '50%', y: '50%' };
  const xPercent = parseFloat(pos.x);
  const yPercent = parseFloat(pos.y);
  
  return (
    <div 
      className="mist-layer" 
      style={{
        background: `radial-gradient(circle at ${pos.x} ${pos.y}, rgba(139, 0, 0, 0.4), transparent 60%),
                    radial-gradient(circle at ${100 - xPercent}% ${100 - yPercent}%, rgba(255, 69, 0, 0.2), transparent 60%)`,
        transition: 'background 0.8s ease-out',
        opacity: activeStage ? 1 : 0.6
      }}
    />
  );
}
