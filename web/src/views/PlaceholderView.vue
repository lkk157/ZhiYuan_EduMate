<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import PagePlaceholder from '@/components/PagePlaceholder.vue'

const route = useRoute()
const title = computed(() => route.meta?.title || '功能模块')
const description = computed(() => route.meta?.description || '该模块正在建设中。')
</script>

<template>
  <PagePlaceholder :title="title" :description="description" />
</template>
