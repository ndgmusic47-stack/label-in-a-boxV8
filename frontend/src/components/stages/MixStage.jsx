import { useState, useEffect } from 'react';
import { mixAudio } from '../../utils/api';
import StageWrapper from './StageWrapper';

export default function MixStage({ sessionId, sessionData, updateSessionData, voice, onClose, onNext, completeStage }) {
  const [mixing, setMixing] = useState(false);
  const [mixUrl, setMixUrl] = useState(null);

  useEffect(() => {
    if (sessionData?.masterFile) {
      setMixUrl(sessionData.masterFile);
    }
  }, [sessionData]);

  const handleMixNow = async () => {
    setMixing(true);
    try {
      const userId = sessionStorage.getItem("user_id");
      const sessionId = sessionStorage.getItem("session_id");

      const result = await mixAudio(userId, sessionId);

      if (result.mix_url) {
        setMixUrl(result.mix_url);
        completeStage && completeStage("mix", result.mix_url);
      }
    } catch (err) {
      console.error("Mix failed:", err);
    } finally {
      setMixing(false);
    }
  };

  return (
    <StageWrapper 
      title="Mix & Master" 
      icon="🎛️" 
      onClose={onClose}
      onNext={onNext}
      voice={voice}
    >
      <div className="stage-scroll-container">
        <div className="flex flex-col items-center justify-center gap-8 p-6 md:p-10">
          <button
            className="mix-btn"
            disabled={mixing}
            onClick={handleMixNow}
          >
            {mixing ? "Mixing..." : "Mix Now"}
          </button>

          {mixUrl && (
            <audio controls src={mixUrl} style={{ width: "100%" }} />
          )}
        </div>
      </div>
    </StageWrapper>
  );
}
