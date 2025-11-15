import '../styles/mist.css';

/**
 * MistLayer - NP22 Purple/Gold gradient mist background
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
  
  return (
    <div 
      className="mist-layer" 
      style={{
        '--x': pos.x,
        '--y': pos.y
      }}
    />
  );
}
