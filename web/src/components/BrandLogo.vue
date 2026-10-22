<script setup>
defineProps({
  tone: { type: String, default: 'dark' },
  compact: { type: Boolean, default: false },
})
</script>

<template>
  <div class="brand" :class="[`brand--${tone}`, { 'brand--compact': compact }]">
    <div class="brand-mark" aria-hidden="true">
      <span>E</span>
      <i />
    </div>
    <div v-if="!compact" class="brand-text">
      <strong>智课学伴</strong>
      <small>EduMate</small>
    </div>
  </div>
</template>

<style scoped>
.brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  position: relative;
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 13px;
  background: linear-gradient(135deg, #1677ff, #62a8ff);
  box-shadow: 0 8px 18px rgba(22, 119, 255, 0.28);
  color: #fff;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.04em;
}

.brand-mark i {
  position: absolute;
  right: -3px;
  top: -3px;
  width: 11px;
  height: 11px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: #7ee2b8;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-text strong {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.brand-text small {
  margin-top: 2px;
  color: var(--em-text-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.brand--light .brand-text strong {
  color: #fff;
}

.brand--light .brand-text small {
  color: rgba(255, 255, 255, 0.68);
}

.brand--compact {
  justify-content: center;
}
</style>
