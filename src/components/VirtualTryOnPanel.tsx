import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Camera,
  CameraOff,
  SwitchCamera,
  Loader2,
  ShieldCheck,
  Maximize2,
} from 'lucide-react';
import type { ProductResponse, SizeMeasurementRow } from '../types/product';

interface VirtualTryOnPanelProps {
  product?: ProductResponse | null;
  selectedSize?: string | null;
  selectedSizeRow?: SizeMeasurementRow | null;
}

type CameraStatus =
  | 'idle'
  | 'requesting_permission'
  | 'streaming'
  | 'error';

function isLikelyMobileDevice(): boolean {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') {
    return false;
  }
  const ua = navigator.userAgent || '';
  if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua)) {
    return true;
  }
  return window.matchMedia?.('(pointer: coarse) and (max-width: 1024px)').matches ?? false;
}

export const VirtualTryOnPanel: React.FC<VirtualTryOnPanelProps> = ({
  product,
  selectedSize,
}) => {
  const [cameraStatus, setCameraStatus] = useState<CameraStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [preferredFacingMode, setPreferredFacingMode] = useState<'user' | 'environment'>(() =>
    isLikelyMobileDevice() ? 'environment' : 'user'
  );
  const [activeCameraLabel, setActiveCameraLabel] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stopCameraTracks = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // Ignore track stop errors
        }
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setActiveCameraLabel(null);
  }, []);

  // Stop camera tracks when the user leaves the component or closes/navigates away from the page
  useEffect(() => {
    const handlePageHide = () => {
      stopCameraTracks();
    };
    window.addEventListener('pagehide', handlePageHide);
    window.addEventListener('beforeunload', handlePageHide);
    return () => {
      window.removeEventListener('pagehide', handlePageHide);
      window.removeEventListener('beforeunload', handlePageHide);
      stopCameraTracks();
    };
  }, [stopCameraTracks]);

  // Attach MediaStream to <video> element whenever streaming is active
  useEffect(() => {
    if (cameraStatus === 'streaming' && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {
        // Handled by browser autoplay rules with muted + playsInline
      });
    }
  }, [cameraStatus]);

  const startCamera = useCallback(
    async (facingModeOverride?: 'user' | 'environment') => {
      const targetFacing = facingModeOverride ?? preferredFacingMode;
      setErrorMessage(null);

      if (
        typeof navigator === 'undefined' ||
        !navigator.mediaDevices ||
        typeof navigator.mediaDevices.getUserMedia !== 'function'
      ) {
        setCameraStatus('error');
        setErrorMessage(
          'Camera access is not supported in this browser environment. Please use a modern browser over HTTPS.'
        );
        return;
      }

      setCameraStatus('requesting_permission');
      stopCameraTracks();

      try {
        let stream: MediaStream;
        try {
          // Prefer back camera ('environment') on mobile and front camera ('user') on desktop,
          // with portrait-friendly resolution hints for full standing body (head-to-feet) framing.
          stream = await navigator.mediaDevices.getUserMedia({
            video: {
              facingMode: { ideal: targetFacing },
              width: { ideal: 1080 },
              height: { ideal: 1920 },
            },
            audio: false,
          });
        } catch {
          // Fallback to any available video camera if resolution/facingMode constraints are rejected
          stream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false,
          });
        }

        streamRef.current = stream;
        const videoTrack = stream.getVideoTracks()[0];
        if (videoTrack) {
          setActiveCameraLabel(
            videoTrack.label || (targetFacing === 'environment' ? 'Back Camera' : 'Front Camera')
          );
          videoTrack.onended = () => {
            stopCameraTracks();
            setCameraStatus('idle');
          };
        }
        setCameraStatus('streaming');
      } catch (err) {
        stopCameraTracks();
        setCameraStatus('error');
        const domErr = err as DOMException;
        if (domErr?.name === 'NotAllowedError' || domErr?.name === 'PermissionDeniedError') {
          setErrorMessage(
            'Camera permission was denied. Please allow camera access in your browser address bar and click "Start Camera" again.'
          );
        } else if (domErr?.name === 'NotFoundError' || domErr?.name === 'DevicesNotFoundError') {
          setErrorMessage(
            'No camera device was detected on your system. Please connect a webcam or use a device with a camera.'
          );
        } else if (domErr?.name === 'NotReadableError' || domErr?.name === 'TrackStartError') {
          setErrorMessage(
            'Your camera is currently in use by another application. Please close other apps using the camera and try again.'
          );
        } else {
          setErrorMessage(
            domErr?.message || 'Unable to access your device camera.'
          );
        }
      }
    },
    [preferredFacingMode, stopCameraTracks]
  );

  const handleStopCamera = () => {
    stopCameraTracks();
    setCameraStatus('idle');
    setErrorMessage(null);
  };

  const handleToggleFacingMode = () => {
    const nextFacing = preferredFacingMode === 'user' ? 'environment' : 'user';
    setPreferredFacingMode(nextFacing);
    if (cameraStatus === 'streaming') {
      void startCamera(nextFacing);
    }
  };

  const shouldMirrorPreview = preferredFacingMode === 'user';

  return (
    <aside
      aria-label="Live Camera Panel"
      className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 shadow-2xs space-y-4"
    >
      {/* Panel Header */}
      <div className="border-b border-[var(--border-subtle)] pb-3.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Camera className="h-4 w-4 text-[var(--text-primary)]" />
            <h2 className="font-serif-display text-xl font-semibold text-[var(--text-primary)]">
              Live Camera
            </h2>
          </div>
          <span
            className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-mono-tabular text-[11px] font-medium ${
              cameraStatus === 'streaming'
                ? 'border-[var(--status-success-border)] bg-[var(--status-success-bg)] text-[var(--status-success-text)]'
                : 'border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[var(--text-secondary)]'
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                cameraStatus === 'streaming' ? 'bg-[var(--status-success-text)]' : 'bg-[var(--text-muted)]'
              }`}
            />
            {cameraStatus === 'streaming' ? 'LIVE 9:16' : 'STANDBY'}
          </span>
        </div>
        <p className="mt-1.5 text-xs leading-relaxed text-[var(--text-secondary)]">
          Full-length 9:16 portrait mirror preview. Step back so your full standing body from head to feet is visible in the frame.
        </p>
      </div>

      {/* Optional Active Garment & Size Context Bar */}
      {product && product.name && (
        <div className="flex items-center justify-between gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-3 py-2 text-xs">
          <span className="truncate font-medium text-[var(--text-primary)]">{product.name}</span>
          {selectedSize && (
            <span className="shrink-0 font-mono-tabular text-[11px] font-semibold text-[var(--text-secondary)]">
              Size {selectedSize}
            </span>
          )}
        </div>
      )}

      {/* Portrait 9:16 Live Camera Frame */}
      <div className="relative w-full overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-subtle)] aspect-[9/16]">
        {/* STATE 1: Idle Standby */}
        {cameraStatus === 'idle' && (
          <div className="flex h-full w-full flex-col items-center justify-between bg-[var(--bg-subtle)] p-6 text-center">
            <div className="w-full flex items-center justify-between text-[10px] font-mono-tabular uppercase tracking-wider text-[var(--text-muted)]">
              <span>Head Alignment</span>
              <span>9:16 Portrait</span>
            </div>

            <div className="my-auto flex flex-col items-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full border border-[var(--border-strong)] bg-[var(--bg-surface)] text-[var(--text-primary)]">
                <Maximize2 className="h-5 w-5" />
              </div>
              <p className="mt-3 text-xs font-semibold text-[var(--text-primary)]">
                Full-Body Camera Frame
              </p>
              <p className="mt-1.5 max-w-[200px] text-[11px] leading-relaxed text-[var(--text-secondary)]">
                Click <strong>Start Camera</strong> below to open your live device camera in a 9:16 standing frame.
              </p>
            </div>

            <div className="w-full flex items-center justify-between text-[10px] font-mono-tabular uppercase tracking-wider text-[var(--text-muted)]">
              <span>Feet Alignment</span>
              <span>{preferredFacingMode === 'environment' ? 'Back Cam' : 'Front Cam'}</span>
            </div>
          </div>
        )}

        {/* STATE 2: Requesting Permission */}
        {cameraStatus === 'requesting_permission' && (
          <div className="flex h-full w-full flex-col items-center justify-center bg-[var(--bg-subtle)] p-6 text-center">
            <Loader2 className="h-6 w-6 animate-spin text-[var(--text-primary)]" />
            <p className="mt-3 text-xs font-semibold text-[var(--text-primary)]">
              Requesting Camera Permission…
            </p>
            <p className="mt-1 text-[11px] leading-relaxed text-[var(--text-secondary)]">
              Please allow camera access in your browser prompt to start the live preview.
            </p>
          </div>
        )}

        {/* STATE 3: Live Video Stream (Portrait 9:16 with object-fit: cover) */}
        {cameraStatus === 'streaming' && (
          <div className="relative h-full w-full bg-black">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className={`h-full w-full object-cover ${
                shouldMirrorPreview ? '-scale-x-100' : ''
              }`}
            />

            {/* Subtle non-intrusive head-to-feet framing guide */}
            <div className="pointer-events-none absolute inset-3 flex flex-col justify-between rounded-lg border border-white/25 p-2.5 text-[10px] font-mono-tabular text-white/90">
              <div className="flex items-center justify-between">
                <span className="rounded bg-black/65 px-1.5 py-0.5 backdrop-blur-xs">
                  HEAD
                </span>
                <span className="rounded bg-black/65 px-1.5 py-0.5 backdrop-blur-xs">
                  9:16 LIVE
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="rounded bg-black/65 px-1.5 py-0.5 backdrop-blur-xs">
                  FEET
                </span>
                {activeCameraLabel && (
                  <span className="max-w-[140px] truncate rounded bg-black/65 px-1.5 py-0.5 backdrop-blur-xs">
                    {activeCameraLabel}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* STATE 4: Permission Denied or Camera Unavailable */}
        {cameraStatus === 'error' && (
          <div className="flex h-full w-full flex-col items-center justify-center bg-[var(--bg-subtle)] p-6 text-center">
            <div className="flex h-11 w-11 items-center justify-center rounded-full border border-[var(--status-error-border)] bg-[var(--status-error-bg)] text-[var(--status-error-text)]">
              <CameraOff className="h-5 w-5" />
            </div>
            <p className="mt-3 text-xs font-semibold text-[var(--text-primary)]">
              Camera Unavailable
            </p>
            <p className="mt-1.5 text-[11px] leading-relaxed text-[var(--text-secondary)]">
              {errorMessage || 'Unable to access your camera.'}
            </p>
          </div>
        )}
      </div>

      {/* Start Camera / Stop Camera / Switch Camera Controls */}
      <div className="space-y-2">
        {cameraStatus !== 'streaming' ? (
          <button
            type="button"
            onClick={() => void startCamera()}
            disabled={cameraStatus === 'requesting_permission'}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--accent-bg)] px-4 py-3 text-xs font-medium text-[var(--accent-text)] transition-colors hover:bg-[var(--accent-hover)] disabled:opacity-60 cursor-pointer"
          >
            {cameraStatus === 'requesting_permission' ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Starting Camera…
              </>
            ) : (
              <>
                <Camera className="h-4 w-4" />
                Start Camera
              </>
            )}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleStopCamera}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--status-error-border)] bg-[var(--status-error-bg)] px-4 py-3 text-xs font-medium text-[var(--status-error-text)] transition-colors hover:opacity-90 cursor-pointer"
          >
            <CameraOff className="h-4 w-4" />
            Stop Camera
          </button>
        )}

        <button
          type="button"
          onClick={handleToggleFacingMode}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-3 py-2 text-xs font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)] cursor-pointer"
        >
          <SwitchCamera className="h-3.5 w-3.5" />
          Mode: {preferredFacingMode === 'environment' ? 'Back Camera (Mobile)' : 'Front Camera (Desktop)'}
        </button>
      </div>

      {/* Privacy Notice */}
      <div className="flex items-start gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-3 text-[11px] leading-relaxed text-[var(--text-secondary)]">
        <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--text-primary)]" />
        <span>
          Live browser stream only. No photographs are captured, stored, or uploaded to any external server.
        </span>
      </div>
    </aside>
  );
};
