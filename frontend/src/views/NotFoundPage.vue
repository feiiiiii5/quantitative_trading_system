<template>
  <div class="not-found-page">
    <div class="nf-inner">
      <div class="nf-code">404</div>
      <div class="nf-divider" />
      <div class="nf-msg">PAGE NOT FOUND</div>
      <div class="nf-hint">THE REQUESTED RESOURCE DOES NOT EXIST OR HAS BEEN MOVED</div>
      <router-link to="/dashboard" class="nf-btn">RETURN TO DASHBOARD</router-link>
    </div>
  </div>
</template>

<style scoped>
.not-found-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 60vh;
}

.nf-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--u4);
}

.nf-code {
  font-size: 96px;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.04em;
  text-shadow: 0 0 40px rgba(41, 121, 255, 0.3);
}

.nf-divider {
  width: 60px;
  height: 2px;
  background: var(--accent);
  opacity: 0.4;
}

.nf-msg {
  font-size: var(--fs-xl);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.nf-hint {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  text-align: center;
  max-width: 400px;
}

.nf-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--u2) var(--u6);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border: 1px solid var(--accent);
  border-radius: var(--r-md);
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-mechanical),
              color var(--dur-fast) var(--ease-mechanical);
  text-decoration: none;
}

.nf-btn:hover {
  background: var(--accent);
  color: #fff;
}
</style>
