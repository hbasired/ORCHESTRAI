"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Float, Environment, Text } from "@react-three/drei";
import { Suspense, useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface StageProps {
    position: [number, number, number];
    name: string;
    queueDepth: number;
    status: string;
    index: number;
}

function Stage({ position, name, queueDepth, status, index }: StageProps) {
    const meshRef = useRef<THREE.Mesh>(null);

    const color = useMemo(() => {
        if (status === "maintenance") return "#ffaa00";
        if (queueDepth > 25) return "#ff3366";
        if (queueDepth > 15) return "#ffcc00";
        return "#00ff88";
    }, [queueDepth, status]);

    useFrame((state) => {
        if (meshRef.current && status === "running") {
            meshRef.current.rotation.y = state.clock.elapsedTime * 0.2;
        }
    });

    return (
        <group position={position}>
            {/* Stage platform */}
            <mesh position={[0, 0.1, 0]}>
                <boxGeometry args={[6, 0.2, 4]} />
                <meshStandardMaterial color="#1c2333" />
            </mesh>

            {/* Machine body */}
            <mesh position={[0, 1.5, 0]}>
                <boxGeometry args={[4, 2, 3]} />
                <meshStandardMaterial color={color} emissive={color} emissiveIntensity={status === "running" ? 0.3 : 0.1} />
            </mesh>

            {/* Rotating element */}
            <mesh ref={meshRef} position={[0, 3, 0]}>
                <cylinderGeometry args={[0.5, 0.5, 0.3, 8]} />
                <meshStandardMaterial color="#00f0ff" emissive="#00f0ff" emissiveIntensity={0.5} />
            </mesh>

            {/* Queue visualization */}
            {Array.from({ length: Math.min(queueDepth, 10) }, (_, i) => (
                <mesh key={i} position={[-3 + i * 0.5, 0.5, 2]}>
                    <boxGeometry args={[0.3, 0.3, 0.3]} />
                    <meshStandardMaterial color="#7b2ff7" />
                </mesh>
            ))}

            {/* Status light */}
            <pointLight position={[0, 4, 0]} color={color} intensity={0.5} distance={10} />
        </group>
    );
}

function ConveyorBelt({ start, end }: { start: [number, number, number]; end: [number, number, number] }) {
    const length = Math.sqrt(
        Math.pow(end[0] - start[0], 2) + Math.pow(end[2] - start[2], 2)
    );
    const midPoint: [number, number, number] = [
        (start[0] + end[0]) / 2,
        0.3,
        (start[2] + end[2]) / 2
    ];

    return (
        <mesh position={midPoint}>
            <boxGeometry args={[length, 0.1, 0.5]} />
            <meshStandardMaterial color="#2a3444" />
        </mesh>
    );
}

interface FactoryProps {
    stages: Array<{ id: number; name: string; queue_depth: number; status: string }>;
}

function Factory({ stages }: FactoryProps) {
    return (
        <>
            {/* Floor */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
                <planeGeometry args={[200, 100]} />
                <meshStandardMaterial color="#0a0e17" />
            </mesh>

            {/* Grid overlay */}
            <gridHelper args={[200, 40, "#1c2333", "#141a26"]} position={[0, 0.01, 0]} />

            {/* Production stages arranged in a line */}
            {stages.map((stage, index) => (
                <Stage
                    key={stage.id}
                    index={index}
                    position={[-40 + index * 10, 0, 0]}
                    name={stage.name}
                    queueDepth={stage.queue_depth}
                    status={stage.status}
                />
            ))}

            {/* Conveyor belts between stages */}
            {stages.slice(0, -1).map((_, i) => (
                <ConveyorBelt
                    key={i}
                    start={[-36 + i * 10, 0, 0]}
                    end={[-44 + (i + 1) * 10, 0, 0]}
                />
            ))}

            {/* Ambient lighting */}
            <ambientLight intensity={0.4} />
            <directionalLight position={[20, 30, 10]} intensity={0.6} />

            {/* Overhead lights */}
            {[-30, 0, 30].map((x, i) => (
                <pointLight key={i} position={[x, 15, 0]} color="#ffffff" intensity={0.3} distance={40} />
            ))}
        </>
    );
}

export default function FactoryScene({ stages = [] }: FactoryProps) {
    return (
        <div className="w-full h-full min-h-[600px] overflow-hidden rounded-xl">
            <Canvas camera={{ position: [0, 30, 50], fov: 60 }}>
                <Suspense fallback={null}>
                    <Factory stages={stages} />
                    <Environment preset="warehouse" />
                    <OrbitControls
                        enablePan={true}
                        enableZoom={true}
                        enableRotate={true}
                        maxPolarAngle={Math.PI / 2.2}
                        minDistance={20}
                        maxDistance={100}
                    />
                </Suspense>
            </Canvas>
        </div>
    );
}
