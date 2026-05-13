import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import svgr from 'vite-plugin-svgr'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // Base path for hosting under a subdirectory. Default `/` for the standalone
  // build served by frontend_1 on port 7010. Set to `/live/` when this app is
  // embedded inside the stats_app container at port 7012 — see
  // stats_app/Dockerfile and stats_app/nginx.conf.
  const base = process.env.VITE_BASE_URL || env.VITE_BASE_URL || '/'

  return {
    base,
    define: {
      'process.env.REACT_APP_API_URL': JSON.stringify(env.REACT_APP_API_URL || '/api'),
    },
    plugins: [svgr({ svgrOptions: { exportType: 'default' } }), react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
        },
      },
    },
    server: {
      host: true,
      port: 3000,
      proxy: {
        '/api': {
          target: env.VITE_CRCON_API_URL || env.REACT_APP_API_URL,
          changeOrigin: true,
        },
      },
    },
  }
})
