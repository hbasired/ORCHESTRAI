'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';

// Routes that don't require authentication
const publicRoutes = ['/login', '/landing'];

interface AuthCheckProps {
    children: React.ReactNode;
}

export default function AuthCheck({ children }: AuthCheckProps) {
    const router = useRouter();
    const pathname = usePathname();
    const [isChecking, setIsChecking] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    useEffect(() => {
        // Check if current route is public
        if (publicRoutes.some(route => pathname?.startsWith(route))) {
            setIsChecking(false);
            setIsAuthenticated(true);
            return;
        }

        // Check for auth token in localStorage
        const token = localStorage.getItem('auth_token');

        if (!token) {
            // Redirect to landing instead of login
            router.push('/landing');
            return;
        }

        // Optionally verify token with backend
        setIsAuthenticated(true);
        setIsChecking(false);
    }, [pathname, router]);

    if (isChecking) {
        return (
            <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                    <p className="text-gray-400">Authenticating...</p>
                </div>
            </div>
        );
    }

    if (!isAuthenticated && !publicRoutes.some(route => pathname?.startsWith(route))) {
        return null;
    }

    return <>{children}</>;
}
