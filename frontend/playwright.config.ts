import { defineConfig } from '@playwright/test'
export default defineConfig({ testDir:'./tests', timeout:45000, workers:1, use:{baseURL:'http://127.0.0.1:5173', headless:true, launchOptions:{channel:'chromium'}, screenshot:'only-on-failure'}, reporter:'list' })
