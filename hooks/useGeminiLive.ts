import { useState, useEffect, useRef, useCallback } from 'react';
import { GoogleGenAI, LiveServerMessage, Modality } from '@google/genai';
import { LogEntry, MessageSource, ActiveToolState } from '../types';
import { SYSTEM_INSTRUCTION, TOOLS, MOCK_GITHUB_DATA, MOCK_LOGS_DATA } from '../constants';
import { blobToBase64, createPcmBlob, decodeAudioData, encodePcm } from '../utils/audio';

export const useGeminiLive = () => {
  const [connected, setConnected] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [volume, setVolume] = useState(0);
  const [activeTool, setActiveTool] = useState<ActiveToolState | null>(null);

  // Refs for audio handling to avoid re-renders
  const audioContextRef = useRef<AudioContext | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const sessionRef = useRef<any>(null); // To store the active session promise
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());

  const addLog = useCallback((source: MessageSource, text: string, metadata?: any) => {
    setLogs(prev => [...prev, {
      id: Math.random().toString(36).substring(7),
      timestamp: new Date(),
      source,
      text,
      metadata
    }]);
  }, []);

  const handleToolCall = async (functionCalls: any[]) => {
    const responses = [];
    for (const call of functionCalls) {
        addLog(MessageSource.SYSTEM, `Intercepted Tool Call: ${call.name}`, call.args);
        setActiveTool({ name: call.name, startTime: Date.now() });

        // Simulate network delay for realism
        await new Promise(resolve => setTimeout(resolve, 1500));

        let result;
        if (call.name === 'check_github_pr') {
            result = MOCK_GITHUB_DATA;
        } else if (call.name === 'check_gcp_logs') {
            result = { logs: MOCK_LOGS_DATA(call.args.service || 'unknown-service') };
        } else if (call.name === 'restart_cloud_run_service') {
            result = { status: "OK", revision: "v20240124-002", message: "Service restarting..." };
        } else {
            result = { error: "Unknown tool" };
        }

        addLog(MessageSource.TOOL, `Tool Output (${call.name})`, result);
        responses.push({
            id: call.id,
            name: call.name,
            response: { result }
        });
        setActiveTool(null);
    }
    return responses;
  };

  const connect = async () => {
    try {
      addLog(MessageSource.SYSTEM, "Initializing Gemini Live Uplink...");
      
      const apiKey = process.env.API_KEY;
      if (!apiKey) {
        throw new Error("API_KEY not found in environment.");
      }

      const ai = new GoogleGenAI({ apiKey });
      
      // Setup Audio Contexts
      inputContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      
      // Start Microphone
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Connect to Gemini
      // Note: Gemini 3 Flash does not yet support the Live API (bidiGenerateContent).
      // We must use the specific 2.5 Native Audio model for real-time WebRTC/WebSocket interactions.
      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-12-2025',
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction: SYSTEM_INSTRUCTION,
          tools: [{ functionDeclarations: TOOLS }],
          inputAudioTranscription: {}, 
          outputAudioTranscription: {},
        },
        callbacks: {
          onopen: () => {
            setConnected(true);
            addLog(MessageSource.SYSTEM, "Uplink Established. Audio Stream Active.");
            
            // Setup Audio Processing for Input
            if (!inputContextRef.current) return;
            const source = inputContextRef.current.createMediaStreamSource(stream);
            const processor = inputContextRef.current.createScriptProcessor(4096, 1, 1);
            
            processor.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              // Calculate volume for visualizer
              let sum = 0;
              for (let i = 0; i < inputData.length; i++) {
                sum += inputData[i] * inputData[i];
              }
              setVolume(Math.sqrt(sum / inputData.length));

              // Send to Gemini
              const pcmBlob = createPcmBlob(inputData);
              sessionPromise.then(session => {
                session.sendRealtimeInput({ media: pcmBlob });
              });
            };

            source.connect(processor);
            processor.connect(inputContextRef.current.destination);
            
            sourceRef.current = source;
            processorRef.current = processor;
          },
          onmessage: async (message: LiveServerMessage) => {
             // Handle Transcriptions
             if (message.serverContent?.inputTranscription?.text) {
                 addLog(MessageSource.USER, message.serverContent.inputTranscription.text);
             }
            //  if (message.serverContent?.outputTranscription?.text) {
                 // Optionally log partial agent text, but it might be noisy. 
                 // We will wait for turnComplete or rely on audio.
            //  }

             // Handle Tool Calls
             if (message.toolCall) {
                const responses = await handleToolCall(message.toolCall.functionCalls);
                sessionPromise.then(session => {
                    session.sendToolResponse({ functionResponses: responses });
                });
             }

             // Handle Audio Output
             const audioData = message.serverContent?.modelTurn?.parts?.[0]?.inlineData?.data;
             if (audioData && audioContextRef.current) {
                 const ctx = audioContextRef.current;
                 nextStartTimeRef.current = Math.max(nextStartTimeRef.current, ctx.currentTime);
                 
                 const audioBuffer = await decodeAudioData(
                    decodeAtob(audioData),
                    ctx,
                    24000,
                    1
                 );
                 
                 const source = ctx.createBufferSource();
                 source.buffer = audioBuffer;
                 source.connect(ctx.destination);
                 source.addEventListener('ended', () => {
                     sourcesRef.current.delete(source);
                 });
                 source.start(nextStartTimeRef.current);
                 nextStartTimeRef.current += audioBuffer.duration;
                 sourcesRef.current.add(source);
             }

             // Handle Turn Complete (Logging the final agent response if available in text)
             if (message.serverContent?.turnComplete) {
                // Not always guaranteed to have text here, but good trigger point
             }
          },
          onclose: () => {
             setConnected(false);
             addLog(MessageSource.SYSTEM, "Uplink Closed.");
          },
          onerror: (err) => {
             console.error(err);
             addLog(MessageSource.SYSTEM, "Error: " + err.message);
          }
        }
      });
      sessionRef.current = sessionPromise;

    } catch (err: any) {
      addLog(MessageSource.SYSTEM, `Connection Failed: ${err.message}`);
      setConnected(false);
    }
  };

  const disconnect = () => {
    if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
    }
    if (processorRef.current && inputContextRef.current) {
        processorRef.current.disconnect();
        inputContextRef.current.close();
    }
    if (audioContextRef.current) {
        audioContextRef.current.close();
    }
    // Stop playing sources
    sourcesRef.current.forEach(source => source.stop());
    sourcesRef.current.clear();
    
    // There is no explicit .close() on sessionPromise session object in the example, 
    // but stopping audio stream triggers end of interaction usually.
    // However, if we had access to the session object we could try to send a close signal.
    // For now, we reset state.
    setConnected(false);
    addLog(MessageSource.SYSTEM, "Disconnected by user.");
  };

  return {
    connected,
    connect,
    disconnect,
    volume,
    logs,
    activeTool
  };
};

// Helper for decoding manually since system instruction bans external libs for this
function decodeAtob(base64: string) {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
}