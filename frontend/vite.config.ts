import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
export default defineConfig({plugins:[react()],server:{port:5173},preview:{port:4173},test:{include:['src/**/*.test.ts','src/**/*.test.tsx'],environment:'jsdom',setupFiles:'./src/test/setup.ts',coverage:{provider:'v8',reporter:['text'],include:['src/App.tsx','src/api.ts'],thresholds:{lines:80}}}})
