/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Pages 하위 경로. 저장소 이름이 바뀌면 여기만 고친다(CCR-INFRA-001 4.1)
export default defineConfig({
  base: '/competition-crawler/',
  plugins: [react()],
  test: {
    include: ['tests/**/*.test.ts'],
    environment: 'node',
  },
})
