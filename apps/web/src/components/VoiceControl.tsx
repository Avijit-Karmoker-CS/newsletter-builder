"use client";

import { useEffect, useRef, useState } from "react";

type SpeechResultEvent = {
  resultIndex: number;
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
};

type BrowserRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechResultEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type Transcriber = (audio: Float32Array) => Promise<{ text?: string }>;

function recognitionCtor(): (new () => BrowserRecognition) | null {
  if (typeof window === "undefined") return null;
  const host = window as Window & {
    SpeechRecognition?: new () => BrowserRecognition;
    webkitSpeechRecognition?: new () => BrowserRecognition;
  };
  return host.SpeechRecognition || host.webkitSpeechRecognition || null;
}

function cleanTranscript(text: string) {
  return text
    .replace(/\[(?:BLANK_AUDIO|Music|Applause|Noise|Silence|Laughter)\]/gi, " ")
    .replace(/\((?:BLANK_AUDIO|Music|Applause|Noise|Silence|inaudible)\)/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function joinText(current: string, spoken: string) {
  const addition = spoken.replace(/\s+/g, " ").trim();
  if (!addition) return current;
  if (!current) return addition;
  return /\s$/.test(current) ? current + addition : `${current} ${addition}`;
}

function logVoice(location: string, message: string, data: Record<string, unknown>, hypothesisId: string) {
  // #region agent log
  fetch("http://127.0.0.1:7538/ingest/6f030dbc-997f-4bbb-bb1f-a9b253a980e2", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "f3ff1c" },
    body: JSON.stringify({
      sessionId: "f3ff1c",
      location,
      message,
      data,
      timestamp: Date.now(),
      hypothesisId,
      runId: "voice-fallback",
    }),
  }).catch(() => {});
  // #endregion
}

let stopActive: (() => void) | null = null;
let transcriberPromise: Promise<Transcriber> | null = null;

async function localTranscriber(): Promise<Transcriber> {
  if (!transcriberPromise) {
    transcriberPromise = (async () => {
      const dynamicImport = new Function("url", "return import(url)") as (url: string) => Promise<{
        pipeline: (task: string, model: string) => Promise<Transcriber>;
        env: {
          allowLocalModels: boolean;
          backends: { onnx: { wasm: { numThreads: number; wasmPaths: string } } };
        };
      }>;
      const mod = await dynamicImport("https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2");
      mod.env.allowLocalModels = false;
      mod.env.backends.onnx.wasm.numThreads = 1;
      mod.env.backends.onnx.wasm.wasmPaths =
        "https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2/dist/";
      return mod.pipeline("automatic-speech-recognition", "Xenova/whisper-tiny.en");
    })().catch((error) => {
      transcriberPromise = null;
      throw error;
    });
  }
  return transcriberPromise;
}

async function blobTo16kMono(blob: Blob): Promise<Float32Array> {
  const audioCtx = new AudioContext();
  const decoded = await audioCtx.decodeAudioData(await blob.arrayBuffer());
  const rate = 16000;
  const offline = new OfflineAudioContext(1, Math.max(1, Math.ceil(decoded.duration * rate)), rate);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start();
  const rendered = await offline.startRendering();
  await audioCtx.close();
  return rendered.getChannelData(0);
}

export function VoiceControl({
  value,
  onChange,
  children,
}: {
  value: string;
  onChange: (next: string) => void;
  children: React.ReactNode;
}) {
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const recRef = useRef<BrowserRecognition | null>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const heardSpeech = useRef(false);
  const [listening, setListening] = useState(false);
  const [hint, setHint] = useState("");

  valueRef.current = value;
  onChangeRef.current = onChange;

  useEffect(() => {
    return () => {
      recRef.current?.stop();
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  function stopTracks() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }

  async function transcribeRecording() {
    const rec = mediaRef.current;
    const mime = rec?.mimeType || "audio/webm";
    const blob = await new Promise<Blob>((resolve) => {
      if (!rec || rec.state === "inactive") {
        resolve(new Blob(chunksRef.current, { type: mime }));
        return;
      }
      rec.onstop = () => resolve(new Blob(chunksRef.current, { type: mime }));
      rec.stop();
    });
    mediaRef.current = null;
    stopTracks();
    if (blob.size < 1000) return "";
    setHint("Transcribing…");
    const samples = await blobTo16kMono(blob);
    const transcriber = await localTranscriber();
    const result = await transcriber(samples);
    return cleanTranscript(result.text || "");
  }

  async function stopListening() {
    recRef.current?.stop();
    const useRecording = !heardSpeech.current;
    setListening(false);
    if (!useRecording) {
      if (mediaRef.current && mediaRef.current.state !== "inactive") mediaRef.current.stop();
      stopTracks();
      setHint("");
      return;
    }
    try {
      const text = await transcribeRecording();
      logVoice("VoiceControl.tsx:fallback", "local transcript", { chars: text.length }, "D");
      if (text) onChangeRef.current(joinText(valueRef.current, text));
      setHint(text ? "" : "No words were heard. You can keep typing.");
    } catch {
      logVoice("VoiceControl.tsx:fallback", "local transcript failed", { chars: 0 }, "D");
      stopTracks();
      setHint("Voice could not transcribe that. You can keep typing.");
    }
  }

  async function toggle() {
    if (listening) {
      await stopListening();
      return;
    }
    heardSpeech.current = false;
    chunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      mediaRef.current = recorder;
      recorder.start();
    } catch {
      setHint("Allow the microphone to use voice. Typing still works.");
      logVoice("VoiceControl.tsx:mic", "microphone denied", { available: false }, "C");
      return;
    }

    stopActive?.();
    const Ctor = recognitionCtor();
    if (Ctor) {
      const rec = new Ctor();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = navigator.language || "en-US";
      rec.onresult = (event) => {
        let finalChunk = "";
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const piece = event.results[i][0]?.transcript || "";
          if (event.results[i].isFinal) finalChunk += piece;
          else interim += piece;
        }
        if (finalChunk.trim()) {
          heardSpeech.current = true;
          onChangeRef.current(joinText(valueRef.current, finalChunk));
        }
        setHint(interim.trim() ? interim.trim() : "Listening…");
        logVoice(
          "VoiceControl.tsx:onresult",
          "speech result",
          { finalChars: finalChunk.trim().length, interimChars: interim.trim().length },
          "B"
        );
      };
      rec.onerror = (event) => {
        const code = event.error || "unknown";
        logVoice("VoiceControl.tsx:onerror", "speech error", { code }, "C");
        if (code === "network" || code === "service-not-allowed") {
          setHint("Listening… words are added when you stop.");
          return;
        }
        if (code === "not-allowed") {
          setHint("Allow the microphone to use voice. Typing still works.");
        }
      };
      rec.onend = () => {
        if (stopActive === stop) stopActive = null;
      };
      const stop = () => {
        try {
          rec.stop();
        } catch {
          /* already stopped */
        }
      };
      recRef.current = rec;
      stopActive = stop;
      try {
        rec.start();
        logVoice("VoiceControl.tsx:start", "speech started", { available: true }, "A");
      } catch {
        logVoice("VoiceControl.tsx:start", "speech start failed", { available: true }, "A");
      }
    } else {
      logVoice("VoiceControl.tsx:toggle", "speech recognition missing", { available: false }, "A");
    }
    setListening(true);
    setHint("Listening…");
  }

  return (
    <div className="voice-control">
      <div className="voice-control-input">{children}</div>
      <div className="voice-side">
        <button
          type="button"
          className={listening ? "voice-btn listening" : "voice-btn"}
          aria-pressed={listening}
          onClick={() => {
            void toggle();
          }}
        >
          {listening ? "Stop voice" : "Voice"}
        </button>
        {hint && <span className="voice-hint">{hint}</span>}
      </div>
    </div>
  );
}
