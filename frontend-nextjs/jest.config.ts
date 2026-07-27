import type { Config } from "jest";
import nextJest from "next/jest";

const createJestConfig = nextJest({
    dir: "./",
});

const config: Config = {
    testEnvironment: "jsdom",
    testMatch: ["**/__tests__/**/*.test.(ts|tsx|js|jsx)"],
    moduleNameMapper: {
        "^@/(.*)$": "<rootDir>/src/$1",
    },
};

export default createJestConfig(config);
