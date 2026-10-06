/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// 노트북 페이지 서버가 뿌리(/)에서 낸다(CCR-INFRA-001 8.11)
export default defineConfig({
  base: '/',
  plugins: [react()],
  test: {
    include: ['tests/**/*.test.ts'],
    environment: 'node',
  },
})
