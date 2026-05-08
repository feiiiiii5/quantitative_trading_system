<template>
  <div class="login-page">
    <div class="login-ambient">
      <div class="ambient-grid" />
      <div class="ambient-scanline" />
    </div>
    <div class="login-card" :class="{ 'shake': errorShaking }">
      <div class="card-glow" />
      <div class="card-header">
        <div class="brand-mark">
          <span class="brand-glyph">QC</span>
        </div>
        <div class="brand-title">QUANTCORE</div>
        <div class="brand-sub">SECURE TERMINAL ACCESS</div>
      </div>
      <div class="card-divider" />
      <form class="login-form" @submit.prevent="handleLogin">
        <div class="field">
          <label class="field-label">
            <span class="label-prompt">&gt;</span> USERNAME
          </label>
          <div class="input-wrap">
            <input
              v-model="username"
              class="field-input"
              type="text"
              autocomplete="username"
              spellcheck="false"
              placeholder="operator_id"
            />
            <span class="input-cursor" />
          </div>
        </div>
        <div class="field">
          <label class="field-label">
            <span class="label-prompt">&gt;</span> PASSWORD
          </label>
          <div class="input-wrap">
            <input
              v-model="password"
              class="field-input"
              type="password"
              autocomplete="current-password"
              placeholder="••••••••"
            />
            <span class="input-cursor" />
          </div>
        </div>
        <div v-if="error" class="login-error">
          <span class="error-indicator">!</span>
          {{ error }}
        </div>
        <button class="login-btn" type="submit" :disabled="submitting">
          <span v-if="submitting" class="btn-loading">
            <span class="loading-bar" />
            CONNECTING
          </span>
          <span v-else>AUTHENTICATE &rarr;</span>
        </button>
      </form>
      <div class="card-footer">
        <span class="footer-status">
          <span class="status-dot" />
          SYSTEM ONLINE
        </span>
        <span class="footer-version">v3.2.1</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)
const errorShaking = ref(false)

async function handleLogin() {
  error.value = ''
  errorShaking.value = false
  if (!username.value.trim() || !password.value) {
    error.value = 'ALL FIELDS REQUIRED'
    triggerShake()
    return
  }
  submitting.value = true
  try {
    await authStore.login(username.value.trim(), password.value)
    router.push('/')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'AUTH FAILED'
    error.value = msg.toUpperCase()
    triggerShake()
  } finally {
    submitting.value = false
  }
}

function triggerShake() {
  errorShaking.value = true
  setTimeout(() => { errorShaking.value = false }, 400)
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(170deg, #050507 0%, #0d0d1a 100%);
  position: relative;
  overflow: hidden;
}

.login-ambient {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.ambient-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(41, 121, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(41, 121, 255, 0.03) 1px, transparent 1px);
  background-size: 48px 48px;
}

.ambient-scanline {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(255, 255, 255, 0.008) 2px,
    rgba(255, 255, 255, 0.008) 4px
  );
}

.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 380px;
  padding: 32px 28px 24px;
  border: 1px solid var(--border-mid);
  border-radius: 4px;
  background: rgba(8, 8, 16, 0.92);
  backdrop-filter: blur(32px) brightness(0.7);
  display: flex;
  flex-direction: column;
  gap: 0;
  animation: fadeSlideUp 400ms var(--ease-out-expo) both;
}

.login-card.shake {
  animation: fadeSlideUp 400ms var(--ease-out-expo) both,
             errorShake 400ms var(--ease-mechanical);
}

.card-glow {
  position: absolute;
  top: -1px;
  left: 20%;
  right: 20%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.6;
}

.card-glow::after {
  content: '';
  position: absolute;
  top: -8px;
  left: 10%;
  right: 10%;
  height: 16px;
  background: linear-gradient(90deg, transparent, rgba(41, 121, 255, 0.08), transparent);
  filter: blur(4px);
}

@keyframes fadeSlideUp {
  from {
    opacity: 0;
    transform: translate3d(0, 12px, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@keyframes errorShake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-6px); }
  40% { transform: translateX(5px); }
  60% { transform: translateX(-3px); }
  80% { transform: translateX(2px); }
}

.card-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding-bottom: 20px;
}

.brand-mark {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--accent);
  border-radius: 4px;
  background: rgba(41, 121, 255, 0.06);
  margin-bottom: 4px;
}

.brand-glyph {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 700;
  color: var(--accent);
  text-shadow: 0 0 12px rgba(41, 121, 255, 0.4);
  letter-spacing: -0.04em;
}

.brand-title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.2em;
  text-shadow: 0 0 8px rgba(41, 121, 255, 0.3);
}

.brand-sub {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 400;
  color: var(--text-tertiary);
  letter-spacing: 0.15em;
}

.card-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-mid), transparent);
  margin-bottom: 20px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.label-prompt {
  color: var(--accent);
  font-weight: 600;
}

.input-wrap {
  position: relative;
}

.field-input {
  width: 100%;
  padding: 10px 12px;
  background: rgba(5, 5, 7, 0.6);
  border: 1px solid var(--border-mid);
  border-radius: 4px;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 13px;
  outline: none;
  transition: border-color var(--dur-fast) var(--ease-mechanical),
              box-shadow var(--dur-fast) var(--ease-mechanical);
}

.field-input::placeholder {
  color: var(--text-muted);
  font-size: 12px;
}

.field-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent-muted), inset 0 0 12px rgba(41, 121, 255, 0.03);
}

.field-input:focus ~ .input-cursor {
  opacity: 1;
}

.input-cursor {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 1px;
  height: 16px;
  background: var(--accent);
  opacity: 0;
  animation: cursorBlink 1s step-end infinite;
  pointer-events: none;
  box-shadow: 0 0 4px rgba(41, 121, 255, 0.5);
}

@keyframes cursorBlink {
  0%, 100% { opacity: 0; }
  50% { opacity: 1; }
}

.field-input:focus ~ .input-cursor {
  animation: cursorBlinkActive 1s step-end infinite;
}

@keyframes cursorBlinkActive {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.login-error {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--rise);
  text-align: center;
  padding: 8px 12px;
  background: var(--rise-bg);
  border: 1px solid rgba(255, 59, 59, 0.15);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.error-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid var(--rise);
  font-size: 9px;
  font-weight: 700;
  flex-shrink: 0;
}

.login-btn {
  width: 100%;
  height: 44px;
  background: var(--accent);
  color: #ffffff;
  border: none;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: filter var(--dur-fast) var(--ease-mechanical),
              box-shadow var(--dur-fast) var(--ease-mechanical);
}

.login-btn:hover:not(:disabled) {
  filter: brightness(1.15);
  box-shadow: 0 0 16px rgba(41, 121, 255, 0.25);
}

.login-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.login-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-loading {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.loading-bar {
  display: inline-block;
  width: 32px;
  height: 2px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 1px;
  position: relative;
  overflow: hidden;
}

.loading-bar::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 60%;
  height: 100%;
  background: #ffffff;
  animation: progressScan 1s var(--ease-mechanical) infinite;
}

@keyframes progressScan {
  0% { left: -60%; }
  100% { left: 100%; }
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20px;
  padding-top: 12px;
  border-top: 1px solid var(--border-hair);
}

.footer-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--fall);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--fall);
  animation: statusPulse 2s ease-in-out infinite;
}

.footer-version {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-muted);
  letter-spacing: 0.04em;
}
</style>
