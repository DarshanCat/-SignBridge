"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { cameraErrorMessage } from "@/lib/camera";
import { createHolistic, type HolisticInstance } from "@/lib/holistic";
import {
  appendFrame,
  EMPTY_BUFFER,
  summarize,
  toFrame,
  type BufferState,
  type CaptureStats,
  type HolisticResults,
  type LandmarkFrame,
} from "@/lib/landmarks";

export type CaptureState = "idle" | "starting" | "running" | "error";
export type ExtractorState = "not_loaded" | "loading" | "ready" | "error";

export interface LandmarkCapture {
  state: CaptureState;
  extractor: ExtractorState;
  error: string | null;
  stats: CaptureStats;
  /** Increments every time the camera is started; results from older runs must be ignored. */
  runId: number;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  start: () => Promise<void>;
  stop: () => void;
  getBuffer: () => LandmarkFrame[];
}

const EMPTY: CaptureStats = { frames: 0, withPose: 0, withHands: 0 };

function draw(canvas: HTMLCanvasElement | null, r: HolisticResults) {
  const ctx = canvas?.getContext("2d");
  if (!canvas || !ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const dots = (pts: { x: number; y: number }[] | undefined, color: string, radius: number) => {
    ctx.fillStyle = color;
    pts?.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x * canvas.width, p.y * canvas.height, radius, 0, 2 * Math.PI);
      ctx.fill();
    });
  };
  dots(r.poseLandmarks, "#5eead4", 3);
  dots(r.leftHandLandmarks, "#fbbf24", 3);
  dots(r.rightHandLandmarks, "#f472b6", 3);
}

/** Webcam + in-browser MediaPipe Holistic. Video never leaves the browser; only a short landmark buffer is kept. */
export function useLandmarkCapture(): LandmarkCapture {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const holisticRef = useRef<HolisticInstance | null>(null);
  const bufferRef = useRef<BufferState>(EMPTY_BUFFER);
  const runningRef = useRef(false);
  const [state, setState] = useState<CaptureState>("idle");
  const [extractor, setExtractor] = useState<ExtractorState>("not_loaded");
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<CaptureStats>(EMPTY);
  const [runId, setRunId] = useState(0);

  const stop = useCallback(() => {
    runningRef.current = false;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    canvasRef.current?.getContext("2d")?.clearRect(0, 0, 9999, 9999);
    bufferRef.current = EMPTY_BUFFER;
    setStats(EMPTY);
    setState((s) => (s === "error" ? s : "idle"));
  }, []);

  const start = useCallback(async () => {
    setError(null);
    setRunId((r) => r + 1);
    setState("starting");
    try {
      if (!holisticRef.current) {
        setExtractor("loading");
        try {
          holisticRef.current = await createHolistic((r) => {
            draw(canvasRef.current, r);
            bufferRef.current = appendFrame(bufferRef.current, toFrame(r));
          });
          setExtractor("ready");
        } catch (e) {
          setExtractor("error");
          throw e;
        }
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) throw new Error("Video element is not available.");
      video.srcObject = stream;
      await video.play();
      runningRef.current = true;
      setState("running");

      let last = 0;
      const loop = async () => {
        if (!runningRef.current) return;
        if (video.readyState >= 2 && video.currentTime !== last) {
          last = video.currentTime;
          try {
            await holisticRef.current?.send({ image: video });
            setStats(summarize(bufferRef.current.frames));
          } catch (e) {
            runningRef.current = false;
            setError(e instanceof Error ? e.message : "Landmark extraction failed.");
            setState("error");
            return;
          }
        }
        requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    } catch (e) {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      setError(cameraErrorMessage(e));
      setState("error");
    }
  }, []);

  useEffect(
    () => () => {
      runningRef.current = false;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      void holisticRef.current?.close();
      holisticRef.current = null;
    },
    [],
  );

  const getBuffer = useCallback(() => bufferRef.current.frames, []);
  return { state, extractor, error, stats, runId, videoRef, canvasRef, start, stop, getBuffer };
}
