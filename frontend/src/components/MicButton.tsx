"use client";

export default function MicButton({ isRecording, isProcessing, isPlaying, disabled, onTap }: {
  isRecording: boolean; isProcessing: boolean; isPlaying: boolean;
  disabled: boolean; onTap: () => void;
}) {
  if (isProcessing) {
    return (
      <div className="flex flex-col items-center gap-3">
        <div className="w-20 h-20 rounded-full bg-patch-card border-2 border-patch-border flex items-center justify-center">
          <div className="flex items-center gap-1">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="wave-bar w-1 bg-patch-accent rounded-full" style={{ height: "8px" }} />
            ))}
          </div>
        </div>
        <span className="text-xs text-patch-soft/50">{isPlaying ? "She's speaking..." : "Thinking..."}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative">
        {isRecording && (
          <>
            <div className="absolute inset-0 rounded-full bg-patch-accent/20 animate-ripple" />
            <div className="absolute inset-0 rounded-full bg-patch-accent/10 animate-ripple" style={{ animationDelay: "0.5s" }} />
          </>
        )}
        <button
          onClick={onTap}
          disabled={disabled}
          className={`relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-200 select-none
            ${isRecording ? "bg-patch-accent scale-110 mic-recording" : "bg-patch-card border-2 border-patch-border hover:border-patch-accent hover:bg-patch-accent/10"}
            ${disabled ? "opacity-30 cursor-not-allowed" : "cursor-pointer active:scale-95"}`}
        >
          {isRecording ? (
            /* Stop/square icon when recording */
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="#fff" stroke="none">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          ) : (
            /* Mic icon when idle */
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none"
              stroke="#fb7185" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" x2="12" y1="19" y2="22" />
            </svg>
          )}
        </button>
      </div>
      <span className="text-xs text-patch-soft/50">{isRecording ? "Tap to send" : "Tap to speak"}</span>
    </div>
  );
}
