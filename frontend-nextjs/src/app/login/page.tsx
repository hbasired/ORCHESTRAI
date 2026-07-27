'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function LoginPage() {
    const router = useRouter();
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const [mode, setMode] = useState<'credentials' | 'face' | 'register'>('credentials');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [cameraActive, setCameraActive] = useState(false);
    const [capturedImage, setCapturedImage] = useState<string | null>(null);

    // Start camera for face recognition
    const startCamera = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: 640, height: 480 }
            });
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                // Wait for video to be ready before marking camera as active
                videoRef.current.onloadedmetadata = () => {
                    videoRef.current?.play().then(() => {
                        setCameraActive(true);
                    }).catch(err => {
                        console.error('Video play error:', err);
                        setCameraActive(true); // Still mark as active even if autoplay fails
                    });
                };
            }
        } catch (err) {
            setError('Camera access denied. Please allow camera permissions.');
            console.error('Camera error:', err);
        }
    }, []);

    const stopCamera = useCallback(() => {
        if (videoRef.current?.srcObject) {
            const stream = videoRef.current.srcObject as MediaStream;
            stream.getTracks().forEach(track => track.stop());
            videoRef.current.srcObject = null;
            setCameraActive(false);
        }
    }, []);

    // Capture frame from video
    const captureFrame = useCallback((): string | null => {
        if (!videoRef.current || !canvasRef.current) return null;

        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');

        if (!ctx) return null;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0);

        return canvas.toDataURL('image/jpeg', 0.9);
    }, []);

    // Handle credential login
    const handleCredentialLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await fetch(`${API_URL}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (data.success) {
                localStorage.setItem('auth_token', data.token);
                localStorage.setItem('username', data.username);
                router.push('/');
            } else {
                setError(data.detail || 'Login failed');
            }
        } catch (err) {
            setError('Connection error. Please check if the server is running.');
        } finally {
            setLoading(false);
        }
    };

    // Handle face login
    const handleFaceLogin = async () => {
        setError('');
        setLoading(true);

        const imageData = captureFrame();
        if (!imageData) {
            setError('Failed to capture image');
            setLoading(false);
            return;
        }

        setCapturedImage(imageData);

        try {
            const response = await fetch(`${API_URL}/api/auth/login/face`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_data: imageData })
            });

            const data = await response.json();

            if (data.success) {
                localStorage.setItem('auth_token', data.token);
                localStorage.setItem('username', data.username);
                stopCamera();
                router.push('/');
            } else {
                setError(data.detail || 'Face not recognized');
                setCapturedImage(null);
            }
        } catch (err) {
            setError('Connection error. Please check if the server is running.');
            setCapturedImage(null);
        } finally {
            setLoading(false);
        }
    };

    // Handle registration with face
    const handleRegisterWithFace = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!username || !password) {
            setError('Username and password are required');
            return;
        }

        if (password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        setLoading(true);

        const imageData = cameraActive ? captureFrame() : null;

        try {
            const response = await fetch(`${API_URL}/api/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username,
                    password,
                    face_image: imageData
                })
            });

            const data = await response.json();

            if (data.success) {
                localStorage.setItem('auth_token', data.token);
                localStorage.setItem('username', data.username);
                stopCamera();
                router.push('/');
            } else {
                setError(data.detail || 'Registration failed');
            }
        } catch (err) {
            setError('Connection error. Please check if the server is running.');
        } finally {
            setLoading(false);
        }
    };

    // Start camera when switching to face mode
    useEffect(() => {
        if (mode === 'face' || (mode === 'register' && cameraActive)) {
            startCamera();
        } else {
            stopCamera();
        }

        return () => stopCamera();
    }, [mode, startCamera, stopCamera]);

    return (
        <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center p-4">
            {/* Background grid */}
            <div className="absolute inset-0 grid-pattern opacity-20" />

            {/* Login container */}
            <div className="relative z-10 w-full max-w-md">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center gap-3 mb-4">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center">
                            <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <h1 className="text-2xl font-bold text-white">AI Embodied Agent</h1>
                    </div>
                    <p className="text-gray-400">Unified Intelligence for Manufacturing</p>
                </div>

                {/* Mode tabs */}
                <div className="flex gap-2 mb-6">
                    <button
                        onClick={() => setMode('credentials')}
                        className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all ${mode === 'credentials'
                            ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                            : 'bg-[#141a26] text-gray-400 hover:text-white'
                            }`}
                    >
                        Credentials
                    </button>
                    <button
                        onClick={() => setMode('face')}
                        className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all ${mode === 'face'
                            ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                            : 'bg-[#141a26] text-gray-400 hover:text-white'
                            }`}
                    >
                        Face Scan
                    </button>
                    <button
                        onClick={() => setMode('register')}
                        className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all ${mode === 'register'
                            ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                            : 'bg-[#141a26] text-gray-400 hover:text-white'
                            }`}
                    >
                        Register
                    </button>
                </div>

                {/* Login card */}
                <div className="glass p-6 rounded-2xl">
                    {/* Error message */}
                    {error && (
                        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    {/* Credentials mode */}
                    {mode === 'credentials' && (
                        <form onSubmit={handleCredentialLogin} className="space-y-4">
                            <div>
                                <label className="block text-sm text-gray-400 mb-2">Username</label>
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="w-full bg-[#1c2333] border border-[#2a3444] rounded-lg px-4 py-3 text-white focus:border-cyan-500 focus:outline-none"
                                    placeholder="Enter username"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm text-gray-400 mb-2">Password</label>
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full bg-[#1c2333] border border-[#2a3444] rounded-lg px-4 py-3 text-white focus:border-cyan-500 focus:outline-none"
                                    placeholder="Enter password"
                                    required
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full py-3 rounded-lg font-semibold bg-gradient-to-r from-cyan-500 to-purple-500 text-white hover:shadow-lg hover:shadow-cyan-500/25 transition-all disabled:opacity-50"
                            >
                                {loading ? 'Signing in...' : 'Sign In'}
                            </button>
                        </form>
                    )}

                    {/* Face recognition mode */}
                    {mode === 'face' && (
                        <div className="space-y-4">
                            <div className="relative aspect-video bg-[#1c2333] rounded-lg overflow-hidden">
                                {/* Always render video element so we can assign srcObject */}
                                <video
                                    ref={videoRef}
                                    autoPlay
                                    playsInline
                                    muted
                                    className={`w-full h-full object-cover ${cameraActive ? 'opacity-100' : 'opacity-0'}`}
                                />

                                {/* Face guide overlay - only show when camera is active */}
                                {cameraActive && (
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <div className="w-48 h-48 border-2 border-cyan-400 rounded-full opacity-50" />
                                    </div>
                                )}

                                {/* Loading text - show when camera not yet active */}
                                {!cameraActive && (
                                    <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                                        <span>Camera loading...</span>
                                    </div>
                                )}

                                {capturedImage && (
                                    <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                                        <div className="text-center">
                                            <div className="animate-spin w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto mb-2" />
                                            <span className="text-cyan-400">Verifying...</span>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <button
                                onClick={handleFaceLogin}
                                disabled={loading || !cameraActive}
                                className="w-full py-3 rounded-lg font-semibold bg-gradient-to-r from-cyan-500 to-purple-500 text-white hover:shadow-lg hover:shadow-cyan-500/25 transition-all disabled:opacity-50"
                            >
                                {loading ? 'Scanning...' : 'Scan Face to Login'}
                            </button>

                            <p className="text-center text-sm text-gray-500">
                                Position your face within the circle
                            </p>
                        </div>
                    )}

                    {/* Register mode */}
                    {mode === 'register' && (
                        <form onSubmit={handleRegisterWithFace} className="space-y-4">
                            <div>
                                <label className="block text-sm text-gray-400 mb-2">Username</label>
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="w-full bg-[#1c2333] border border-[#2a3444] rounded-lg px-4 py-3 text-white focus:border-purple-500 focus:outline-none"
                                    placeholder="Choose a username"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm text-gray-400 mb-2">Password</label>
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full bg-[#1c2333] border border-[#2a3444] rounded-lg px-4 py-3 text-white focus:border-purple-500 focus:outline-none"
                                    placeholder="Choose a password (min 6 chars)"
                                    required
                                    minLength={6}
                                />
                            </div>

                            {/* Optional face capture */}
                            <div>
                                <div className="flex items-center justify-between mb-2">
                                    <label className="text-sm text-gray-400">Register Face (Optional)</label>
                                    <button
                                        type="button"
                                        onClick={() => cameraActive ? stopCamera() : startCamera()}
                                        className="text-sm text-purple-400 hover:text-purple-300"
                                    >
                                        {cameraActive ? 'Stop Camera' : 'Enable Camera'}
                                    </button>
                                </div>

                                {cameraActive && (
                                    <div className="relative aspect-video bg-[#1c2333] rounded-lg overflow-hidden">
                                        <video
                                            ref={videoRef}
                                            autoPlay
                                            playsInline
                                            muted
                                            className="w-full h-full object-cover"
                                        />
                                        <div className="absolute inset-0 flex items-center justify-center">
                                            <div className="w-32 h-32 border-2 border-purple-400 rounded-full opacity-50" />
                                        </div>
                                    </div>
                                )}
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full py-3 rounded-lg font-semibold bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:shadow-lg hover:shadow-purple-500/25 transition-all disabled:opacity-50"
                            >
                                {loading ? 'Creating account...' : 'Create Account'}
                            </button>
                        </form>
                    )}
                </div>

                {/* Hidden canvas for capturing */}
                <canvas ref={canvasRef} className="hidden" />

                {/* Footer */}
                <p className="text-center text-sm text-gray-500 mt-6">
                    Manufacturing Intelligence Platform v2.0
                </p>
            </div>
        </div>
    );
}
