"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Grid, Float, Environment, Text } from "@react-three/drei";
import { Suspense, useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface RobotProps {
    position: [number, number, number];
    status: string;
    id: number;
    battery: number;
}

function Robot({ position, status, id, battery }: RobotProps) {
    const meshRef = useRef<THREE.Mesh>(null);

    // Color based on status
    const color = useMemo(() => {
        if (status === "error") return "#ff3366";
        if (status === "warning" || battery < 20) return "#ffcc00";
        if (status === "charging") return "#7b2ff7";
        return "#00ff88";
    }, [status, battery]);

    useFrame((state) => {
        if (meshRef.current) {
            meshRef.current.position.y = Math.sin(state.clock.elapsedTime * 2 + id) * 0.1 + 0.3;
        }
    });

    return (
        <group position={position}>
            {/* Robot body */}
            <mesh ref={meshRef} position={[0, 0.3, 0]}>
                <boxGeometry args={[0.8, 0.4, 0.6]} />
                <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} />
            </mesh>

            {/* Wheels */}
            {[[-0.4, 0, -0.3], [-0.4, 0, 0.3], [0.4, 0, -0.3], [0.4, 0, 0.3]].map((pos, i) => (
                <mesh key={i} position={pos as [number, number, number]} rotation={[Math.PI / 2, 0, 0]}>
                    <cylinderGeometry args={[0.1, 0.1, 0.05, 16]} />
                    <meshStandardMaterial color="#1c2333" />
                </mesh>
            ))}

            {/* Status light */}
            <pointLight position={[0, 0.6, 0]} color={color} intensity={0.5} distance={2} />

            {/* Battery indicator */}
            <mesh position={[0, 0.6, 0]}>
                <boxGeometry args={[battery / 100 * 0.6, 0.05, 0.1]} />
                <meshStandardMaterial color={battery < 20 ? "#ff3366" : "#00ff88"} />
            </mesh>
        </group>
    );
}

interface WarehouseProps {
    robots: Array<{ id: number; position_x: number; position_y: number; battery: number; status: string }>;
}

function Warehouse({ robots }: WarehouseProps) {
    return (
        <>
            {/* Floor */}
            <Grid
                infiniteGrid
                cellSize={2}
                cellThickness={0.5}
                sectionSize={10}
                sectionThickness={1}
                sectionColor="#00f0ff"
                cellColor="#2a3444"
                fadeDistance={50}
                fadeStrength={1}
            />

            {/* Warehouse walls */}
            <mesh position={[-50, 5, 0]} rotation={[0, Math.PI / 2, 0]}>
                <planeGeometry args={[100, 10]} />
                <meshStandardMaterial color="#1c2333" transparent opacity={0.3} />
            </mesh>
            <mesh position={[50, 5, 0]} rotation={[0, -Math.PI / 2, 0]}>
                <planeGeometry args={[100, 10]} />
                <meshStandardMaterial color="#1c2333" transparent opacity={0.3} />
            </mesh>

            {/* Charging stations */}
            {[[-40, 0, 40], [-35, 0, 40], [-30, 0, 40], [-25, 0, 40]].map((pos, i) => (
                <Float key={i} speed={1} floatIntensity={0.5}>
                    <mesh position={pos as [number, number, number]}>
                        <cylinderGeometry args={[1, 1, 0.2, 32]} />
                        <meshStandardMaterial color="#7b2ff7" emissive="#7b2ff7" emissiveIntensity={0.3} />
                    </mesh>
                </Float>
            ))}

            {/* Shelving units */}
            {Array.from({ length: 8 }, (_, row) =>
                Array.from({ length: 5 }, (_, col) => (
                    <group key={`shelf-${row}-${col}`} position={[-30 + row * 10, 0, -30 + col * 12]}>
                        {/* Shelf frame */}
                        <mesh position={[0, 2, 0]}>
                            <boxGeometry args={[6, 4, 1]} />
                            <meshStandardMaterial color="#1c2333" />
                        </mesh>
                        {/* Shelf glow */}
                        <pointLight position={[0, 3, 1]} color="#00f0ff" intensity={0.2} distance={5} />
                    </group>
                ))
            )}

            {/* Robots */}
            {robots.map((robot) => (
                <Robot
                    key={robot.id}
                    id={robot.id}
                    position={[(robot.position_x - 50), 0, (robot.position_y - 50)]}
                    status={robot.status}
                    battery={robot.battery}
                />
            ))}

            {/* Ambient lighting */}
            <ambientLight intensity={0.3} />
            <directionalLight position={[10, 20, 10]} intensity={0.5} />
        </>
    );
}

export default function WarehouseScene({ robots = [] }: WarehouseProps) {
    return (
        <div className="w-full h-full min-h-[600px] overflow-hidden rounded-xl">
            <Canvas camera={{ position: [50, 40, 50], fov: 60 }}>
                <Suspense fallback={null}>
                    <Warehouse robots={robots} />
                    <Environment preset="night" />
                    <OrbitControls
                        enablePan={true}
                        enableZoom={true}
                        enableRotate={true}
                        maxPolarAngle={Math.PI / 2.2}
                        minDistance={10}
                        maxDistance={100}
                    />
                </Suspense>
            </Canvas>
        </div>
    );
}
