import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    server: {
        port: 5173,
        proxy: {
            '/admin': {
                target: 'http://localhost:8002',
                changeOrigin: true
            },
            '/v1': {
                target: 'http://localhost:8002',
                changeOrigin: true
            },
            '/health': {
                target: 'http://localhost:8002',
                changeOrigin: true
            }
        }
    },
    build: {
        outDir: 'dist',
        emptyOutDir: true,
        rollupOptions: {
            output: {
                manualChunks: {
                    'vendor': ['vue', 'vue-router', 'pinia'],
                    'ui': ['radix-vue', 'lucide-vue-next'],
                    'charts': ['chart.js', 'vue-chartjs']
                }
            }
        }
    }
});
