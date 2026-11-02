"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { aspectOf, cameraErrorMessage, openCamera, type Resolution } from "@/lib/camera";
import { createHolistic, type HolisticInstance, type LoadPhase } from "@/lib/holistic";
import { drawOverlay, poseReadout, type PoseReadout } from "@/lib/overlay";
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
  /** What the body pose tracker sees in the latest frame (for the on-screen hint). */
  pose: PoseReadout;
  /** What the camera actually delivers (null until it runs); the picture, overlay and landmark conversion follow it. */
  resolution: Resolution | null;
  /** Which loading step the landmark model is in while extractor is "loading". */
  loadPhase: LoadPhase | null;
  /** Load the landmark model without the camera, so Start camera is instant. Safe to call more than once. */
  preload: () => void;
  /** Increments every time the camera is started; results from older runs must be ignored. */
  runId: number;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  start: () => Promise<void>;
  stop: () => void;
  getBuffer: () => LandmarkFrame[];
  /** Start collecting every extracted frame (landmarks only) for a recording; ends with endRecording(). */
  beginRecording: () => void;
  endRecording: () => LandmarkFrame[];
  /** The live camera stream (for a local MediaRecorder in the landmark check tab); null when the camera is off. */
  getStream: () => MediaStream | null;
  /** Called with every extracted frame and its performance.now() time; pass null to remove. */
  setFrameListener: (fn: ((frame: LandmarkFrame, tMs: number) => void) | null) => void;
}

const EMPTY: CaptureStats = { frames: 0, withPose: 0, withHands: 0 };
const NO_POSE: PoseReadout = { detected: false, visible: 0, shoulders: false, elbows: false, wrists: false, shoulderWidth: null };

/** Webcam + in-browser MediaPipe Holistic. Video never leaves the browser; only a short landmark buffer is kept. */
export function useLandmarkCapture(): LandmarkCapture {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const holisticRef = useRef<HolisticInstance | null>(null);
  const bufferRef = useRef<BufferState>(EMPTY_BUFFER);
  const runningRef = useRef(false);
  const recordRef = useRef<LandmarkFrame[] | null>(null);
  const listenerRef = useRef<((frame: LandmarkFrame, tMs: number) => void) | null>(null);
  const [state, setState] = useState<CaptureState>("idle");
  const [extractor, setExtractor] = useState<ExtractorState>("not_loaded");
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<CaptureStats>(EMPTY);
  const [runId, setRunId] = useState(0);
  const [pose, setPose] = useState<PoseReadout>(NO_POSE);
  const [resolution, setResolution] = useState<Resolution | null>(null);
  const widthRef = useRef<number | null>(null); // smoothed shoulder width, so the warning does not flicker
  const [loadPhase, setLoadPhase] = useState<LoadPhase | null>(null);
  const loadingRef = useRef<Promise<void> | null>(null);

  const stop = useCallback(() => {
    runningRef.current = false;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    canvasRef.current?.getContext("2d")?.clearRect(0, 0, 9999, 9999);
    bufferRef.current = EMPTY_BUFFER;
    recordRef.current = null;
    setResolution(null);
    setStats(EMPTY);
    setState((s) => (s === "error" ? s : "idle"));
  }, []);

  const ensureModel = useCallback((): Promise<void> => {
    if (holisticRef.current) return Promise.resolve();
    loadingRef.current ??= (async () => {
      setExtractor("loading");
      try {
        holisticRef.current = await createHolistic((r) => {
          drawOverlay(canvasRef.current?.getContext("2d") as CanvasRenderingContext2D, canvasRef.current?.width ?? 640, canvasRef.current?.height ?? 480, r);
          const readout = poseReadout(r.poseLandmarks);
          widthRef.current = readout.shoulderWidth === null ? widthRef.current : widthRef.current === null ? readout.shoulderWidth : widthRef.current * 0.85 + readout.shoulderWidth * 0.15;
          setPose({ ...readout, shoulderWidth: readout.shoulderWidth === null ? null : widthRef.current });
          const v = videoRef.current;
          const frame = toFrame(r, v && v.videoWidth && v.videoHeight ? aspectOf({ width: v.videoWidth, height: v.videoHeight }) : undefined);
          bufferRef.current = appendFrame(bufferRef.current, frame);
          recordRef.current?.push(frame);
          listenerRef.current?.(frame, performance.now());
        }, setLoadPhase);
        setExtractor("ready");
      } catch (e) {
        setExtractor("error");
        throw e;
      } finally {
        loadingRef.current = null;
      }
    })();
    return loadingRef.current;
  }, []);

  const preload = useCallback(() => {
    ensureModel().catch(() => {}); // the error state is shown; Start camera retries
  }, [ensureModel]);

  const start = useCallback(async () => {
    setError(null);
    setRunId((r) => r + 1);
    setState("starting");
    try {
      await ensureModel();
      const stream = await openCamera((c) => navigator.mediaDevices.getUserMedia(c));
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) throw new Error("Video element is not available.");
      video.srcObject = stream;
      await video.play();
      widthRef.current = null;
      setResolution(video.videoWidth && video.videoHeight ? { width: video.videoWidth, height: video.videoHeight } : null);
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
  }, [ensureModel]);

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
  const getStream = useCallback(() => streamRef.current, []);
  const setFrameListener = useCallback((fn: ((frame: LandmarkFrame, tMs: number) => void) | null) => {
    listenerRef.current = fn;
  }, []);
  const beginRecording = useCallback(() => {
    recordRef.current = [];
  }, []);
  const endRecording = useCallback(() => {
    const frames = recordRef.current ?? [];
    recordRef.current = null;
    return frames;
  }, []);
  return { state, extractor, error, stats, runId, videoRef, canvasRef, start, stop, getBuffer, beginRecording, endRecording, pose, resolution, loadPhase, preload, getStream, setFrameListener };
}
